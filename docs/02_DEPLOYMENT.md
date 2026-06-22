# 02 — Deployment (Railway) — Complete Reference

## Where it runs
- **Host:** Railway. Project **"superb-education"**, environment **production**.
- **Services:** `web` (the Django app) + `Postgres` (managed database).
- **web public URL:** https://web-production-9d149.up.railway.app
- **Custom domain:** https://erp.reloaddigital.in
- **Repo connected:** github.com/rehousingcom-dot/digital-munshi, branch `main`,
  **auto-deploy ON** (push to main → Railway builds & deploys automatically).

## How a deploy happens (the normal workflow)
```bash
cd ~/"ERP Munshi"
git add -A
git commit -m "describe change"
git push origin main          # ← Railway auto-builds + deploys (~2-3 min)
```
That's it. Watch in Railway → web → Deployments. Deploy stages:
Initialization → Build → Deploy → Post-deploy → **Online**.

## Build & run config (config-as-code: `railway.json`)
```json
{
  "build":  { "builder": "DOCKERFILE", "dockerfilePath": "Dockerfile" },
  "deploy": {
    "preDeployCommand": "python manage.py migrate --noinput",
    "startCommand":     "gunicorn config.wsgi:application -c gunicorn.conf.py",
    "restartPolicyType":"ALWAYS"
  }
}
```
- **Builder = DOCKERFILE** (NOT Railway's auto/nixpacks/mise — that broke, see troubleshooting).
- **Migrations** run as a separate **pre-deploy** step (before the container serves).
- **Container's main process = pure gunicorn** (PID 1, stays foreground). This is critical —
  combining `migrate && gunicorn` in the start command made the container exit ("Completed").
- **gunicorn.conf.py** binds `[::]:8080` (IPv6 dual-stack — Railway's internal network is
  IPv6; binding only IPv4 caused 502). Port fixed at **8080**.

## Railway service settings that matter
- **Networking → Public Networking → target port = 8080** (must match gunicorn bind).
- **Serverless = OFF** (keep container always running).
- **Restart policy = ALWAYS** (from railway.json).
- **Builder = Dockerfile** (from railway.json).

## Environment variables (Railway → web → Variables)
| Variable | Value | Why |
|---|---|---|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` | connects to managed Postgres (reference var) |
| `SECRET_KEY` | (long random string) | Django crypto. Currently a placeholder — rotate for real security |
| `DEBUG` | `False` | production mode (security on, no debug pages) |
| `ALLOWED_HOSTS` | `web-production-9d149.up.railway.app,.up.railway.app,erp.reloaddigital.in` | Django host validation. Add new domains here. |

Optional (for integrations, add when ready):
`RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `GSTIN_API_KEY`, `EMAIL_HOST`,
`EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, WhatsApp Cloud API token, `SECURE_SSL_REDIRECT`.

> ⚠️ Changing any variable triggers a redeploy. After adding a domain to ALLOWED_HOSTS,
> Django also auto-adds it to CSRF_TRUSTED_ORIGINS (settings.py does this from ALLOWED_HOSTS).

## First-time / one-off server tasks (Railway → web → Console)
The **Console** tab is a live shell inside the running container.
```bash
python manage.py createsuperuser     # make a Django admin (done: user "Nkgrewal")
python manage.py seed_plans          # seed subscription plans (run if plans empty)
python manage.py migrate             # usually auto (pre-deploy), manual only if needed
```
Don't type URLs in the Console — it's a shell, not a browser.

## Custom domain (erp.reloaddigital.in) — how it was set up
1. Railway → web → Settings → Networking → **Add Custom Domain** → `erp.reloaddigital.in`,
   target port **8080**. Railway gives 2 DNS records.
2. In **Cloudflare** (reloaddigital.in zone) added:
   - **CNAME**  `erp` → `0ffmpe1b.up.railway.app`  — **Proxy: DNS only (grey cloud)**.
   - **TXT**  `_railway-verify.erp` → `railway-verify=77c9375c8277...` (verification).
3. Railway verifies + issues free SSL (a few min → green tick). Site then serves https.
- Cloudflare proxy is **DNS only** so Railway can issue/renew SSL. (Can switch to Proxied
  later only with Cloudflare SSL/TLS mode = Full.)
- To add another domain: repeat in Railway, add CNAME+TXT in Cloudflare, add host to
  `ALLOWED_HOSTS` var.

## Rollback
Railway → web → Deployments → pick a previous successful deploy → "⋮" → Redeploy.
Or `git revert <commit>` and push.

## Backups
Railway managed Postgres has automatic backups (plan-dependent). Extra safety: weekly
manual DB dump (Railway → Postgres → Data/Connect, or `pg_dump` via Console using
`$DATABASE_URL`). See runbook.
