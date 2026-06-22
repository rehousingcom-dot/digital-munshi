from django.contrib import admin
from .models import BankAccount, BankTransaction, Cheque, LoanAccount, ExpenseCategory, Expense


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("date", "category", "party", "amount", "tax_amount", "mode")
    list_filter = ("mode", "date")
    search_fields = ("reference", "notes", "category__name")


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ("name", "account_type", "account_no", "bank_name", "opening_balance", "is_active")
    list_filter = ("account_type", "is_active")
    search_fields = ("name", "account_no", "bank_name")


@admin.register(BankTransaction)
class BankTransactionAdmin(admin.ModelAdmin):
    list_display = ("account", "date", "direction", "amount", "mode", "party")
    list_filter = ("direction", "mode", "date")
    search_fields = ("reference", "notes", "party__name")


@admin.register(Cheque)
class ChequeAdmin(admin.ModelAdmin):
    list_display = ("cheque_no", "cheque_type", "party", "amount", "due_date", "status")
    list_filter = ("cheque_type", "status", "due_date")
    search_fields = ("cheque_no", "party__name", "bank_name")


@admin.register(LoanAccount)
class LoanAccountAdmin(admin.ModelAdmin):
    list_display = ("lender", "principal", "interest_rate", "tenure_months", "emi", "current_balance")
    search_fields = ("lender", "account_no")
