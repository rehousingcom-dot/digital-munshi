from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse, HttpResponse
from django.views.generic import TemplateView

# ---- PWA service worker (served at root so its scope covers the whole app) ----
_SW_JS = """
// Kill-switch SW: purane clients pe cache clear + unregister (PWA offline cache hata diya).
self.addEventListener("install", e => { self.skipWaiting(); });
self.addEventListener("activate", e => { e.waitUntil((async () => {
  try { const ks = await caches.keys(); await Promise.all(ks.map(k => caches.delete(k))); } catch (_) {}
  try { await self.registration.unregister(); } catch (_) {}
  try { const cs = await self.clients.matchAll(); cs.forEach(c => c.navigate(c.url)); } catch (_) {}
})()); });
"""

def service_worker(request):
    return HttpResponse(_SW_JS, content_type="application/javascript")


def cron_run(request):
    """Secure cron trigger — koi bhi external scheduler (cron-job.org) roz hit kare.
    ?token=<CRON_TOKEN env> match hone pe daily_summary + backup_db background me chalate hain.
    Turant response deta hai (thread me chalta hai) taaki HTTP timeout na ho."""
    import os
    import threading
    token = request.GET.get("token", "")
    expected = os.environ.get("CRON_TOKEN", "")
    if not expected or token != expected:
        return JsonResponse({"error": "forbidden"}, status=403)

    tasks = (request.GET.get("tasks") or "daily_summary,backup_db").split(",")

    def _run():
        from django.core.management import call_command
        for t in tasks:
            t = t.strip()
            if not t:
                continue
            try:
                call_command(t)
            except Exception:
                pass

    threading.Thread(target=_run, daemon=True).start()
    return JsonResponse({"status": "started", "tasks": tasks})


def sms_test(request):
    """SMS gateway test — /api/sms/test/?token=<CRON_TOKEN>&to=<number>&text=<optional>
    Gateway ka raw response return karta hai (debug ke liye)."""
    import os
    if request.GET.get("token", "") != os.environ.get("CRON_TOKEN", "") or not os.environ.get("CRON_TOKEN"):
        return JsonResponse({"error": "forbidden"}, status=403)
    to = request.GET.get("to", "")
    if not to:
        return JsonResponse({"error": "give ?to=<number>"}, status=400)
    from apps.core import sms as _sms
    if not _sms.is_enabled():
        return JsonResponse({"error": "SMS_API_URL not set"}, status=400)
    text = request.GET.get("text") or "Digital Munshi SMS test. -RELOAD"
    tid = request.GET.get("tid", "")
    ok, info = _sms.send_sms(to, text, template_id=tid)
    return JsonResponse({"ok": ok, "gateway_response": info})


def robots_txt(request):
    return HttpResponse("User-agent: *\nAllow: /\nDisallow: /api/\nDisallow: /admin/\n"
                        "Sitemap: https://erp.reloaddigital.in/sitemap.xml\n",
                        content_type="text/plain")


def sitemap_xml(request):
    from apps.core.marketing import KEYWORD_PAGES, BLOG_POSTS
    base = "https://erp.reloaddigital.in"
    urls = [base + "/welcome/", base + "/", base + "/blog/"]
    from apps.core.marketing import CITIES
    urls += [base + "/software/" + s + "/" for s in KEYWORD_PAGES]
    urls += [base + "/blog/" + s + "/" for s in BLOG_POSTS]
    urls += [base + "/billing-software-in-" + s + "/" for s in CITIES]
    from apps.core import marketing_hi as MH
    urls += [base + "/hi/blog/"]
    urls += [base + "/hi/software/" + s + "/" for s in MH.KEYWORD_PAGES]
    urls += [base + "/hi/blog/" + s + "/" for s in MH.BLOG_POSTS]
    urls += [base + "/hi/billing-software-in-" + s + "/" for s in MH.CITIES]
    from apps.core.marketing import COMPARISONS
    urls += [base + "/compare/" + s + "/" for s in COMPARISONS]
    urls += [base + "/tools/", base + "/tools/gst-calculator/", base + "/tools/invoice-generator/", base + "/tools/hsn-code-finder/"]
    urls += [base + "/tools/emi-calculator/", base + "/tools/discount-calculator/", base + "/tools/profit-margin-calculator/", base + "/tools/rupees-in-words/", base + "/tools/barcode-generator/", base + "/tools/upi-qr-code-generator/", base + "/tools/chit-fund-calculator/"]
    body = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    for u in urls:
        body += f"<url><loc>{u}</loc><changefreq>weekly</changefreq></url>"
    body += "</urlset>"
    return HttpResponse(body, content_type="application/xml")
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.core import views as core_views
from apps.inventory import views as inv_views
from apps.party import views as party_views
from apps.billing import views as billing_views
from apps.payments import views as payment_views
from apps.billing import print_views
from apps.tenants import views as tenant_views
from apps.accounts import views as account_views
from apps.inventory import views as inv_extra
from apps.party import views as party_extra
from apps.hr import views as hr_views
from apps.hr import print_views as hr_print
from apps.cashbank import views as cashbank_views
from apps.accounting import views as acc_views
from apps.committee import views as committee_views


