from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.views.generic import TemplateView
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
    path("admin/", admin.site.urls),
    path("api/health/", health, name="health"),
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # SaaS: signup, plans, subscription billing
    path("api/signup/", tenant_views.signup, name="signup"),
    path("api/plans/", tenant_views.plans, name="plans"),
    path("api/subscription/", tenant_views.subscription_status, name="subscription"),
    path("api/subscription/create_order/", tenant_views.create_order, name="create_order"),
    path("api/subscription/verify/", tenant_views.verify_payment, name="verify_payment"),
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
    path("api/parties-import/", party_extra.parties_import, name="parties_import"),
    path("api/cashbank-summary/", cashbank_views.cashbank_summary, name="cashbank_summary"),
    path("api/expense-summary/", cashbank_views.expense_summary, name="expense_summary"),
    path("api/trial-balance/", acc_views.trial_balance, name="trial_balance"),
    path("portal/<uuid:share>/", party_extra.customer_portal, name="customer_portal"),
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
