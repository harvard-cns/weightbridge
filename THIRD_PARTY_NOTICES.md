# Imported WeightBridge snapshot provenance

This change imports the complete `examples/weightbridge/` directory from
https://github.com/meta-pytorch/monarch/pull/4758 at commit
`d6720b86bc94f2d68c67a31943c1d07580e02da0` (SwiftSeal03/monarch).
Examples, tests, scripts, and .gitignore are copied verbatim. Library changes
only update comment/docstring terminology; executable logic is unchanged.
README and documentation are subsequently edited locally: installation details
are moved into a guide, API and integration documentation are consolidated,
and motivation is covered by the paper. pyproject.toml additionally declares
and packages the source license and this notice. LICENSE, MANIFEST.in, and this notice are redistribution
support files added by this import.

The source repository root LICENSE at that revision is BSD-3-Clause and is
reproduced verbatim in this repository root LICENSE. Existing Meta Platforms,
Inc. and affiliates copyright/license headers are retained. Preserve these
notices, license conditions, and disclaimer in source redistributions and
reproduce them in documentation/materials accompanying binary distributions.
No Meta or Monarch endorsement is claimed.

## Scope and review requirements

The BSD license here records the terms supplied with the imported snapshot.
It does not independently establish copyright ownership. Public source and
headers do not independently prove employer release authorization. Before
merging, maintainers should confirm that the relevant rights holders authorized
this snapshot for public BSD redistribution. This import does not assert that
confirmation has occurred. The source PR contains a historical CLA warning;
its current resolution and any applicable internal employer approvals have
not been verified. Monarch contribution acceptance and downstream
redistribution are separate questions.

The original Harvard CNS paths absent from the source snapshot are
`wbridge/frontend/megatron_adapter.py` and
`wbridge/frontend/sglang_adapter.py`; these obsolete adapters are removed.
The earlier library-only migration document is removed because documentation,
examples, and tests now come from the same full source snapshot as the library.

Packaging includes this notice and the BSD license. Optional dependencies
retain their own licenses; they are not vendored by this import.
