# Digital Munshi ERP — Review & Improvement Roadmap

Yeh meri (Claude ki) poore software ki honest review hai aur aage ke improvements,
priority ke hisaab se. Abhi software **kaafi complete aur tested** hai — yeh list isse
ek serious production product banane ke liye hai.

---

## ✅ Abhi kya solid hai
- Multi-tenant SaaS (data isolation), 7-din trial, Razorpay subscription
- Billing (multi-unit, multi-discount, CGST/SGST/IGST), inventory, party ledger, payments
- 8 business-type profiles + granular settings (Vyapar-style)
- Documents: Invoice/Estimate/Challan/Credit-Debit Note, Bill of Supply
- GST + GSTR-1 reports, dashboard, low-stock, WhatsApp share, invoice PDF
- 19/19 regression tests pass, JSX clean, koi known bug nahi

---

## A. Production-Readiness (asli customers se pehle — IMPORTANT)
1. **Automated test suite** — abhi maine manually test kiya hai; Django `tests.py` (pytest)
   likhna chahiye taaki har change pe auto-verify ho (CI).
2. **Pagination** — items/parties/vouchers ki list endpoints poora data dete hain. Hazaaron
   records pe slow. DRF pagination enable karna (frontend ko thoda adjust karna hoga).
3. **Role-based permissions enforce** — abhi role (Admin/Accountant/Operator/Viewer) store hota
   hai par enforce nahi. Viewer ko sirf read, Operator ko billing-only, etc. enforce karna.
4. **HTTPS + production settings** — `DEBUG=False`, proper `ALLOWED_HOSTS`, secure cookies,
   `SECRET_KEY` env se (script ab auto-set karti hai).
5. **Rate limiting** — signup/login pe throttling (abuse/brute-force se bachne ke liye).
6. **Backups** — PostgreSQL daily backup + restore process.
7. **Audit log** — kis user ne kya change kiya (compliance + trust).

## B. High-Value Features (Indian market — revenue badhane wale)
1. **E-Invoice (IRN) + E-Way Bill** — B2B/turnover-based mandatory. Govt API integration.
2. **Barcode scanner billing** — scan karke item turant add (POS speed). Hardware + UI.
3. **Razorpay auto-recurring** — abhi har period manually pay karna padta hai; Subscriptions
   API + eMandate se auto-renew (churn kam).
4. **Reports** — P&L, Day Book, Party Statement (PDF), Stock Summary, Purchase register.
5. **Import/Export** — items/parties Excel se import, data CSV/Excel export.
6. **Payment-to-invoice allocation** — abhi payment party-level hai; invoice-wise allocation +
   aging report (30/60/90 days).
7. **WhatsApp Business API** — auto-send (bina click). Settings me token field ready hai.
8. **Multi-user invite** — owner apne staff ko invite kare (abhi ek hi user per org).

## C. UX / Polish
1. **Mobile-responsive SPA** — sidebar mobile pe collapse, billing screen touch-friendly.
2. **Hindi/English UI toggle** — bahut se dukaandaar Hindi prefer karte hain.
3. **Invoice template options** — logo upload, theme/colour, multiple formats (thermal/A4).
4. **Keyboard shortcuts** in billing (fast data entry — Vyapar ka strong point).
5. **Better number formatting** (Indian ₹ lakh/crore) — partly done.

## D. Engineering Quality
1. **Proper frontend build** — abhi SPA ek single HTML hai (Babel browser me = first load slow).
   Production ke liye Vite/React build (fast, code-split).
2. **Background jobs** (Celery) — bulk WhatsApp, report generation, email.
3. **API docs** (Swagger/OpenAPI) — for integrations.
4. **Error monitoring** (Sentry) + structured logging.

---

## Suggested order (mera recommendation)
1. **Abhi**: Mac pe local test karein (`./run_local.sh`), demo data se sab features dekhein.
2. **Next**: automated tests + role permissions + pagination (production base).
3. **Phir**: E-invoice/E-way bill + barcode billing + better reports (market features).
4. **Phir**: PostgreSQL + server deploy + auto-recurring billing (go-live).
5. **Polish**: mobile UI, Hindi, invoice templates.

> Recently fixed (review me): negative-stock enforcement, posted-voucher edit block.

---

## ✅ Is round me BUILD ho gaya (roadmap se)
**Production base:** role-based permissions (Admin/Accountant/Operator/Viewer enforce), audit log,
API pagination, rate-limiting (throttle), production security settings, **automated test suite (6 tests pass)**,
**Swagger API docs** (`/api/docs/`).

**Market features:** P&L, Day Book, Party Statement, Purchase Register, **Receivables Aging**,
payment-to-invoice **allocation**; **E-Invoice (IRN) + E-Way Bill JSON** (govt schema, upload-ready);
**barcode scan** billing; **multi-user staff** invite; **CSV import/export** (items & parties); invoice **logo** upload.

**Billing/WhatsApp groundwork:** Razorpay **auto-recurring** (Subscriptions API code + webhook, dev-mode active);
**WhatsApp Business Cloud API** send (token-based, wa.me fallback).

**Frontend:** **mobile-responsive** + collapsible sidebar, **barcode field** in billing, Reports screen,
Staff management screen, import/export + logo buttons.

## ⏳ Abhi bhi baaki (infra / credentials chahiye)
- **Live govt e-invoice/e-way API** (GSP/NIC credentials) — abhi JSON ready, upload manual.
- **Live WhatsApp Cloud API** (Meta verified number + token) — code ready, token chahiye.
- **Live Razorpay recurring** (eMandate + webhook secret) — code ready, keys chahiye.
- **Full Hindi UI translation** (abhi Hinglish labels) — bada i18n kaam, alag se.
- **Vite/React production build**, Celery background jobs, Sentry — deployment-time infra.
- PostgreSQL + server deployment.
