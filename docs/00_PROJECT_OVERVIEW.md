# 00 — Project Overview

## What it is
**Digital Munshi ERP** is a multi-tenant SaaS for Indian small & medium businesses.
One subscription gives a business everything to run their shop: GST billing, inventory,
payments/credit (udhaar), accounting, HR & payroll, POS, and reports — all in the cloud,
accessible from any browser or phone.

**Positioning:** competitor to Vyapar, Swipe, Zoho Books, Tally — but cloud-first,
Hinglish UI, simple enough for a kirana shopkeeper, deep enough for a wholesaler.

## Target users (business types)
Retail/Kirana, Wholesale/Distributor, Restaurant/Cafe, Pharmacy/Medical,
Services/Professional, Manufacturer, General. (Set at signup; presets configure defaults.)

## Business model
- **SaaS subscription** per business (Organization). 7-day free trial on signup.
- Plans (Free/Basic/Pro etc.) with per-plan limits (e.g. max users). Billing via Razorpay.
- Multi-firm: one user can own multiple businesses (separate books each).

## Full feature list (built)

### Billing & GST
- Sales/Purchase invoices (Voucher model), GST-compliant (CGST/SGST/IGST, CESS).
- Document types: Invoice, Estimate/Quotation, Delivery Challan, Credit/Debit Note,
  Bill of Supply, Purchase, Purchase Return.
- Free quantity, discounts, multiple tax rates, MRP-based tax, round-off.
- **Multi-currency** invoices (exchange rate).
- **Recurring invoices** (weekly/monthly/quarterly/yearly auto-generate).
- Invoice **print + PDF** (xhtml2pdf), **WhatsApp share**, public share link (customer portal).
- **Thermal print** (58mm) for POS.
- E-invoice / E-way bill JSON export.

### Inventory
- Items (goods/services), categories, units, HSN, barcode.
- Batches, stock tracking, low-stock & reorder alerts, live stock report.
- **Combos / BOM** (bundle items — stock explodes to components on sale).
- **Serial / IMEI** tracking.
- **Price lists** (per-customer/segment pricing).
- Custom fields (JSON) on items.
- CSV import/export.

### Parties (customers/suppliers)
- Customer & supplier master, GSTIN verify (auto-fill name/address via API when key set).
- Debtor/creditor balances, party documents, custom fields, party groups.
- Public share UUID per party.

### Payments & Cash/Bank
- Payment receipts/vouchers, **payment allocation** to invoices, udhaar (credit) tracking.
- **Payment reminders** (auto).
- Bank accounts, bank transactions + reconciliation, cheques, expenses + categories,
  loan accounts.

### Accounting (double-entry)
- Chart of Accounts (16 default accounts auto-seeded), Journal entries (debit=credit
  validation), Trial Balance, ledgers.

### HR & Payroll
- Employees, attendance, leave, payroll generation, **payslip PDF**.

### Multi-tenancy & SaaS
- Organization / Plan / Subscription models, trial + subscription enforcement middleware.
- Per-plan user limits. Staff users with roles (RBAC) + audit log.
- Platform admin SaaS panel (MRR, signups, churn metrics) at `/admin` + custom metrics API.
- Multi-firm switching.

### Frontend / UX
- Single-page React app, mobile responsive, Hindi/English toggle.
- Command palette (Ctrl+K), barcode/label designer, dashboard with charts.
- Premium marketing login/signup page.

## Tech summary
Django 5 + DRF + JWT, PostgreSQL, React SPA (single file), gunicorn + WhiteNoise,
Docker on Railway. See `docs/01_ARCHITECTURE.md`.
