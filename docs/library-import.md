# Monarch library import and migration

The library is imported verbatim from Monarch PR #4758, commit
`d6720b86bc94f2d68c67a31943c1d07580e02da0`. See THIRD_PARTY_NOTICES.md
for attribution, license scope, and outstanding provenance review.

This is a breaking library update. Existing Harvard CNS examples, tests, and
API/architecture documentation are retained as historical material and have
not been migrated. They describe the earlier PyTorch P2P/HTTP implementation.
Do not use them as a working integration guide for this imported library.
The old Megatron/SGLang frontend modules are absent from the source snapshot
and are removed rather than retained as incompatible adapters.

Integration changes:

- AdapterContext now takes hf_weights (name-to-factory mapping), hf_shapes,
  wksd_factory (fresh runtime state-dict snapshot), load_weights, and rank.
  The old hf_iter_factory, wksd, and load_spec_path fields are removed.
- ReceiverAdapter takes num_workers; call poll_requests on all model-parallel
  ranks in lockstep. before_receive(epoch) is the quiescence hook before mutation.
- Start the ZMQ coordinator with wbridge.backend.coordinator.spawn; derive
  endpoints with coordinator_ipc/coordinator_tcp_port in control_channel.
  The earlier FastAPI controller and set_worker_num contract do not apply.
- SenderArgs selects protocol (efa, tcp, monarch) and optional sender_staging;
  the earlier gpu_direct/cpu_direct transfer_mode contract does not apply.
- send_weights returns a CUDA event (or None). Wait before overwriting source
  weights; wait_send_complete is the separate delivery/consumption debug barrier.
- Monarch must be supplied by the environment and requires actor execution;
  sender/receiver staging with Monarch is unsupported.

Install optional runtime extras as needed: `.[cuda,mooncake]` or
`.[checkpoints]`. The generic imports do not require Monarch or Mooncake.
For the exact source integration contract and deployment caveats, consult
https://github.com/SwiftSeal03/monarch/tree/d6720b86bc94f2d68c67a31943c1d07580e02da0/examples/weightbridge/docs
rather than the retained historical docs.

## Import validation

Verified inside lbd2 container slime3 at /root/weightbridge:

- All 21 imported library Python files match the source snapshot byte-for-byte.
- Generic library/frontend imports and compileall succeed.
- Wheel build succeeds; LICENSE and THIRD_PARTY_NOTICES.md are present under
  dist-info/licenses. No source PR examples/tests/docs/scripts are packaged.
- Source-snapshot arena planner, logical splitting, Monarch engine, Mooncake
  engine, and TCP control tests: 76 passed. These tests were run from temporary
  scratch storage, not imported into this repository; engine tests include mocks
  and do not establish real RDMA fabric correctness.
- Retained Harvard CNS tests: 13 passed, 26 failed (old API/return contracts).
- An isolated source control-channel check: 1 passed, 1 failed; the test calls
  ControlChannel.step, which is absent in the imported API.
- A broader source-snapshot run encountered control-channel failures and hung
  before completion; it was terminated. This is not a passing full-suite result.
- git diff --check reports one pre-existing blank line at EOF in the imported
  utils/layout.py. Kept unchanged to preserve the source snapshot; other changed
  files pass the whitespace check.

This draft is not merge-ready: migrate retained tests/examples/docs, resolve
control-channel validation, verify real GPU/RDMA weight equality, and confirm
rights-holder release authorization before merging.
