# 04 — Troubleshooting Log (deploy bugs & their fixes)

> These are REAL problems hit while first deploying to Railway (June 2026) and exactly how
> each was fixed. If a similar symptom returns, the fix is here. Don't undo these fixes.

## Git push: "denied" / "Invalid username or token"
- Cause: Mac keychain cached the wrong GitHub account; literal placeholders pasted.
- Fix: push with token embedded in remote URL for the correct owner:
  `git remote set-url origin https://rehousingcom-dot:<PAT>@github.com/rehousingcom-dot/digital-munshi.git`
- ⚠️ The PAT used was exposed in chat — **revoke it** and create a fresh one if needed.

## Build FAILED — `mise ERROR ... No GitHub artifact attestations for python@3.12.6`
- Cause: `runtime.txt` (python-3.12.6) made Railway's Railpack/mise builder try to install
  that exact python and fail on attestation.
- Fix: **deleted `runtime.txt`** and forced the **Dockerfile** builder via `railway.json`
  (`"builder": "DOCKERFILE"`). Commit `7fcc0b1`.

## Container CRASHED — `Error: '$PORT' is not a valid port number`
- Cause: the start command passed the literal string `$PORT` to gunicorn (Railway didn't
  shell-expand it).
- Fix: gunicorn reads PORT from the environment in Python via `gunicorn.conf.py`
  (no shell `$PORT`). Commit `4f8c12a`.

## 502 "Application failed to respond" (build OK, migrations OK, but no response)
- Root cause: **Railway's internal network is IPv6.** gunicorn bound only to `0.0.0.0`
  (IPv4), so Railway's edge proxy couldn't reach it → 15s timeout → 502.
- Fix: bind gunicorn to **`[::]` (IPv6 dual-stack, accepts IPv4 too)**. `gunicorn.conf.py`:
  `bind = "[::]:8080"`. Commits `d42242c`, `25595db`. Also set Railway target port = 8080.
- Verified locally: `gunicorn config.wsgi -c gunicorn.conf.py` → `Listening at http://[::]:8080`.

## Container shows "Completed" / Console "No running instances" (process exits)
- Cause: start command was `migrate && gunicorn ...`; after migrate the wrapper/exit
  behaviour left no long-running process → container ended (exit 0 = "Completed") →
  every request 502.
- Fix: **separate concerns** — migrations as `preDeployCommand`, and the container runs
  **pure gunicorn** (`startCommand: gunicorn config.wsgi:application -c gunicorn.conf.py`),
  which stays foreground as PID 1. Set `restartPolicyType: ALWAYS`. Commit `eff1fb9`.
- Also pinned `gunicorn==21.2.0` (stable) to avoid a brand-new gunicorn's control-socket
  quirk. Commit `1ce0ea3`.

## "DisallowedHost: Invalid HTTP_HOST header"
- Cause: `ALLOWED_HOSTS` env var not set → Django rejected the Railway/custom domain.
- Fix: set `ALLOWED_HOSTS = web-production-9d149.up.railway.app,.up.railway.app,erp.reloaddigital.in`.
  Also set `DATABASE_URL`, `SECRET_KEY`, `DEBUG=False`. App went live.

## "CSRF Failed: CSRF token missing" on Sign up / Login
- Cause: DRF default auth included **SessionAuthentication**. When an admin session cookie
  was present (logged into /admin in same browser), DRF enforced CSRF on the JSON POST,
  which the SPA doesn't send → rejected.
- Fix: removed SessionAuthentication — DRF now **JWT-only** (the SPA uses Bearer tokens, no
  CSRF needed). Added `CSRF_TRUSTED_ORIGINS` (auto-built from ALLOWED_HOSTS). Commit `7fee3bb`.
- Do NOT re-add SessionAuthentication to `DEFAULT_AUTHENTICATION_CLASSES`.

## Railway logging incident (June 22-23, 2026)
- "Logs and metrics may be slow to load" banner — a Railway-side incident, not our bug.
  It hid gunicorn logs during debugging. Serving was unaffected once config was correct.

## Key invariants to keep (don't regress)
- Builder = Dockerfile (railway.json). No `runtime.txt`.
- gunicorn binds `[::]:8080`; Railway target port = 8080.
- migrate = preDeploy; start command = pure gunicorn; restart ALWAYS.
- DRF auth = JWT only; CSRF_TRUSTED_ORIGINS from ALLOWED_HOSTS.
- Env vars present: DATABASE_URL, SECRET_KEY, DEBUG=False, ALLOWED_HOSTS.