def health(request):
    return JsonResponse({"status": "ok", "service": "ERP Munshi"})


router = DefaultRouter()
# Core
router.register("companies", core_views.CompanyViewSet)
router.register("settings", core_views.SettingViewSet)
router.register("units", core_views.UnitViewSet)
router.register("tax-rates", core_views.TaxRateViewSet)
router.register("godowns", core_views.GodownViewSet)
# Inventory
router.register("categories", inv_views.CategoryViewSet)
router.register("items", inv_views.ItemViewSet)
router.register("variants", inv_views.ItemVariantViewSet)
router.register("unit-prices", inv_views.ItemUnitPriceViewSet)
router.register("batches", inv_views.BatchViewSet)
router.register("stock", inv_views.StockViewSet)
router.register("price-lists", inv_views.PriceListViewSet)
router.register("price-list-items", inv_views.PriceListItemViewSet)
router.register("item-components", inv_views.ItemComponentViewSet)
router.register("serials", inv_views.SerialNumberViewSet)
# Party
router.register("parties", party_views.PartyViewSet)
router.register("party-documents", party_views.PartyDocumentViewSet)
# Billing
router.register("vouchers", billing_views.VoucherViewSet)
router.register("recurring-invoices", billing_views.RecurringInvoiceViewSet)
# Payments
router.register("payments", payment_views.PaymentViewSet)
# Audit
router.register("audit-logs", account_views.AuditLogViewSet, basename="audit-log")
# Staff (multi-user)
router.register("staff", account_views.StaffViewSet, basename="staff")
# HR / Payroll
router.register("employees", hr_views.EmployeeViewSet)
router.register("attendance", hr_views.AttendanceViewSet)
router.register("leaves", hr_views.LeaveRequestViewSet)
router.register("payslips", hr_views.SalarySlipViewSet)
# Committee / BC / Chit
router.register("committees", committee_views.CommitteeViewSet)
router.register("committee-members", committee_views.CommitteeMemberViewSet)
router.register("committee-rounds", committee_views.CommitteeRoundViewSet)
router.register("committee-payments", committee_views.CommitteePaymentViewSet)
# Cash & Bank
router.register("bank-accounts", cashbank_views.BankAccountViewSet)
router.register("bank-transactions", cashbank_views.BankTransactionViewSet)
router.register("cheques", cashbank_views.ChequeViewSet)
router.register("loans", cashbank_views.LoanAccountViewSet)
router.register("expense-categories", cashbank_views.ExpenseCategoryViewSet)
router.register("expenses", cashbank_views.ExpenseViewSet)
router.register("accounts-ledger", acc_views.AccountViewSet)
router.register("journals", acc_views.JournalEntryViewSet)

