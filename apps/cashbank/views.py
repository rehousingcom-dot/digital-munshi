from decimal import Decimal
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.tenants.tenancy import OrgScopedQuerysetMixin
from .models import BankAccount, BankTransaction, Cheque, LoanAccount, ExpenseCategory, Expense
from .serializers import (
    BankAccountSerializer, BankTransactionSerializer, ChequeSerializer, LoanAccountSerializer,
    ExpenseCategorySerializer, ExpenseSerializer,
)


class BankAccountViewSet(OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = BankAccount.objects.all()
    serializer_class = BankAccountSerializer


class BankTransactionViewSet(OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = BankTransaction.objects.all().select_related("account", "party")
    serializer_class = BankTransactionSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        acc = self.request.query_params.get("account")
        if acc:
            qs = qs.filter(account_id=acc)
        return qs


class ChequeViewSet(OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Cheque.objects.all().select_related("party")
    serializer_class = ChequeSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        st = self.request.query_params.get("status")
        if st:
            qs = qs.filter(status=st.upper())
        return qs


class LoanAccountViewSet(OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = LoanAccount.objects.all()
    serializer_class = LoanAccountSerializer


class ExpenseCategoryViewSet(OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = ExpenseCategory.objects.all()
    serializer_class = ExpenseCategorySerializer


class ExpenseViewSet(OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Expense.objects.all().select_related("category", "party")
    serializer_class = ExpenseSerializer


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def expense_summary(request):
    """Expense category-wise total + grand total (P&L feed)."""
    from django.db.models import Sum
    from datetime import timedelta
    from django.utils import timezone
    try:
        days = int(request.query_params.get("days", 30))
    except (TypeError, ValueError):
        days = 30
    end = timezone.localdate()
    start = end - timedelta(days=days - 1)
    qs = Expense.objects.filter(date__gte=start, date__lte=end)
    by_cat = {}
    total = Decimal("0")
    for e in qs.select_related("category"):
        cat = e.category.name if e.category else "Other"
        amt = Decimal(str(e.amount)) + Decimal(str(e.tax_amount))
        by_cat[cat] = by_cat.get(cat, Decimal("0")) + amt
        total += amt
    return Response({
        "period": {"from": str(start), "to": str(end)},
        "total": float(total),
        "by_category": [{"category": k, "amount": float(v)} for k, v in
                        sorted(by_cat.items(), key=lambda x: -x[1])],
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def cashbank_summary(request):
    """Cash & Bank dashboard — total cash, total bank, pending cheques, loan outstanding."""
    accounts = list(BankAccount.objects.all())
    cash = sum((a.balance for a in accounts if a.account_type == "CASH"), Decimal("0"))
    bank = sum((a.balance for a in accounts if a.account_type == "BANK"), Decimal("0"))
    cheques = Cheque.objects.filter(status="PENDING")
    chq_recv = sum((c.amount for c in cheques if c.cheque_type == "RECEIVABLE"), Decimal("0"))
    chq_pay = sum((c.amount for c in cheques if c.cheque_type == "PAYABLE"), Decimal("0"))
    loan_out = sum((l.current_balance for l in LoanAccount.objects.all()), Decimal("0"))
    return Response({
        "cash_in_hand": float(cash),
        "bank_balance": float(bank),
        "total_balance": float(cash + bank),
        "cheques_receivable": float(chq_recv),
        "cheques_payable": float(chq_pay),
        "loan_outstanding": float(loan_out),
        "accounts": BankAccountSerializer(accounts, many=True).data,
    })
