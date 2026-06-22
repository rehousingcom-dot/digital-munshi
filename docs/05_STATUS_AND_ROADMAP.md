# 05 — Status & Roadmap

_Last updated: 23 June 2026 (deployment day)._

## ✅ DONE (live & working)
- Full ERP built: billing/GST, inventory, parties, payments, cash/bank, accounting, HR/payroll,
  POS, reports, multi-tenancy, multi-firm, subscriptions (7 "Waves" of features — see CHANGELOG/IMPROVEMENTS.md).
- **Deployed to Railway** with managed PostgreSQL. Auto-deploy on `git push`.
- App **LIVE** at https://web-production-9d149.up.railway.app.
- **Custom domain** https://erp.reloaddigital.in added (Cloudflare CNAME + TXT; SSL provisioning).
- Admin panel working; superuser **Nkgrewal** created.
- Signup/login fixed (CSRF → JWT-only auth).
- **Login/signup page redesigned** — premium marketing hero, features, testimonial, password
  toggle, brand-orange CTA (commit `c540cc8`).

## 🔜 IMMEDIATE NEXT (small)
1. **Verify custom domain SSL** — check Railway shows green tick on erp.reloaddigital.in;
   site loads over https with a lock. (DNS/SSL may take up to ~30 min.)
2. **Seed subscription plans** if not done: Console → `python manage.py seed_plans`
   (so the Subscribe page shows real plans). Verify a fresh signup → trial flow end-to-end.
3. **Rotate SECRET_KEY** to a strong unique value (current is a placeholder).
4. **⚠️ Revoke the exposed GitHub PAT** (Settings → Developer settings → tokens).
5. Smoke-test the live app: signup → create item → create invoice → print/PDF/WhatsApp →
   payment → report. Fix anything that breaks in production (prod = Postgres + DEBUG=False).

## 🧩 INTEGRATIONS (the "bad me karenge" list — needs API keys + live server, which we now have)
Add each key as a Railway env var, then wire/enable:
- **Razorpay LIVE** — `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET` for real subscription payments
  (currently dev-mode without keys). Recurring billing already coded.
- **GSTIN verify API** — `GSTIN_API_KEY` (Appyflow/MasterGST) → auto-fill party name/address.
- **WhatsApp Cloud API** — token for sending invoices via WhatsApp (share link already works).
- **Email (SMTP)** — `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` → invoice email,
  password reset.
- **Shopify** — order/product sync (for online sellers).
- **Shiprocket** — shipping/logistics.
- (Optional) e-invoice / e-way bill live API (JSON export already built).

## 🚀 GROWTH / PRODUCT BACKLOG
- Marketing landing page (separate from app login) + pricing page + SEO.
- Onboarding wizard for new businesses (sample data, guided first invoice).
- Mobile app / PWA polish.
- More reports, GST filing automation, bank feed import.
- Team/role management UI polish, notifications.
- See `MARKET_AND_MARKETING_PLAN.md` for go-to-market.

## How to resume work tomorrow (checklist)
1. Read `CLAUDE.md` then this file.
2. `cd ~/"ERP Munshi"` → `git pull` (in case) → make changes.
3. For frontend (`templates/app.html`) changes: transpile-check (runbook) before push.
4. `git add -A && git commit -m "..." && git push origin main` → Railway auto-deploys.
5. Server tasks: Railway → web → Console.
6. Verify on the live URL with a hard refresh.
