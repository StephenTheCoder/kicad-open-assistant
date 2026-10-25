# Security boundaries and reporting

The experimental dock runs in KiCad through its legacy Python interface. It is not a security sandbox around KiCad itself. Parsing, storage and network operations run in disposable Python workers. On Windows a Job Object enforces a 512 MiB process-memory cap and kill-on-close; parsing has a 30-second deadline and chat a 180-second application deadline. Failure to apply the Job Object fails closed. Workers do not execute generated code or modify designs.

Input allowlists, size/page/pixel/archive-expansion limits, a bounded final request, verified TLS and disabled automatic inference retries apply to both connection modes. Only reviewed inline PNG images are accepted by the backend; arbitrary URL fetches, tools, caller instructions and endpoint overrides are rejected. Images and documents remain untrusted; keep pinned parser dependencies patched.

Sponsored access uses high-entropy bearer tokens stored as SHA-256 hashes on the server. Issuing a token for an existing user rotates access without resetting accounting. Revocation and the administrator kill switch are checked during streaming. Use HTTPS; distribute tokens through a secure channel, not public issues or chat logs.

The ledger serializes reservations with SQLite `BEGIN IMMEDIATE` and durable writes. Run one deployment against one local persistent database. Do not use NFS, ephemeral DBs, separate writable replicas or copies restored behind the provider's actual spending. Reservations include the full supported model's context and output cap at reviewed, conservative prices. Caching discounts are ignored. Unknown/cancelled outcomes retain the full reservation; no automatic retry or refund can create free capacity. A lost accounting service blocks work. Operator price reviews must expire; changing model/rate policy needs review and tests.

The global allowance bounds API spending only under the configured provider prices and model limits. It does not include hosting charges or unrelated calls made with the same provider credential. Use a dedicated provider project/key, provider-side limits as a second layer, and keep pricing current. Sponsored activation remains disabled until the owner sets the deployment and budget.

Report vulnerabilities privately through the repository owner's GitHub security reporting if enabled. Never include API keys, access tokens, private designs or unredacted request bodies in an issue. If private reporting is unavailable, open an issue asking for a secure contact route without disclosing the vulnerability detail.
