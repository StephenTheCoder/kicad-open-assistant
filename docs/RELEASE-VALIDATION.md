# Release validation — 0.1.0 candidate

Work in progress; this record does not yet certify a public release. Updated 2026-10-24.

Accepted host: Windows x64 KiCad 10.0.7 (file version 10.0.7.51283), Python 3.11.5, wxPython 4.3.1 / wxWidgets 3.3.3. Other hosts and schematic UI are unsupported.

## Evidence so far

- 37 automated tests pass locally: actual OpenAI 3.37.0 SDK with mocked HTTP streaming, cancellation, conversation persistence/isolation, PDF/DOCX/image bounds, request policy, backend authentication/revocation, rates, concurrent reservations, kill switch, disconnect accounting and secret exclusion.
- Windows Credential Manager synthetic write/read/delete passed in the interactive user context; the test credential was removed. The sandbox-only attempt was denied and no file fallback occurred.
- The first PCM-format candidate was installed into a fresh isolated profile using the manual installer and launched in actual PCB Editor. The real dock opened and loaded its database through a worker. This was not a mock UI.
- Candidate metadata passes the installed official KiCad PCM v2 schema. Repeated ZIP builds are byte-for-byte identical. The source/index/archive scan has no unexplained findings; Pillow's embedded font requires an exact-file-hash exception for an AWS-shaped base64 sequence.
- Original source is public at https://github.com/StephenTheCoder/kicad-open-assistant. CI run 40149123295 passed Windows/Linux tests, audited reproducible packaging, and container build/ledger initialization on commit 1a0b780. CI run 40149801024 also passed actual container HTTP health, authentication, disabled access, revocation and secret exclusion on commit 1160574. Its clean CI package matched the corresponding local build byte-for-byte. CI run 40150553335 passed the DOCX dependency reduction (33 tests on each OS, package and actual container checks). CI run 40151378769 passed all five jobs on 8503f90: 35 tests on each OS, deterministic package, Compose/container HTTP smoke and ingress validation. Its clean CI package matches the local candidate. The managed-host adapter adds two tests (37 total). CI run [40152610253](https://github.com/StephenTheCoder/kicad-open-assistant/actions/runs/40152610253) passes all five jobs on 871462c: 37 tests on each OS, ingress validation, both container modes, and reproducible packaging. The managed container runs HTTP as UID 10001 and preserves charges/kill state across restart. The clean CI archive matches the current local candidate byte-for-byte. A prior managed-host test lacked the filesystem capability needed to prepare the container-owned volume; the corrected constrained test passes. The Railway configuration also passes its current official JSON schema. No versioned release has been published.

## Pending gates

Actual UI checks of CRUD/restart, attachments/review, keyboard, resize/reopen, cancellation and failure states; the bounded live smoke after local key configuration; final reproducibility and full history/archive audit; tested release links. Sponsored allowances have been approved privately by the owner; the selected Railway account, hosting-fee limit and server funding secret remain unconfigured. Access stays disabled.

Historical FEASIBILITY.md evidence does not replace release testing. Code/version changes after a test require appropriate rechecks.

Latest local candidate: SHA-256 `91cdf6544eeb02ea682d615eb0ef7555ddd68ddb9e29f27738ebc99875ec6446`, 13,416,089 bytes, 2,627 members. Two local builds match exactly. This candidate still requires actual runtime validation. The offline API fixture is prepared but has not been launched; it is not evidence of a UI pass.

Packaged-worker preflight under KiCad's Python passes all five original attachment fixtures and mocked streaming/missing-credential/network/quota paths. This runs actual packaged code but does not count as UI interaction or a live model response. The newest unmodified candidate is installed in fresh release-d; offline fixture-e is prepared. Both await runtime launch. The current archive includes the managed server-secret privacy disclosure.
