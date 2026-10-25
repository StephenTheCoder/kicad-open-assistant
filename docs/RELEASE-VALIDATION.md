# Release validation â€” 0.1.0 candidate

Work in progress; this record does not yet certify a public release. Updated 2026-10-24.

Accepted host: Windows x64 KiCad 10.0.7 (file version 10.0.7.51283), Python 3.11.5, wxPython 4.3.1 / wxWidgets 3.3.3. Other hosts and schematic UI are unsupported.

## Evidence so far

- 30 automated tests pass locally: actual OpenAI 3.37.0 SDK with mocked HTTP streaming, cancellation, conversation persistence/isolation, PDF/DOCX/image bounds, request policy, backend authentication/revocation, rates, concurrent reservations, kill switch, disconnect accounting and secret exclusion.
- Windows Credential Manager synthetic write/read/delete passed in the interactive user context; the test credential was removed. The sandbox-only attempt was denied and no file fallback occurred.
- The first PCM-format candidate was installed into a fresh isolated profile using the manual installer and launched in actual PCB Editor. The real dock opened and loaded its database through a worker. This was not a mock UI.
- Candidate metadata passes the installed official KiCad PCM v2 schema. Repeated ZIP builds are byte-for-byte identical. The source/index/archive scan has no unexplained findings; Pillow's embedded font requires an exact-file-hash exception for an AWS-shaped base64 sequence.
- Original source is public at https://github.com/StephenTheCoder/kicad-open-assistant. CI run 40149123295 passed Windows/Linux tests, audited reproducible packaging, and container build/ledger initialization on commit 1a0b780. Subsequent changes add an actual disabled-container HTTP check; its result is pending. No versioned release has been published.

## Pending gates

Actual UI checks of CRUD/restart, attachments/review, keyboard, resize/reopen, cancellation and failure states; the bounded live smoke after local key configuration; final reproducibility and full history/archive audit; CI/container results; public source and tested release links. Sponsored hosting and funding remain deliberately unconfigured/disabled.

Historical FEASIBILITY.md evidence does not replace release testing. Code/version changes after a test require appropriate rechecks.

Latest local candidate: SHA-256 `0a49fa71c65a73f4aaf49f8e05bad929d94411a3461a2c5291f1bace8f3c71dd`, 17,656,503 bytes, 2,911 members. Two local builds match exactly. This candidate still requires actual runtime validation. The offline API fixture is prepared but has not been launched; it is not evidence of a UI pass.
