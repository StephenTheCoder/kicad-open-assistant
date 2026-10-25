# Acceptance checklist

Status key: checked = achieved in this milestone; unchecked = required later or pending a decision. A defined requirement is not a passed test.

## Feasibility milestone

- [x] Separate Git repository and original MIT code/docs scaffold.
- [x] Read-only graphify query of existing functional investigation; REA evidence reused without reopening the proprietary artifact.
- [x] KiCad version detected and official extension/API documentation consulted.
- [x] Original prototype loaded and run inside the actual PCB editor.
- [x] KiCad-owned modeless window and real experimental dock distinguished and demonstrated.
- [x] PCB and schematic tested separately, including IPC action launch; documentation discrepancy recorded.
- [x] Minimal context preview, local streaming simulation and active cancellation demonstrated.
- [x] Screenshots, versions, failure conditions and unsupported boundaries recorded.
- [x] Original basic requirements, architecture, hosting ADR and licensing plan prepared.
- [x] Owner chose option A: experimental PCB-only dock pinned to Windows KiCad 10.0.7. Full release work is authorized.

## Basic release gates

Implementation now exists. Passing automated and runtime evidence is recorded in RELEASE-VALIDATION.md; this checklist is not a blanket pass.

| Feature | Acceptance test |
|---|---|
| Electronics/KiCad Q&A | Representative questions receive streamed answers; missing circuit values are requested; no fabricated ERC/DRC pass or executed code |
| Conversations | Create/rename/switch/delete; restart preserves state; stream stays with originating conversation; deletion cancels pending work; crash recovery marks partial turns |
| Text/KiCad attachments | Each allowed type previews exact selected text; boundary-size and unsupported/binary/encoding cases produce useful errors |
| PDF | Text PDFs extract bounded page text; scanned/encrypted/corrupt/over-page-limit inputs are identified; no hidden full PDF upload |
| DOCX | Paragraph/table extraction; bounded expanded ZIP and parser resources; no external relationship fetches or macro execution |
| Images | Decode formats and pixel caps; outgoing metadata stripped; preview is the transmitted image; oversized/corrupt images fail safely |
| Aggregate limits | Enforce count, raw/encoded bytes, character/token budgets and gateway limits; no silent truncation |
| Explicit context | No selection means no design context; user chooses exact editor/files; unsaved snapshot status shown; wrong-instance and changed-file cases tested |
| Outgoing review | Show history, prompt, actual files/fields/images, destination and model; edits invalidate approval; sent bytes match immutable reviewed snapshot |
| Responsiveness | Long extraction/network requests leave editor usable; duplicate sends prevented; close/switch/project changes do not cause stale widget access |
| Cancellation | Cancel during preparation/streaming; no late updates; hosted request cancelled where supported; costs/partial output represented accurately |
| Errors | Simulated auth/quota/timeout/disconnection/parser/server errors preserve draft and offer specific recovery; no automatic alternate-destination resend |
| Accessibility | Keyboard-only CRUD/attachment/review/send/cancel; focus visible and predictable; screen reader, high DPI, themes and narrow layout verified |
| Personal key | OS credential storage with a clear error if unavailable; key absent from logs, DB and package; invalid key and unavailable store tested |
| Hosted mode | Server-only funded key; authenticated limits and hard budget accounting; malicious client cannot bypass caps; cancellation, retention and outage behavior tested |
| Packaging | Exact host/runtime compatibility matrix, signed/reproducible packaging plan, dependency lock/SBOM/notices and GPL obligations where applicable |

Hosted authentication and limits are implemented; deployment location and owner-funded allowances remain explicit activation choices. Autonomous routing, circuit generation, board modification and cloud sync are outside Basic.

## Accepted UI release gate

- [ ] A: version-gate the dock; test pane teardown, reload, multiple editors and every supported KiCad/wx build; disclose PCB-only/legacy support.

Alternatives B (owned window), C (companion) and D (fork/upstream host work) were not selected. Their historical evidence remains in ADR-001 and FEASIBILITY.md; they are not Basic release requirements.
