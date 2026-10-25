# KiCad Open Assistant

An original, open-source advisory AI assistant **docked inside KiCad's PCB Editor**. Release 0.1 targets Windows x64 **KiCad 10.0.7**, with its bundled Python/wx runtime. It uses deprecated/internal host interfaces and is explicitly experimental. It never modifies designs or executes model-generated code. Schematic files can be attached; schematic UI hosting is unsupported.

The owner accepted this PCB-only dock after real feasibility tests: [UI decision](docs/ADR-001-ui-hosting.md). There is no silent fallback to a browser, floating window or companion.

## Basic features

- Electronics and KiCad questions through OpenAI Responses, progressive text, cancellation and clear errors.
- Local conversations with create, rename, switch, delete, export and restart persistence.
- Bounded KiCad/text, PDF, DOCX and PNG/JPEG/WebP attachments, local extraction and editable outgoing text.
- Explicit active-board metadata selection and review of destination, history, text and actual outgoing images before sending.
- Personal keys in Windows Credential Manager, or optional authenticated sponsored access funded by the operator.
- Disposable workers keep network, parsing and SQLite off KiCad's UI thread and enforce memory/time limits.

Sponsored access starts disabled. Its backend has revocable application tokens, server-controlled model/output limits, quotas, rate/concurrency limits, durable global spending reservations and an administrator kill switch. The operator's OpenAI key remains a server secret; users never receive it or need a subscription. Publishing source does not activate hosting.

## Install and use

Use the versioned PCM ZIP from the GitHub release, not GitHub's source ZIP. In KiCad Manager choose **Plugin and Content Manager → Install from File**, apply the package, restart PCB Editor, then choose **Tools → External Plugins → KiCad Open Assistant**. Follow [installation and removal](docs/INSTALLATION.md).

Set a connection, choose a conversation, select attachments/context deliberately, then **Review and send**. Ctrl+Enter opens review from the composer; Escape cancels local work. Cancelled or failed requests may have incurred provider cost; the app never retries automatically.

## Build, validate and operate

Read [acceptance criteria](docs/ACCEPTANCE.md), [release validation](docs/RELEASE-VALIDATION.md), [implementation architecture](docs/IMPLEMENTATION.md), [privacy](docs/PRIVACY.md), [security](docs/SECURITY.md), [backend deployment](docs/BACKEND.md), and [contribution/build instructions](CONTRIBUTING.md). Tests mock inference by default. Real KiCad checks and the bounded live smoke are recorded separately; a mock UI does not establish integration.

Personal mode works independently of sponsored hosting. Hosted activation requires a chosen host/domain, server secret mount, current pricing review and explicit funded allowance.

## Licensing and provenance

Original code/prose are MIT licensed; dependencies retain their notices. See [licensing](docs/LICENSING.md), [third-party notices](docs/THIRD-PARTY-NOTICES.md) and [provenance](docs/PROVENANCE.md). No proprietary plugin implementation, assets, configuration, conversations or investigation archive are included. This project is not endorsed by KiCad or OpenAI. PCM-compatible packaging does not imply official repository acceptance.
