# Digital Munshi ERP — Kya-Kya Ho Chuka Hai (Work Summary)

_Last updated: 1 July 2026_

**Live app:** https://erp.reloaddigital.in
**Landing page:** https://erp.reloaddigital.in/welcome/
**GitHub:** github.com/rehousingcom-dot/digital-munshi · **Host:** Railway + Postgres

---

## 1. Core ERP (pehle se bana hua — foundation)

- **Billing & GST invoicing** — Tax invoice, estimate, proforma, sale order, delivery challan, credit/debit note, bill of supply. A4 + 58mm thermal print, PDF.
- **Inventory** — Items, variants (size/colour/model), multi-godown stock, batches, combos/BOM, serial/IMEI, price-lists, barcode.
- **Party (customer/supplier)** — Ledger, debtor/creditor, GSTIN verify, documents, opening balance, credit limit/days.
- **Payments & Udhaar** — Receipts/payments, allocation, party balance.
- **Accounting** — Double-entry, chart of accounts, journals, trial balance, bank reconciliation.
- **Cash & Bank** — Bank accounts, cheques, loans, expenses.
- **HR / Payroll** — Employees, attendance, leave, salary slips (PDF).
- **Reports** — P&L, balance sheet, GSTR-1/3B, HSN summary, day book, receivables aging, purchase register, live stock, low stock, party statement.
- **POS** — Fast quick-bill + thermal receipt.
- **Multi-firm** — Ek account me kai businesses, alag books.
- **SaaS** — Signup, 7-day trial, subscription plans, Razorpay billing, admin panel.

---

## 2. Deployment & Go-Live (LIVE ho gaya)

- Railway pe deploy — Dockerfile, gunicorn, WhiteNoise, auto-deploy on git push.
- Managed PostgreSQL connected.
- Custom domain **erp.reloaddigital.in** (Cloudflare + SSL).
- Admin panel + superuser.
- Signup/login CSRF → JWT fix; auto-logout bug fix (7-day access token + refresh).

---

## 3. Client Feedback Deck — saare 8 slides fix

- GST bug fix (18% ki jagah item ka apna rate).
- Billing UX — description column, unit column, row auto-open, tax toggle, inline party/item add.
- Invoice pe **bank details + UPI "Scan & Pay" QR**, image/doc upload.
- Estimate/Order/Challan → Invoice conversion (ek hi baar guard).
- **Challan → Invoice pe returned-qty prompt** (net delivered qty invoice).
- **Multi-batch grid** (ek saath kai batch), **batch-wise barcode**.
- Reports pe branded header + date-range filter.

---

## 4. Language (English + Hindi toggle)

- Poori ERP UI **English** me convert.
- **EN / हिं toggle button** — user choose kar sakta hai. Nav, dashboard, login, New Sale, Party, Items, Reports, Cash & Bank, Utilities, Accounting, HR — sab translate.

---

## 5. Email OTP (signup) — WORKING

- SMS ki jagah **email OTP**.
- Railway SMTP block karta hai → **Resend (HTTPS API)** se solve.
- Domain **reloaddigital.in** verified — kisi bhi customer email pe OTP jaata hai.

---

## 6. Razorpay Payments — WORKING (test mode)

- Full checkout: order → payment → server callback → signature verify → subscription activate.
- Pro plan (₹799) test payment successful.
- Popup/blank-tab issue → **redirect mode + server callback** se fix.
- PWA service worker disable (stale code hata).
- **Go-live:** website approval (submitted) ke baad Railway me LIVE keys swap — bas.

---

## 7. Cloudinary — Photos ab permanent

- Item photos / logo / documents ab **Cloudinary** pe (Railway restart pe nahi udhte).
- Confirmed working.

---

## 8. Nayi Improvements (aaj ka batch — sab live)

| Feature | Kya karta hai |
|---|---|
| **Auto DB backup** | Roz raat poora data JSON Cloudinary pe + email link (cron-job.org se 8 PM) |
| **Daily sales summary** | Har owner ko shaam ko aaj ki bikri/kharid/top-item email |
| **Dead / Fast movers report** | Kaunsa maal ruka, kaunsa jaldi bikta (Reports tab) |
| **Camera barcode scan** | New Sale me 📷 Camera button — phone/laptop camera se scan |
| **Error monitoring (Sentry)** | Production bugs turant pata (SENTRY_DSN env se on) |
| **Online Catalog** | Public shop link (/shop/...) — customer WhatsApp par order kare |
| **Loyalty points** | Har ₹100 bikri pe 1 point auto; Party + New Sale me dikhta |
| **Marketing landing + SEO** | /welcome/ page + robots.txt + sitemap.xml + meta tags |
| **Party ledger PDF + WhatsApp** | Customer statement PDF, seedha WhatsApp pe share |

---

## 9. Ab Bacha Kya Hai

**Key/account milne pe (main kar dunga):**
- Razorpay **LIVE keys** — website approval ke baad swap (code ready).
- **GSTIN verify API** — party name/address auto-fill.
- **WhatsApp Cloud API** — invoice/reminder auto-send.
- Optional: Shopify, Shiprocket, e-invoice/e-way live.

**Sirf aapko karna hai (Security — zaroori):**
- GitHub PAT **revoke**.
- Gmail app-password, Resend key, Razorpay test-key, Cloudinary secret **rotate**.
- `SECRET_KEY` ko strong unique value se badalna.

---

_Sab code GitHub pe commit + Railway pe auto-deploy. Detail docs `docs/` folder me._
