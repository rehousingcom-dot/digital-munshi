# Digital Munshi ERP — Build Plan

Source: "Digital Munshi ERP" presentation (8 slides). Yeh plan deck ke requirements ko
modules + phases mein todta hai. Approach: web-first (Django + REST API), local test → server.

---

## Module roadmap (deck ke according)

### Phase 1 — Foundation + Inventory  ✅ (ho gaya)
- **Accounts:** users, roles, JWT login
- **Core/Settings:** Company, settings-driven config (slide 2), Units, Tax rates, Godowns
- **Inventory (slide 5):** Items, primary+secondary unit & conversion, variants with auto
  unique item-code + barcode (size/colour/model wise), batch-wise MRP & discount,
  per-unit sale price, godown-wise stock

### Phase 2 — Party (Customer / Supplier)  ✅ (ho gaya)
Deck slide 4:
- Customer & supplier master, sundry debtors / creditors (opening balance + type)
- Document upload (PartyDocument)
- GSTIN format + checksum validation; legal name & address (government API baad mein)
- Duplicate party name/GSTIN check API

### Phase 3 — Sales & Purchase Billing  ✅ (ho gaya)
Deck slide 6, 7, 8:
- Sale/Purchase voucher with lines, price with/without tax per unit, billing from ANY unit
  (primary unit auto-calc from secondary via conversion)
- Multi-level discount (disc 1/2/3 + flat amount), sab WITHOUT-TAX amount pe apply
- Tax item-wise + transaction-wise; CGST/SGST (intra-state) vs IGST (inter-state) auto
- Stock auto-update on post; Purchase pe auto barcode + sale price via margin (amount/%)
- Auto voucher numbering (S/00001, P/00001)

### Phase 4 — Dashboard & Reports  ✅ (ho gaya)
Deck slide 3:
- Hot selling / slow selling items, Sales Trend, Profit Trend
- Slow Moving / Dead Stock, Cash Flow (receivables estimate), Stock valuation
- (Later) Voice-Based Business Management

### Phase 5 — Payments, Invoice, GST, Frontend  ✅ (ho gaya)
- Payment/receipt module + party ledger balance
- Invoice print (HTML) + PDF, amount in words
- GST report (output/input tax, B2B/B2C, net payable)
- Frontend UI (React via CDN) — login, dashboard charts, billing screen

### Phase 6 — SaaS / Multi-tenant  ✅ (ho gaya)
- Multi-tenant isolation (har business = alag organization, row-level scoping)
- Signup + 7-din free trial
- Subscription plans (Basic/Pro/Premium), monthly/yearly
- Razorpay billing (orders + signature verify) + DEV mode for local testing
- Expiry enforcement (402) + Subscribe page in frontend

### Phase 7 — All-Business Features  ✅ (ho gaya)
- Business-type profiles (Retail/Wholesale/Restaurant/Pharmacy/Services/Manufacturer/General)
  with per-type presets + Settings page (deck slide 2 "all changes from settings")
- GST scheme: Regular / Composition (Bill of Supply) / Unregistered
- Item types GOODS vs SERVICE; reorder level + low-stock alerts
- Document types: Estimate, Delivery Challan, Credit/Debit Note + estimate→invoice convert
- GSTR-1 (B2B/B2C/HSN) report
- Platform Admin panel — SaaS metrics (tenants, MRR, trials, revenue)

### Phase 8 — Aage (future)
- Razorpay auto-recurring (Subscriptions API + eMandate) for hands-free renewal
- GSTR-1 JSON export, e-invoice (IRN) + e-way bill (govt API)
- Barcode scanner billing, multi-godown stock transfer
- WhatsApp invoice share, loyalty, staff/payroll
- PostgreSQL + server deployment (Docker, Nginx, gunicorn)
- Desktop/mobile build, voice-based billing

---

## Tech decisions (confirmed)
- **Platform:** Web first → desktop/mobile later (same API base)
- **GSTIN:** abhi manual + format validation; paid verification API Phase 2+
- **Stack:** Django + DRF + PostgreSQL + (React frontend later)

---

## Build order
Items ✅ → Party → Billing (Sale/Purchase) → Dashboard → Reports → Frontend → Deploy
