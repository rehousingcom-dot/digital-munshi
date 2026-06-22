# CLAUDE.md — Master Context (READ THIS FIRST)

> Future session ke liye: yeh file sabse pehle padho. Yahan poore project ka quick
> orientation hai. Detail ke liye `docs/` folder dekho.

---

## 1. Project kya hai

**Digital Munshi ERP** — ek **multi-tenant SaaS** hai Indian SMBs (kirana, wholesale,
restaurant, pharmacy, services, manufacturer) ke liye. Vyapar / Swipe / Zoho Books /
Tally ka competitor.

Ek hi app me: **Billing + GST invoicing, Inventory, Payments/Udhaar, Accounting
(double-entry), HR/Payroll, POS, Reports/GSTR, Multi-firm**.

- **Brand naam (UI me):** Digital Munshi
- **Tagline:** "Billing software nahi, aapka digital Munshi."
- **Language/tone:** Hinglish (Hindi in Latin script) — audience Indian shopkeepers.

## 2. Live kahan hai

| Cheez | Value |
|---|---|
| Live URL (Railway) | https://web-production-9d149.up.railway.app |
| Custom domain | https://erp.reloaddigital.in (Cloudflare CNAME, SSL provisioning) |
| Admin panel | `/admin/` — superuser **Nkgrewal** (admin@reloaddigital.in) |
| GitHub repo | https://github.com/rehousingcom-dot/digital-munshi (branch `main`) |
| Host | **Railway** — project "superb-education", service "web" + "Postgres" |
| Database | Railway managed **PostgreSQL** (prod) / SQLite (local dev) |

## 3. Tech stack

- **Backend:** Django 5.0 (prod, Python 3.12) / Django 4.2 (local, Python 3.9+), Django REST Framework, **JWT auth** (djangorestframework-simplejwt).
- **DB:** PostgreSQL (prod via `DATABASE_URL`), SQLite (local default).
- **Frontend:** Single-file **React SPA** in `templates/app.html` (~2200 lines) — React 18 UMD + Babel-standalone + Tailwind CDN + Chart.js + JsBarcode. NO build step.
- **Server:** gunicorn + WhiteNoise (static). Containerized via **Dockerfile**.
- **Deploy:** Railway (Dockerfile builder), auto-deploy on `git push`.

## 4. Sabse zaroori: deploy kaise hota hai

```bash
# Local pe change karo, phir:
cd ~/"ERP Munshi"
git add -A && git commit -m "kya change kiya"
git push origin main
# → Railway KHUD build + deploy kar deta hai (~2-3 min). Bas.
```

Server pe commands chalane ke liye (migrate auto chalta hai, par manual zaroorat ho to):
**Railway dashboard → web service → "Console" tab** → ek Linux shell milta hai container ke andar. Wahan `python manage.py <cmd>` chalao (e.g. `createsuperuser`, `seed_plans`).

⚠️ Console me **URL mat type karo** — woh shell hai. URLs browser me.

## 5. Apps (Django) — `apps/` folder

`tenants` (org/plan/subscription, signup, billing), `accounts` (User+roles+audit),
`core` (Company, settings, godown, tax, units), `inventory` (items, batches, stock,
combos/BOM, serial/IMEI, price-lists — 10 models), `party` (customer/supplier),
`billing` (Voucher/invoice, recurring, CESS, multi-currency), `payments`,
`cashbank` (bank, expense, cheque, loan), `accounting` (chart of accounts, journals,
trial balance), `hr` (employee, attendance, leave, payroll), `reports`.

## 6. Current status (June 2026)

✅ **LIVE & working:** deploy successful, Postgres connected, admin works, signup/login
fixed (CSRF), custom domain added, login page redesigned (premium marketing).

🔜 **Pending / next:** integrations (Razorpay LIVE keys, GSTIN API, WhatsApp Cloud API,
Shopify, Shiprocket, email SMTP), custom domain SSL final verify, seed subscription plans.

⚠️ **SECURITY TODO:** ek GitHub PAT (`ghp_...`) chat me expose hua tha — **revoke karo**
GitHub → Settings → Developer settings → Personal access tokens.

## 7. docs/ folder index

- `docs/00_PROJECT_OVERVIEW.md` — product, modules, full feature list.
- `docs/01_ARCHITECTURE.md` — code structure, multi-tenancy, models, frontend.
- `docs/02_DEPLOYMENT.md` — Railway setup A-to-Z, env vars, custom domain, redeploy.
- `docs/03_OPERATIONS_RUNBOOK.md` — server commands, backups, common tasks.
- `docs/04_TROUBLESHOOTING_LOG.md` — deploy ke saare bugs + unke fix (zaroor padho).
- `docs/05_STATUS_AND_ROADMAP.md` — kya ho gaya, kya baaki, integrations plan.

Purane docs (reference): `PROJECT_PLAN.md`, `IMPROVEMENTS.md`,
`MARKET_AND_MARKETING_PLAN.md`, `TESTING_CHECKLIST.md`, `DEPLOY_GUIDE.md`, `README.md`.
