# Digital Munshi ERP

> "Billing software nahi, digital Munshi jo aapka poora business sambhale."

Web-based billing + inventory + GST accounting ERP for Indian SMBs.
Backend: **Django + Django REST Framework**. Database: **SQLite** (local) / **PostgreSQL** (server).

---

## Mac pe local setup (step by step)

Terminal kholo aur project folder mein jao:

```bash
cd "/Users/mrgrewal/ERP Munshi"
```

### 1. Setup ke dauraan bane leftover files hatao (ek baar)
```bash
rm -rf .venv db.sqlite3 db.sqlite3-journal
```
(Ye files build/test ke waqt bani thi — Mac pe fresh banengi.)

### 2. Naya virtual environment banao aur activate karo
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Dependencies install karo
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Environment file banao
```bash
cp .env.example .env
```
`.env` kholo aur `SECRET_KEY` ko koi lambi random string se badal do.
(Local test ke liye `DATABASE_URL` khaali chhod do — SQLite use hoga.)

### 5. Database tables banao
```bash
python manage.py migrate
```

### 6. Subscription plans daalo (SaaS billing)
```bash
python manage.py seed_plans
```

### 7. Platform admin (aapke liye) banao — optional
```bash
python manage.py createsuperuser   # /admin/ ke liye, saare tenants dekhne ke liye
```

### 8. Server chalao
```bash
python manage.py runserver
```

Ab browser mein kholo:
- **App:** http://127.0.0.1:8000/  ← yahan **Sign up** karke (7-din free trial) business banao, phir billing/dashboard use karo
- **Platform admin:** http://127.0.0.1:8000/admin/  ← aap (SaaS owner) ke liye — tenants, plans, payments

Har naya business signup pe apne default units/GST-slabs/godown ke saath ban jaata hai. `seed_base` ki ab zaroorat nahi (woh single-tenant dev ke liye tha).
- **Admin panel (data add/edit):** http://127.0.0.1:8000/admin/
- **API health check:** http://127.0.0.1:8000/api/health/
- **API root:** http://127.0.0.1:8000/api/

---

## Abhi tak kya ban chuka hai

| Module | Status | Kya hai |
|--------|--------|---------|
| Accounts | Done | Users + roles (Admin / Accountant / Operator / Viewer), JWT login |
| Core / Settings | Done | Company, Settings (key-value), Units, Tax rates, Godowns |
| Inventory | Done | Items, primary/secondary unit + conversion, variants (size/colour/model) with **auto item-code & barcode**, batch-wise MRP & discount, per-unit sale price, godown-wise stock |
| Party | Done | Customer/Supplier, debtors/creditors (opening balance), **GSTIN format+checksum validation**, document upload, duplicate-name check |
| Billing | Done | Sale/Purchase vouchers, **multi-unit billing**, multi-level discount on pre-tax amount, **CGST/SGST vs IGST** auto-split, tax-inclusive/exclusive rates, auto stock update, **auto barcode** (purchase), **margin-based sale price** (purchase), auto voucher numbering |
| Reports | Done | Dashboard — sales/profit trend, hot & slow selling, **dead stock**, cash-flow (receivables), stock valuation |
| Payments | Done | Receipt/Payment vouchers, party ledger balance (To Receive / To Pay) |
| Invoice | Done | Print-ready GST invoice (HTML) + **PDF download**, amount in words (Lakh/Crore) |
| GST Report | Done | Output vs input tax, rate-wise, B2B/B2C, net GST payable |
| **Frontend UI** | Done | Signup/Login + trial banner + Dashboard (charts) + New Sale billing + Items/Parties/Vouchers + Subscribe page |
| **SaaS / Multi-tenant** | Done | Har business = alag tenant (data fully isolated), **7-din free trial**, monthly/yearly **subscription**, **Razorpay** billing (dev-mode bina keys ke testable), expiry pe access block |
| **Business profiles** | Done | 7 business types (Retail/Wholesale/Restaurant/Pharmacy/Services/Manufacturer/General) — har type apne presets ke saath; Settings se sab toggle (batch/godown/barcode/MRP-inclusive/negative-stock) |
| **GST scheme** | Done | Regular / **Composition (Bill of Supply, no tax)** / Unregistered |
| **Item types** | Done | GOODS (stock) vs SERVICE (no stock — restaurant/services ke liye), reorder level + **low-stock alerts** |
| **Document types** | Done | Tax Invoice, **Estimate/Quotation**, **Delivery Challan**, Credit/Debit Note + estimate→invoice **convert** |
| **GSTR-1 + Admin panel** | Done | GSTR-1 (B2B/B2C/HSN summary); platform owner ke liye SaaS metrics (tenants, MRR, trials, revenue) |
| **Granular Item Settings** | Done | Vyapar-style — barcode, stock maintenance, manufacturing, MRP, calc-tax-on-MRP, party-wise rate, item-wise tax/discount, wholesale price, batch/exp/mfg/model/size tracking, qty decimals — sab Settings se on/off |
| **WhatsApp Share** | Done | "Share on WhatsApp" — invoice/document seedha customer ko (wa.me, WhatsApp Web/app khulta hai) + **safe public link** (token leak ke bina, share-uuid se) |
| **Roles & Audit** | Done | Role-based permissions (Admin/Accountant/Operator/Viewer enforce) + audit log + multi-user **staff** invite |
| **Accounting reports** | Done | P&L, Day Book, Party Statement, Purchase Register, Receivables Aging, payment-to-invoice allocation |
| **E-Invoice / E-Way** | Done | Govt-schema JSON (IRN + e-way bill) — upload-ready (live GSP API baad mein) |
| **Barcode + CSV** | Done | Barcode scan billing, items/parties CSV import-export, invoice logo upload |
| **Robustness** | Done | API pagination, rate-limiting, prod security settings, **automated tests**, **Swagger docs** (`/api/docs/`) |
| **HR / Payroll** | Done | Employees (salary structure), **attendance check-in/out + daily mark**, leave requests (approve/reject), **payroll auto-compute** from attendance, **salary slip PDF**, mark-paid |

