# Basic release requirements

Status: accepted scope, 2026-10-24. The owner approved an experimental PCB-only dock pinned to Windows KiCad 10.0.7. Implementation evidence is tracked in RELEASE-VALIDATION.md; requirements alone do not prove completion.

## Purpose and scope

KiCad Open Assistant helps a person understand electronics, ask KiCad questions and discuss explicitly selected design information. Distribution of the assistant is free. In personal-key mode the user pays their API provider; in optional hosted mode the operator funds inference under a declared allowance. Free software distribution does not promise unlimited free inference.

The user wants the assistant hosted inside KiCad. A docked panel shares the editor layout and resizes with it. A KiCad-owned modeless window is a separate floating top-level window that leaves the editor usable. A companion is another application/process, even if KiCad launches it. Only the first satisfies strict docking. The hosting decision is a release gate, with PCB and schematic support evaluated separately.

## Evidence basis

The previous investigation establishes chat, conversation management and attachments as visible/static baseline capabilities. Its runtime and hosted behavior were not verified. Public product descriptions describe hosted question assistance and higher unspecified limits. Neither that evidence nor those descriptions justify including autonomous circuit generation, routing, electrical correctness guarantees or automated ERC/DRC fixes in this release. Proposed safeguards, limits and UX below are our own decisions, not claims about the inspected software.

## Functional requirements

### Answers

- Explain components, units, common circuit behavior, KiCad operations and selected design information in conversational text.
- Identify missing facts, assumptions and uncertainty. Label suggested checks; do not present model advice as a passed ERC/DRC test or a certification.
- Do not execute model-generated code, invoke shell commands, modify a design, or follow instructions embedded in attachments as application commands.
- Show mode, provider endpoint, model, request state and actionable errors. Model selection must reflect actual account/model capability, not a hard-coded marketing list.

### Local conversations

- Create, rename, switch and delete independent conversations, with stable identifiers and local restart persistence.
- Store messages and attachment references in transactional SQLite under the user's application data directory, outside plugin installation and Git directories.
- Switching during a response must keep streamed content attached to its originating conversation. Deleting an active conversation cancels its request and requires a clear local deletion confirmation in the product.
- Crash recovery preserves completed turns and marks interrupted partial answers. Allow export; disclose that ordinary local storage is not encrypted unless explicitly implemented.
- No automatic cloud conversation synchronization. Deletion removes local records and unreferenced managed attachments; explain any separate provider-side retention.

### Attachments (proposed application limits)

| Format | Input cap | Processing and review |
|---|---:|---|
| KiCad/text (`.kicad_pcb`, `.kicad_sch`, `.kicad_pro`, `.net`, `.kicad_sym`, `.kicad_mod`, `.txt`, `.md`, `.csv`, `.json`) | 5 MiB/file | Bounded text decoding, explicit encoding error; show exact selected text, basename and truncation |
| PDF | 10 MiB/file, 100 pages | Local text extraction initially; scanned pages are flagged, not silently treated as empty. Original PDF/visual pages require explicit separate selection |
| DOCX | 10 MiB/file; 50 MiB expanded ZIP contents | Extract paragraphs/tables locally; reject encrypted/damaged archives and excessive expansion; no macros or external resource resolution |
| PNG/JPEG/WebP | 10 MiB/file, 20 megapixels | Decode/validate locally, strip metadata from the outgoing copy, display actual outgoing image and dimensions |

Maximum 8 attachments and 20 MiB total original bytes per message; final encoded payload has an independent 30 MiB cap. Text budget starts at 100,000 characters across attachments and context; provider token limits may be lower. All limits are configurable downward by a hosted operator and are validated again server-side. Bound parser time/memory; reject symlinks escaping the explicitly chosen scope and unsupported binary files. These are initial policy values to validate, not tested parser implementations.

The user's original files are never edited. Full-file upload, extracted text and rendered page images are distinct choices. Preview must show actual outgoing data. No hidden upload merely to generate a preview. A changed source file requires a new snapshot/review; sending uses the reviewed immutable snapshot.

### Context and transmission

- Start each chat with no selected project context. User selects an active board, a document, or specific files. Do not infer permission to scan the entire project directory.
- Name the editor instance, file and whether a snapshot includes unsaved changes. An IPC connection must use the launching instance's socket/token; never choose an arbitrary running board.
- Offer a read-only summary and optionally selected raw design text. Schematic files can be explicitly attached even if in-editor schematic hosting is unavailable, but that does not count as schematic UI integration.
- Before sending, show destination/provider, model, included conversation history, prompt, selected files/fields, outgoing text/image preview, byte counts, omissions and estimated usage where available. Allow removal/redaction and cancel.
- Changes to endpoint, mode, model, message, history or context invalidate the reviewed payload. No automatic resend to another provider after failure.
- Do not log keys, prompts, document contents, local full paths or IPC tokens by default. Diagnostics contain redacted request IDs and error categories.

### Responsiveness and accessibility

- Network, parsing and SQLite work must not block the editor event loop. UI updates are marshaled onto its thread.
- Streaming shows text progressively. Cancel stops UI updates, aborts the client stream and requests hosted cancellation where supported. Already processed input/output may still incur costs.
- Disable duplicate submissions; correlate every event by request and conversation ID. Timeouts, authentication, permission, quota, malformed file and network errors have distinct recovery guidance.
- Every control has a visible label/accessibility name, predictable tab order and visible focus. Ctrl+Enter sends after review; Enter inserts a newline; Escape cancels a request from the composer. Test with keyboard and a screen reader, high DPI, dark/light theme and narrow panes.

### Personal API keys and optional operator-funded hosting

- Personal mode connects directly to the chosen supported provider using that user's key. Use the OS credential store, with an explicit session-only fallback if unavailable; never silently write keys to JSON or the conversation DB.
- Hosted mode authenticates users to an operator gateway. The operator's provider key remains server-side. No shared funded key is shipped in a plugin, repository or release archive.
- Gateway enforces authentication, per-user limits, concurrency, payload/token caps, allowed models, spend ceilings and a global kill switch. Reserve budget before inference and reconcile actual usage after completion/cancellation. Treat client price/usage estimates as untrusted.
- Hosted quotas, authentication service, model allowance, funding ceiling, retention policy and deployment are undecided. No backend or account infrastructure is deployed at this milestone. Personal mode must remain usable when the optional host is unavailable.
- TLS verification stays enabled. A paid response is never initiated by the offline prototype.

## Deferred work

Autonomous routing, circuit generation, component placement, automatic board edits, tool-execution agents, live ERC/DRC repair, OCR, broad project indexing, cloud sync, collaboration and multiple-provider parity require separate acceptance and design decisions. A KiCad 11 migration is future work; its documented roadmap is not a tested result here.
