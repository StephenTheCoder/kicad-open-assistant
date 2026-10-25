# Privacy and data flow

Conversations are local by default. SQLite contains your messages, partial answers and any reviewed attachment snapshots you sent. This storage is not encrypted by the application. File exports also contain that content. Local database deletion does not erase separate backups or provider records.

No project is scanned automatically. Active-board context is a small, explicitly selected live metadata summary, including unsaved editor state. Raw files are included only when selected as attachments. PDFs and DOCX are extracted locally; the original documents are not uploaded. Images are decoded locally and converted to metadata-free PNG. Uploaded text and model output are treated as data, never executable code or design-editing commands.

Review shows the prompt, chosen completed history, file text, context, outgoing images, model and destination. Cancel before confirmation sends no model request. The local worker communicates with the panel over private process pipes; it has no listening network service.

Personal mode sends that snapshot over verified HTTPS directly to OpenAI. Sponsored mode sends it to the configured operator backend, which forwards it to OpenAI under the operator account. The backend therefore processes the same selected content. Sponsored status checks transmit your application access token; they send no design content. Avoid configuring an endpoint you do not trust.

The application sends `store=false` and maintains conversation history itself. This does not guarantee zero provider retention. OpenAI abuse-monitoring policies and account-specific controls still apply: [official data controls](https://developers.openai.com/api/docs/guides/your-data).

Credentials are stored in Windows Credential Manager. Personal keys never go to the sponsored service. Sponsored provider keys stay in a server-side secret mount or managed sealed secret variable; clients receive only administrator-issued, revocable application tokens. The backend stores token hashes, pseudonymous user IDs, reservation/usage totals and short-lived hashed-peer rate counters, not prompts or answers. Turn off reverse-proxy request-body/header logging; the supplied configuration does not enable it.

The client intentionally suppresses raw SDK/parser exceptions that could contain document fragments. Errors use fixed categories. Model answers appear as plain text. No telemetry, automatic cloud synchronization or remote tools are included.