Sab kuch **Django admin** se abhi use kar sakte ho, aur har cheez ka **REST API** bhi ready hai.

### API endpoints (sab `/api/` ke neeche)
Masters: `companies, settings, units, tax-rates, godowns, categories, items, variants, unit-prices, batches, stock`
Party: `parties` (+ `parties/check_duplicate/?name=`), `party-documents`
Billing: `vouchers` (+ `vouchers/{id}/post_to_stock/`, filter `?type=SALE|PURCHASE`)
Payments: `payments` (+ `payments/party_balance/?party=<id>`)
Reports: `reports/dashboard/?days=30`, `reports/gst/?days=30`, `reports/stock-valuation/`
Invoice: `/invoice/<id>/?token=<jwt>` (print HTML), `/invoice/<id>/pdf/?token=<jwt>` (PDF)
SaaS: `POST /api/signup/` (with `business_type`), `GET /api/me/`, `GET /api/plans/`, `GET /api/subscription/`, `POST /api/subscription/create_order/`, `POST /api/subscription/verify/`
Business profile: `GET|PUT /api/business-profile/` (type, GST scheme, feature toggles)
Reports: `reports/gstr1/`, `reports/low-stock/`
Billing: `vouchers/{id}/convert/` (estimate→invoice), `vouchers/{id}/share_link/` (WhatsApp + public link)
Public invoice (no login): `/invoice/<id>/?share=<uuid>` and `/invoice/<id>/pdf/?share=<uuid>`
Platform admin (staff only): `GET /api/admin/metrics/`
Reports: `reports/pnl/`, `reports/day-book/`, `reports/party-statement/?party=`, `reports/purchase-register/`, `reports/receivables-aging/`
Staff: `/api/staff/` · Audit: `/api/audit-logs/` · Barcode: `/api/scan/?code=`
E-invoice/E-way: `vouchers/{id}/einvoice_json/`, `vouchers/{id}/eway_json/`
Import/Export: `/api/items-export/`, `/api/items-import/`, `/api/parties-export/`, `/api/parties-import/`
HR/Payroll: `/api/employees/`, `/api/attendance/` (+ `check_in/`, `check_out/`, `mark/`), `/api/leaves/` (+ `{id}/set_status/`), `/api/payslips/` (+ `generate/`, `generate_all/`, `{id}/mark_paid/`)
Payslip print: `/payslip/<id>/?token=<jwt>` (HTML), `/payslip/<id>/pdf/?token=<jwt>` (PDF)
**API docs (Swagger): `/api/docs/`** · Tests: `python manage.py test`

### WhatsApp se document bhejना
"Share on WhatsApp" button (billing screen + Vouchers list) `wa.me` link kholता hai customer ke
number ke saath — message + safe public invoice link ready, aap bas send dabate ho. Yeh reliable aur
zero-setup hai (Vyapar/myBillBook bhi yahi karte hain). Auto-send (bina click) ke liye baad mein official
**WhatsApp Business Cloud API** token Settings mein daal sakte ho (groundwork ready hai). Public link
`share-uuid` se kaam karта hai — aapka login token kabhi expose nahi hota.
Auth: `POST /api/auth/token/` (username+password → JWT access token).

### SaaS / Subscription kaise kaam karta hai
- Har business signup pe **7-din free trial** milta hai.
- Trial/plan khatam hone pe business APIs **402 (Payment Required)** dene lagti hain — sirf subscription/plan endpoints khulte hain taaki user pay kar sake.
- **Razorpay**: `.env` mein `RAZORPAY_KEY_ID` + `RAZORPAY_KEY_SECRET` daalo → real payments. Khaali chhodo → **DEV MODE** (Subscribe page pe "Choose Plan" turant activate kar deta hai, testing ke liye).
- Plans aur prices `/admin/` se kabhi bhi badle ja sakte hain.
- **Data isolation**: har tenant ka data poori tarah alag — ek business doosre ka data kabhi nahi dekh sakta (middleware + per-organization scoping se enforce).

---

## Server pe le jaate waqt (baad mein)

1. PostgreSQL setup karo, `.env` mein `DATABASE_URL=postgres://user:pass@host:5432/erp_munshi` set karo.
2. `.env` mein `DEBUG=False` aur `ALLOWED_HOSTS` apne domain pe set karo.
3. `pip install -r requirements.txt` (isme `gunicorn` + `psycopg2` already hai).
4. `python manage.py collectstatic && python manage.py migrate`
5. `gunicorn config.wsgi` ke saath Nginx ke peeche chalao.

---

## Aage ka roadmap
Poora module plan `PROJECT_PLAN.md` mein hai. Agla: **Party (customer/supplier)** module.
