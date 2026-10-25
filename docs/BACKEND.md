# Sponsored service deployment

Sponsored mode is an authenticated application service. It accepts only bounded advisory conversations for a server-selected model/output policy. It is not an arbitrary OpenAI proxy, requires no user OpenAI key or subscription, and starts **disabled with zero allowance**.

## Choose and prepare the host

For a managed deployment, use the prepared [Railway runbook](RAILWAY.md) and root `railway.json`. It keeps this same Python service and persistent SQLite accounting; the provider domain removes the need to purchase a domain. Hosting fees are separate from the application API allowance. The following Compose instructions remain available for an existing Linux host.

Use one small Linux host with persistent local storage, Docker Compose, a domain and a maintained HTTPS reverse proxy. The supplied Compose service binds only to localhost, runs as UID 10001, drops capabilities, has a read-only root filesystem and resource limits, and disables access logging. CI builds the actual container and verifies HTTP health, authentication, disabled access and revocation with no provider key or inference call. A real deployment still requires validation of the chosen host, secret mount and public HTTPS ingress before activation.

Keep the OpenAI funding key in the host/platform secret store, mounted read-only at `/run/secrets/openai_key`. Set `KOA_SERVER_SECRET_FILE` to its private host path for the local Compose secret adapter. Do not put the key in Compose YAML, an environment example, command-line arguments, GitHub release assets, images or the plugin. A managed host should map its own secret store to the same mount. Use a dedicated provider project/key.

Railway instead supplies the key as the sealed server variable `KOA_SERVER_OPENAI_KEY`, with the explicit `KOA_USE_SERVER_SECRET_ENV=true` adapter. Do not set `KOA_OPENAI_SECRET_FILE` at the same time. The secret is read only by server code (excluded from the client archive), is never returned to clients, and is not written to the ledger. The Dockerfile does not accept it as a build argument. A sealed variable is still available to the running server and platform administrators; protect that account and do not enable environment/body logging.

The mount must be readable by container UID 10001 and inaccessible to unrelated host users. Local Compose file secrets retain the source file's ownership/permissions: provision the dedicated secret file as UID/GID 10001 with mode 0400 (and a private parent directory), or use the platform secret store's equivalent access controls. Do not solve a permission error by making the key world-readable. Run the admin CLI through the container so its activation preflight checks readability under the same UID. It reads only bounded secret content and never prints it.

The Dockerfile and Compose default pin the official Python 3.11 slim-bookworm multi-platform manifest by digest, resolved on 2026-10-24. Review and deliberately update `PYTHON_BASE` for security updates; record any deployment override. Dependency packages are locked with hashes in `requirements-service.lock`. The client ZIP has a separate deterministic build.

From the repository on the host:

```sh
docker compose -f deploy/compose.yaml build
docker compose -f deploy/compose.yaml run --rm assistant python -m kicad_open_assistant.service.admin init
docker compose -f deploy/compose.yaml up -d
```

This starts the API disabled. `/healthz` is a process check, not proof of budget/secret readiness. Install the supplied Caddy example (or equivalent maintained ingress) with the real domain. Configure TLS and bounded body/header/read timeouts. Do not enable request-body or Authorization-header logging. Trust no client-supplied forwarding headers; the service uses the actual peer for a shared short-lived rate bucket, with additional authenticated user limits. Behind a single proxy that peer limit is shared, intentionally conservative.

## Funding and access

The owner must choose the **total lifetime deployment allowance in USD**, plus each user's allowance. These are cumulative limits, not monthly resets. Raising the total budget does not erase previous charges. All budget amounts use integer microdollars (1 USD = 1,000,000 units). Model policy is initially `gpt-4.1-mini-2025-04-14`, maximum 2048 output tokens. The server rejects any differing model or larger output limit, rather than silently changing the reviewed request.

Review current official prices, set an expiry date in `KOA_PRICE_VALID_UNTIL`, and configure `KOA_SPONSORED_ENABLED=true` **only after** the owner chooses the budget and deployment. Then use the offline admin CLI with an explicit allowance:

```sh
# Substitute the owner's approved numeric amount, never infer an unlimited budget.
docker compose -f deploy/compose.yaml exec assistant python -m kicad_open_assistant.service.admin enable --budget-usd APPROVED_AMOUNT
```

Issue each user a random access token through `service.admin issue USER_ID --allowance-usd APPROVED_USER_AMOUNT --token-file /private/output/user.token`, with a private writable output mount. The CLI writes a new file exclusively and does not print the token. Deliver that application token securely; users store it in the client's Windows Credential Manager. It is not the provider key. Reissue for the same ID to rotate access; accumulated charges remain. Revoke with `service.admin revoke USER_ID`. Inspect only that user's remaining allowance with `service.admin status USER_ID`.

## Spending and cancellation

Each request reserves the cost of the full model context window plus the maximum output at conservative published rates before making an inference call. This is deliberately larger than typical request cost; a very small allowance can reject a request until enough room exists for the reservation. Actual completed usage reconciles the reservation. Cached-input discounts are ignored, so accounted usage may slightly overstate provider cost.

Concurrent workers share one SQLite ledger with serialized durable transactions. There are four global and one per-user in-flight requests, six accepted requests per user per minute and a short-lived hashed-peer limit. Clients must supply an idempotency ID; replay never causes a second inference request. SDK retries are disabled. Errors/cancellations with unknown provider usage retain the full charge. If the service crashes, reserved charges remain and active slots are held until an operator investigates. Do not automatically expire/refund them.

The administrator kill switch is `service.admin kill`. It immediately blocks new reservations and is checked during active streaming. Set the environment enable flag back to false too for defense in depth. A missing/locked/corrupt ledger, expired pricing review, missing server secret, exhausted quota or budget fails closed. The client explains the failure and offers a deliberate switch to personal mode; it never resends automatically.

Uncertain reservations require comparison with provider usage before a manual, audited accounting correction. Version 0.1 does not automate refunds or reconciliation against provider invoices. Back up the ledger securely and restore only with a usage reconciliation: restoring an older ledger can otherwise recreate already-spent capacity. Never run separate independently writable copies or put SQLite on a network filesystem. Use provider-side spend controls as a second layer.

## Activation checklist

Confirm auth/revocation, user isolation, concurrent reservation limits, kill behavior, valid certificate, ingress/body timeouts, secret mounts, persistent volume/backup, exact image digest, pricing review expiry and the owner-approved budget. Run one bounded smoke request without design data and record it. The application tests mock inference by default; public source publication does not activate paid hosting.
