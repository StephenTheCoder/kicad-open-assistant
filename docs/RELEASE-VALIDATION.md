# Release validation — 0.1.0 candidate

Work in progress; this record does not yet certify a public release. Updated 2026-10-24.

Accepted host: Windows x64 KiCad 10.0.7 (file version 10.0.7.51283), Python 3.11.5, wxPython 4.3.1 / wxWidgets 3.3.3. Other hosts and schematic UI are unsupported.

## Evidence so far

- 35 automated tests pass locally: actual OpenAI 3.37.0 SDK with mocked HTTP streaming, cancellation, conversation persistence/isolation, PDF/DOCX/image bounds, request policy, backend authentication/revocation, rates, concurrent reservations, kill switch, disconnect accounting and secret exclusion.
- Windows Credential Manager synthetic write/read/delete passed in the interactive user context; the test credential was removed. The sandbox-only attempt was denied and no file fallback occurred.
- The first PCM-format candidate was installed into a fresh isolated profile using the manual installer and launched in actual PCB Editor. The real dock opened and loaded its database through a worker. This was not a mock UI.
- Candidate metadata passes the installed official KiCad PCM v2 schema. Repeated ZIP builds are byte-for-byte identical. The source/index/archive scan has no unexplained findings; Pillow's embedded font requires an exact-file-hash exception for an AWS-shaped base64 sequence.
- Original source is public at https://github.com/StephenTheCoder/kicad-open-assistant. CI run 40149123295 passed Windows/Linux tests, audited reproducible packaging, and container build/ledger initialization on commit 1a0b780. CI run 40149801024 also passed actual container HTTP health, authentication, disabled access, revocation and secret exclusion on commit 1160574. Its clean CI package matched the corresponding local build byte-for-byte. CI run 40150553335 passed the DOCX dependency reduction (33 tests on each OS, package and actual container checks). Ingress template validation passed in run 40150812396; subsequent alpha-flattening and bounded server-secret preflight tests raise the local total to 35 and await their CI run. No versioned release has been published.

## Pending gates

Actual UI checks of CRUD/restart, attachments/review, keyboard, resize/reopen, cancellation and failure states; the bounded live smoke after local key configuration; final reproducibility and full history/archive audit; CI/container results; public source and tested release links. Sponsored hosting and funding remain deliberately unconfigured/disabled.

Historical FEASIBILITY.md evidence does not replace release testing. Code/version changes after a test require appropriate rechecks.

Latest local candidate: SHA-256 `504a77b928bba5e9d3121d39c77cc209cb8bb1cf6166456aef1e8704e77465a1`, 13,416,072 bytes, 2,627 members. Two local builds match exactly. This candidate still requires actual runtime validation. The offline API fixture is prepared but has not been launched; it is not evidence of a UI pass.

Packaged-worker preflight under KiCad's Python passes all five original attachment fixtures and mocked streaming/missing-credential/network/quota paths. This runs actual packaged code but does not count as UI interaction or a live model response. The updated unmodified candidate is installed in release-c; offline fixture-d is prepared. Both await runtime launch.
