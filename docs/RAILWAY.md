# Railway deployment

This target runs the existing Python service on one container with a persistent volume and a Railway HTTPS domain. The deployment template is prepared; a public Railway deployment is not yet verified. Do not interpret a local/container test as proof that public ingress, billing controls or platform secrets are configured.

## Account, costs and persistence

Use an owner-controlled Railway account and a dedicated project/service named `kicad-open-assistant`. Hobby starts at $5/month, including $5 resource usage, with additional usage billed separately. Obtain the owner's hosting spending limit separately from their lifetime OpenAI allowance. Before deploying, set the workspace's **Compute hard usage limit** and an earlier alert. Use a dedicated workspace if the limit would otherwise shut down unrelated services. Do not start a Railway agent or enable paid add-ons. The limit does not cancel the subscription or govern OpenAI spending. Verify current billing terms and any taxes in the account.

Create one volume mounted at `/data`, initially 1 GB if offered. Keep **one replica in one region**, with the supplied 1 CPU/1 GiB ceiling. Never clone a funded ledger into another writable instance. Backups require the reconciliation procedure in [BACKEND.md](BACKEND.md) before restoration; an old backup can otherwise recreate spent capacity.

The root `railway.json` selects the pinned Dockerfile, port-8000 service start, required mount, health check, single replica and resource ceilings. Verify those settings in the resulting deployment. Do not use a pre-deploy command to initialize the ledger: Railway mounts the volume at runtime. The startup adapter refuses an absent mount, prepares only `/data/koa`, then drops to UID/GID 10001 **before** opening the HTTP listener. First boot must be disabled. Later boots preserve charges, access records and the kill switch. Missing funded accounting is never replaced automatically.

## Deploy disabled

1. Connect the public GitHub repository to this dedicated service. Disable automatic PR environments and require an explicit reviewed commit for production deployments; do not send funding secrets to unreviewed builds.
2. Attach `/data` and set the non-secret variables from `deploy/railway.variables.example`. Keep `KOA_SPONSORED_ENABLED=false` and the expired pricing date. `RAILWAY_RUN_UID=0` is only for volume preparation; the HTTP process drops privileges. The application ledger path must be `/data/koa/ledger.sqlite3`.
3. Deploy the reviewed commit. Check health, actual runtime UID 10001, volume ownership and the disabled zero-budget ledger. A missing mount or invalid permissions must fail startup. Configure the generated Railway domain with target port **8000**; use HTTPS in the client. Do not add a TCP proxy.
4. Verify the certificate, `/healthz`, unauthenticated rejection, disabled authenticated access, revocation, and persistence through redeployment. The health endpoint checks the process only. Check NDJSON streaming and cancellation through the real edge before enabling users. The service itself limits bodies to 30 MiB, body reads to 30 seconds, streams to 180 seconds and HTTP concurrency to 8; four inference reservations may be active globally. Forwarded client IP headers are deliberately not trusted.

## Provision secrets and activate deliberately

The owner installs a dedicated OpenAI funding key **directly in Railway**, as the sealed service variable `KOA_SERVER_OPENAI_KEY`. Never enter it in this repository, a build argument, shell command, client dialog or chat. `KOA_USE_SERVER_SECRET_ENV=true` selects this adapter; leave `KOA_OPENAI_SECRET_FILE` unset. Seal the variable before normal operation. Railway's sealed variables are not returned by its UI/API or local `railway run`, although they are available to the deployed server. Do not dump environments or turn on request/Authorization logging.

Review official model pricing and set a short, explicit `KOA_PRICE_VALID_UNTIL`. The default server model and conservative reservation policy are described in BACKEND.md. From a remote shell **inside the deployed container**, run the administrator CLI as UID/GID 10001, using the owner-approved amounts:

```sh
python -m kicad_open_assistant.service.admin enable --budget-usd APPROVED_TOTAL
python -m kicad_open_assistant.service.admin issue USER_ID --allowance-usd APPROVED_PER_USER --token-file /data/koa/USER_ID.token
```

These placeholders are intentional: a new operator must choose their own allowance. Tokens are written exclusively with private permissions and never printed. Retrieve each application token through an authenticated secure transfer and deliver it privately. Do not expose the volume as a web directory. Rotate/revoke tokens using BACKEND.md. Reissuing the same stable user ID preserves usage; do not issue multiple IDs to bypass a person's allowance. Invitation-only access is the initial abuse-control boundary; there is no public self-signup endpoint.

If the platform's remote shell starts as root, use `runuser -u assistant --` before these commands. `KOA_LEDGER` must still name the deployed volume. Do not use local `railway run` for administration: it is a different machine and cannot access the deployed accounting database.

After all preflight checks, set `KOA_SPONSORED_ENABLED=true` and redeploy. Run only the explicitly approved bounded smoke request with no design data. Record its usage and verify that it reduces the same lifetime ledger. Confirm the kill switch, user isolation and exhaustion behavior. No automatic retries or alternate-destination sends occur. Exhausted users can deliberately switch to their own personal key.

The kill switch is `python -m kicad_open_assistant.service.admin kill` on the deployed ledger; also reset the environment flag to false. Do not reset the database, budget or user IDs on billing-cycle boundaries. A hosting outage or hard-limit shutdown leaves uncertain reservations charged and fails sponsored requests closed.

## Official references reviewed 2026-10-24

- [Pricing](https://docs.railway.com/pricing/plans) and [hard cost controls](https://docs.railway.com/pricing/cost-control).
- [Volumes and non-root permissions](https://docs.railway.com/volumes/reference).
- [Configuration as code](https://docs.railway.com/config-as-code/reference) and [configuration schema](https://railway.com/railway.schema.json).
- [Sealed variables](https://docs.railway.com/variables#sealed-variables).
- [HTTPS domains](https://docs.railway.com/networking/public-networking) and [edge limits](https://docs.railway.com/networking/public-networking/specs-and-limits).
