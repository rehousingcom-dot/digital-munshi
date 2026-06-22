# 01 — Architecture & Code Structure

## Repo layout
```
ERP Munshi/
├── config/                 # Django project
│   ├── settings.py         # ALL settings (env-driven). DB, DRF, security, whitenoise.
│   ├── urls.py             # 37 routes — all API endpoints + viewsets + SPA serve
│   ├── wsgi.py             # gunicorn entrypoint: config.wsgi:application
│   └── pagination.py
├── apps/                   # 11 Django apps (business logic)
│   ├── tenants/            # Organization, Plan, Subscription, signup, Razorpay billing
│   ├── accounts/           # User (custom AUTH_USER_MODEL), roles, permissions, AuditLog
│   ├── core/               # Company, Setting, Godown, Tax, Unit (+ logo, signature)
│   ├── inventory/          # Item, Batch, Category, ItemComponent, SerialNumber, PriceList…
│   ├── party/              # Party (customer/supplier), PartyDocument
│   ├── billing/            # Voucher, VoucherLine, RecurringInvoice
│   ├── payments/           # Payment, PaymentAllocation
│   ├── cashbank/           # BankAccount, BankTransaction, Cheque, Expense, LoanAccount
│   ├── accounting/         # Account, JournalEntry, JournalLine (double-entry)
│   ├── hr/                 # Employee, Attendance, Leave, Payroll
│   └── reports/            # report views (no models)
├── templates/
│   ├── app.html            # THE React SPA (~2200 lines) — entire frontend
│   └── portal.html         # public customer invoice view
├── Dockerfile              # prod container (python:3.12-slim → gunicorn)
├── railway.json            # Railway config-as-code (builder, start cmd, restart)
├── gunicorn.conf.py        # gunicorn bind/workers (IPv6 [::]:8080)
├── Procfile                # fallback (Railway uses railway.json/Dockerfile)
├── requirements.txt
└── docs/                   # THIS documentation
```

## Multi-tenancy (CRITICAL to understand)
Every business is an **Organization** (tenant). Almost all business data has an
`organization` FK and is isolated per-tenant.

- **Thread-local "current org"**: `apps/tenants/middleware.py` `TenantMiddleware` sets the
  current organization per request (from the logged-in user's `user.organization`).
- **OrgOwned base model + OrgScopedQuerysetMixin**: models/viewsets auto-filter to the
  current org so one tenant never sees another's data.
- **Subscription enforcement**: middleware blocks API access if trial/subscription expired
  (except EXEMPT_PREFIXES like /admin, /api/signup, /api/auth/token, static).
- **Multi-firm**: a user can own several Organizations and switch active firm
  (`firm_switch` view). Each firm = fully separate books.

## Auth
- **JWT only** for the SPA. `POST /api/auth/token/` → access+refresh. SPA sends
  `Authorization: Bearer <token>` on every request.
- `POST /api/signup/` (AllowAny) creates user+org+trial, returns JWT.
- DRF `DEFAULT_AUTHENTICATION_CLASSES` = **JWTAuthentication only** (SessionAuthentication
  was REMOVED — it caused "CSRF Failed" when an admin session cookie was present; see
  `docs/04_TROUBLESHOOTING_LOG.md`).
- Django admin (`/admin/`) uses Django's own session auth — separate from the SPA.
- Roles/RBAC via `apps/accounts/permissions.py` `RolePermission`.

## Frontend (templates/app.html)
- ONE file. React 18 (UMD) + Babel-standalone (in-browser JSX transpile) + Tailwind CDN
  + Chart.js + JsBarcode. **No bundler / build step.**
- JSX lives inside `<script type="text/babel">` wrapped in Django `{% verbatim %}`.
- Key components: `Login` (auth + marketing landing), `Subscribe` (plans), dashboard,
  NewSale (billing), VouchersView, PartyView/Form, ItemForm, CashBankView, AccountingView,
  POSView, StaffView, PriceListManager, BarcodeDesigner, CommandPalette, FirmSwitcher.
- API base = `/api`. Token stored in memory/localStorage helper (`getToken/setToken`).
- **Editing the SPA:** edit `templates/app.html`, then ALWAYS verify JSX transpiles before
  pushing (see runbook). A single JSX typo white-screens the whole app.

## Settings highlights (config/settings.py)
- `env` (django-environ) drives everything. Reads `.env` locally if present.
- `DATABASE_URL` set → PostgreSQL; empty → SQLite (`db.sqlite3`).
- `DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS` from env.
- WhiteNoise is OPTIONAL (try/except import) so local dev works without it.
- When `DEBUG=False`: security headers on, `SECURE_PROXY_SSL_HEADER` for Railway's https
  proxy, `CSRF_TRUSTED_ORIGINS` auto-built from ALLOWED_HOSTS.
- Razorpay / GSTIN / email keys read from env (blank = dev mode / disabled).

## Static files
- `collectstatic` runs in Docker build → `staticfiles/`, served by WhiteNoise
  (`CompressedManifestStaticFilesStorage`). The SPA mostly uses CDNs, so static is light.