urlpatterns = [
    path("", TemplateView.as_view(template_name="app.html"), name="app"),
    path("sw.js", service_worker, name="service_worker"),
    path("api/cron/run/", cron_run, name="cron_run"),
    path("api/sms/test/", sms_test, name="sms_test"),
    path("admin/", admin.site.urls),
    path("api/health/", health, name="health"),
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # SaaS: signup, plans, subscription billing
    path("api/send-otp/", tenant_views.send_otp, name="send_otp"),
    path("api/signup/", tenant_views.signup, name="signup"),
    path("api/plans/", tenant_views.plans, name="plans"),
    path("api/subscription/", tenant_views.subscription_status, name="subscription"),
    path("api/subscription/create_order/", tenant_views.create_order, name="create_order"),
    path("api/subscription/verify/", tenant_views.verify_payment, name="verify_payment"),
    path("api/subscription/callback/", tenant_views.razorpay_callback, name="razorpay_callback"),
    path("api/subscription/create_recurring/", tenant_views.create_recurring, name="create_recurring"),
    path("api/subscription/webhook/", tenant_views.razorpay_webhook, name="razorpay_webhook"),
    # Platform admin metrics (SaaS owner)
    path("api/me/", tenant_views.me, name="me"),
    path("api/firms/", tenant_views.firms, name="firms"),
    path("api/firms/switch/", tenant_views.firm_switch, name="firm_switch"),
    path("api/admin/metrics/", tenant_views.admin_metrics, name="admin_metrics"),
    # Business profile / settings
    path("api/business-profile/", core_views.business_profile, name="business_profile"),
    path("api/business-profile/logo/", core_views.upload_logo, name="upload_logo"),
    path("api/business-profile/signature/", core_views.upload_signature, name="upload_signature"),
    path("api/run-due-recurring/", billing_views.run_due_recurring, name="run_due_recurring"),
    # Barcode scan + CSV import/export
    path("api/scan/", inv_extra.scan, name="scan"),
    path("api/items-export/", inv_extra.items_export, name="items_export"),
    path("api/items-import/", inv_extra.items_import, name="items_import"),
    path("api/parties-export/", party_extra.parties_export, name="parties_export"),
    path("api/transactions-export/", billing_views.transactions_export, name="transactions_export"),
    path("api/parties-import/", party_extra.parties_import, name="parties_import"),
    path("api/cashbank-summary/", cashbank_views.cashbank_summary, name="cashbank_summary"),
    path("api/expense-summary/", cashbank_views.expense_summary, name="expense_summary"),
    path("api/trial-balance/", acc_views.trial_balance, name="trial_balance"),
    path("portal/<uuid:share>/", party_extra.customer_portal, name="customer_portal"),
    path("party/<int:pk>/statement/", party_extra.party_statement_doc, name="party_statement_doc"),
    path("welcome/", core_views.landing, name="landing"),
    path("api/lead/", core_views.lead_create, name="lead_create"),
    path("software/<slug:slug>/", core_views.keyword_page, name="keyword_page"),
    path("blog/", core_views.blog_index, name="blog_index"),
    path("blog/<slug:slug>/", core_views.blog_post, name="blog_post"),
    path("billing-software-in-<slug:slug>/", core_views.city_page, name="city_page"),
    path("hi/software/<slug:slug>/", core_views.keyword_page_hi, name="keyword_page_hi"),
    path("hi/billing-software-in-<slug:slug>/", core_views.city_page_hi, name="city_page_hi"),
    path("hi/blog/", core_views.blog_index_hi, name="blog_index_hi"),
    path("hi/blog/<slug:slug>/", core_views.blog_post_hi, name="blog_post_hi"),
    path("compare/<slug:slug>/", core_views.comparison_page, name="comparison_page"),
    path("tools/", core_views.tools_index, name="tools_index"),
    path("tools/gst-calculator/", core_views.tool_gst_calculator, name="tool_gst_calculator"),
    path("tools/invoice-generator/", core_views.tool_invoice_generator, name="tool_invoice_generator"),
    path("tools/hsn-code-finder/", core_views.tool_hsn_finder, name="tool_hsn_finder"),
    path("tools/emi-calculator/", core_views.tool_emi, name="tool_emi"),
    path("tools/discount-calculator/", core_views.tool_discount, name="tool_discount"),
    path("tools/profit-margin-calculator/", core_views.tool_margin, name="tool_margin"),
    path("tools/rupees-in-words/", core_views.tool_words, name="tool_words"),
    path("tools/barcode-generator/", core_views.tool_barcode, name="tool_barcode"),
    path("tools/upi-qr-code-generator/", core_views.tool_upi_qr, name="tool_upi_qr"),
    path("tools/chit-fund-calculator/", core_views.tool_chit, name="tool_chit"),
    path("robots.txt", robots_txt, name="robots"),
    path("sitemap.xml", sitemap_xml, name="sitemap"),
    path("shop/<uuid:catalog_uuid>/", core_views.catalog_shop, name="catalog_shop"),
    path("api/catalog/toggle/", tenant_views.catalog_toggle, name="catalog_toggle"),
    path("api/", include(router.urls)),
    path("api/reports/", include("apps.reports.urls")),
    # API docs (Swagger)
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    # Invoice print / PDF
    path("invoice/<int:pk>/", print_views.invoice_html, name="invoice_html"),
    path("invoice/<int:pk>/pdf/", print_views.invoice_pdf, name="invoice_pdf"),
    # Payslip print / PDF
    path("payslip/<int:pk>/", hr_print.payslip_html, name="payslip_html"),
    path("payslip/<int:pk>/pdf/", hr_print.payslip_pdf, name="payslip_pdf"),
]

# Media (logo) serve in dev
from django.conf import settings as _settings
from django.conf.urls.static import static as _static
if _settings.DEBUG:
    urlpatterns += _static(_settings.MEDIA_URL, document_root=_settings.MEDIA_ROOT)
