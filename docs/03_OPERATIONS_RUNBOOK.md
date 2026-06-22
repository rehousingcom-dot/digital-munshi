# 03 — Operations Runbook (day-to-day server tasks)

## Deploy a code change
```bash
cd ~/"ERP Munshi"
git add -A && git commit -m "what changed" && git push origin main
```
Railway auto-deploys. Verify: Railway → web → Deployments → wait for **Online**, then
hard-refresh the site (Cmd+Shift+R).

## ALWAYS verify the React SPA before pushing frontend changes
`templates/app.html` is transpiled in the browser — one JSX typo = blank white app.
Before pushing edits to it, transpile-check locally:
```bash
cd ~/"ERP Munshi"
node -e '
const fs=require("fs");let h=fs.readFileSync("templates/app.html","utf8");
const m=[...h.matchAll(/<script[^>]*type="text\/babel"[^>]*>([\s\S]*?)<\/script>/g)];
let code=m.map(x=>x[1]).join("\n").replace(/\{%\s*verbatim\s*%\}/g,"").replace(/\{%\s*endverbatim\s*%\}/g,"");
require("@babel/standalone").transform(code,{presets:["react"]});
console.log("JSX OK");'
```
(Needs `npm install @babel/standalone` once. If "OK", safe to push.)

## Run a command on the production server
Railway → web → **Console** tab → live shell in the container:
```bash
python manage.py createsuperuser      # new admin login
python manage.py seed_plans           # seed subscription plans
python manage.py shell                # Django shell for data fixes
python manage.py changepassword <user>
```

## Make/verify the admin
- URL: https://web-production-9d149.up.railway.app/admin/ (or erp.reloaddigital.in/admin/)
- Existing superuser: **Nkgrewal** / email admin@reloaddigital.in.
- Make another: Console → `python manage.py createsuperuser`.

## Inspect / run the app locally (dev)
```bash
cd ~/"ERP Munshi"
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate              # SQLite by default (no DATABASE_URL)
python manage.py runserver            # http://127.0.0.1:8000
```
Local uses SQLite + DEBUG=True automatically (no env needed). To mimic prod, set env:
`DEBUG=False SECRET_KEY=x ALLOWED_HOSTS=* gunicorn config.wsgi -c gunicorn.conf.py`.

## Database backup (manual)
Railway → Postgres service → "Connect"/"Data". Or via web Console:
```bash
pg_dump "$DATABASE_URL" > /tmp/backup.sql   # then download via Console file panel
```
Do this weekly until automated backups are confirmed on the plan.

## Check logs
Railway → web → Deployments → open deployment → **Deploy Logs** (runtime), **Build Logs**
(build), **HTTP Logs** (requests + status codes). NOTE: gunicorn access logs are ON.
(During the June 2026 Railway logging incident, logs were delayed — that was Railway-side.)

## Health checks
- Site loads (login page) at the live URL = web container healthy.
- Railway → web → Console showing a running instance (not "No running instances") = up.
- `web` card shows **Online** (not "Completed"/"Crashed").

## Adding a new business (customer) — normal flow
Customer goes to the site → **"Sign up free"** → fills business name, type, username,
password → gets 7-day trial + JWT → lands in dashboard. (No admin action needed.)

## Common gotchas (see 04_TROUBLESHOOTING_LOG.md for full stories)
- 502 "Application failed to respond" → container not serving on [::]:8080 / not running.
- "DisallowedHost" → add the host to `ALLOWED_HOSTS` var.
- "CSRF Failed" on signup → already fixed (JWT-only auth); don't re-add SessionAuthentication.
- White/blank app → JSX syntax error in app.html; transpile-check + fix.
