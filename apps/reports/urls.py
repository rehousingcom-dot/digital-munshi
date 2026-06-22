from django.urls import path
from . import views

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("gst/", views.gst_report, name="gst_report"),
    path("gstr1/", views.gstr1, name="gstr1"),
    path("low-stock/", views.low_stock, name="low_stock"),
    path("stock-valuation/", views.stock_valuation, name="stock_valuation"),
    path("pnl/", views.profit_and_loss, name="pnl"),
    path("day-book/", views.day_book, name="day_book"),
    path("party-statement/", views.party_statement, name="party_statement"),
    path("purchase-register/", views.purchase_register, name="purchase_register"),
    path("receivables-aging/", views.receivables_aging, name="receivables_aging"),
    path("gstr3b/", views.gstr3b, name="gstr3b"),
    path("hsn-summary/", views.hsn_summary, name="hsn_summary"),
    path("balance-sheet/", views.balance_sheet, name="balance_sheet"),
    path("payment-reminders/", views.payment_reminders, name="payment_reminders"),
]
