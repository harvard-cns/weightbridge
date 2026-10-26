"""CPU-only tests for per-update metadata carried from ``send_weights`` to ``poll_requests``."""

from __future__ import annotations

import ctypes
import json
import threading
from types import SimpleNamespace

import pytest

torch = pytest.importorskip("torch")

from wbridge.backend.control_channel import RECEIVE, RECEIVE_REQUEST  # noqa: E402
from wbridge.backend.coordinator import WeightReceiverController  # noqa: E402
from wbridge.backend.receiver import WeightReceiver  # noqa: E402
from wbridge.backend.router import update_metadata_slot_bytes  # noqa: E402
from wbridge.backend.sender import WeightSender  # noqa: E402

META_BYTES = update_metadata_slot_bytes()


class _LoopbackEngine:
    """Copies registered host memory in-process, standing in for a one-sided RDMA write."""

    def write_async(self, session, src_ptrs, dst_ptrs, sizes):
        for src, dst, size in zip(src_ptrs, dst_ptrs, sizes):
            ctypes.memmove(dst, src, size)
        return None

    def wait(self, handles):
        assert handles == []


def _receiver(round_peers: list[list[int]]) -> WeightReceiver:
    r = WeightReceiver.__new__(WeightReceiver)
    r.router = SimpleNamespace(
        local_rounds=[(None, {p: object() for p in peers}) for peers in round_peers]
    )
    r.num_rounds = len(round_peers)
    r._epoch = 0
    peers = sorted({p for ps in round_peers for p in ps})
    r.flag_slot_of = {p: i for i, p in enumerate(peers)}
    r._flag_buf = torch.zeros(max(len(peers), 1) * r.num_rounds, dtype=torch.int64)
    r._meta_bytes = META_BYTES
    r._meta_buf = torch.zeros(max(len(peers), 1) * META_BYTES, dtype=torch.uint8)
    r._connected = True
    r.update_metadata = None
    r._fallback_metadata = None
    return r


def _sender_into(receiver: WeightReceiver, sender_rank: int) -> WeightSender:
    """A sender whose only peer is *receiver*, writing into the inbox slot the receiver assigned it."""
    s = WeightSender.__new__(WeightSender)
    s.engine = _LoopbackEngine()
    s.peers = [100]
    s.peer_session = {100: "loopback"}
    s._meta_bytes = META_BYTES
    s._meta_src = torch.zeros(META_BYTES, dtype=torch.uint8)
    slot = receiver.flag_slot_of[sender_rank]
    s._meta_dst = {100: receiver._meta_buf.data_ptr() + slot * META_BYTES}
    return s


def _flag(r: WeightReceiver, peer: int, epoch: int, ri: int = 0) -> None:
    seq = epoch * r.num_rounds + ri + 1
    slot, _ = r._flag_message_slot(r.flag_slot_of[peer], seq)
    r._flag_buf[slot] = seq


def test_inbox_round_trip_is_tagged_with_its_epoch() -> None:
    r = _receiver([[2, 3]])
    s = _sender_into(r, 3)
    s._write_update_metadata(4, json.dumps({"weight_version": 17}).encode())

    assert json.loads(r._read_update_metadata(3, 4)) == {"weight_version": 17}
    # Another epoch, or a sender that wrote nothing, reads as "no metadata".
    assert r._read_update_metadata(3, 5) is None
    assert r._read_update_metadata(2, 4) is None


def test_oversized_metadata_is_rejected_before_any_write() -> None:
    r = _receiver([[2]])
    s = _sender_into(r, 2)
    with pytest.raises(ValueError, match="WBRIDGE_METADATA_BYTES"):
        s._write_update_metadata(0, b"x" * META_BYTES)
    assert r._read_update_metadata(2, 0) is None


def test_go_carries_first_round_sender_metadata() -> None:
    r = _receiver([[], [5, 7]])
    for rank in (5, 7):
        _sender_into(r, rank)._write_update_metadata(0, b'{"weight_version": 3}')
    _flag(r, 5, 0, ri=1)
    _flag(r, 7, 0, ri=1)

    assert r._rank0_decision(None, staged=False) == {
        "type": RECEIVE_REQUEST,
        "epoch": 0,
        "metadata": {"weight_version": 3},
    }


def test_go_without_metadata_keeps_the_plain_decision() -> None:
    r = _receiver([[2]])
    _flag(r, 2, 0)
    assert r._rank0_decision(None, staged=False) == {"type": RECEIVE_REQUEST, "epoch": 0}


def test_zero_input_rank_takes_metadata_from_the_doorbell() -> None:
    r = _receiver([[], []])
    doorbell = {"type": RECEIVE_REQUEST, "metadata": {"weight_version": 9}}
    assert r._rank0_decision(doorbell, staged=False) == {
        "type": RECEIVE_REQUEST,
        "epoch": 0,
        "metadata": {"weight_version": 9},
    }


def test_before_receive_sees_metadata_on_rank0_and_peers() -> None:
    seen: list[tuple[int, object, object]] = []

    rank0 = _receiver([[2]])
    rank0.rank = 0
    rank0._rank = 0
    rank0.receiver_staging = False
    rank0._ext_req = None
    rank0._ext_cv = threading.Condition()
    broadcast: list[dict] = []
    rank0._chan = SimpleNamespace(broadcast=broadcast.append)
    rank0.request_update = lambda: True
    _sender_into(rank0, 2)._write_update_metadata(0, b'{"weight_version": 41}')
    _flag(rank0, 2, 0)

    assert rank0.poll_requests(lambda epoch: seen.append((0, epoch, rank0.update_metadata)))
    assert rank0.update_metadata == {"weight_version": 41}

    # The peer only gets the decision rank 0 broadcast, round-tripped through JSON like the hub does.
    peer = _receiver([[2]])
    peer.rank = 1
    peer._rank = 1
    peer.receiver_staging = False
    wire = json.loads(json.dumps(broadcast[0]))
    peer._chan = SimpleNamespace(poll_decision=lambda timeout_ms: wire)
    peer.request_update = lambda: True
    assert peer.poll_requests(lambda epoch: seen.append((1, epoch, peer.update_metadata)))

    assert seen == [(0, 0, {"weight_version": 41}), (1, 0, {"weight_version": 41})]


def test_coordinator_relays_doorbell_metadata_to_rank0() -> None:
    controller = WeightReceiverController.__new__(WeightReceiverController)
    sent: list[dict] = []
    controller._send_to_rank0 = sent.append
    controller._gather_ack = lambda **_: True

    assert controller._handle({"type": RECEIVE, "metadata": {"weight_version": 2}}) == {
        "status": "success"
    }
    assert controller._handle({"type": RECEIVE}) == {"status": "success"}
    assert sent == [
        {"type": RECEIVE_REQUEST, "metadata": {"weight_version": 2}},
        {"type": RECEIVE_REQUEST},
    ]
