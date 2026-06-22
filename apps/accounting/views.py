from decimal import Decimal
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.tenants.tenancy import OrgScopedQuerysetMixin, get_current_org
from .models import Account, JournalEntry, seed_accounts
from .serializers import AccountSerializer, JournalEntrySerializer


class AccountViewSet(OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer

    def list(self, request, *args, **kwargs):
        # Pehli baar — default chart of accounts seed
        org = get_current_org()
        if org and not Account.objects.exists():
            seed_accounts(org)
        return super().list(request, *args, **kwargs)


class JournalEntryViewSet(OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = JournalEntry.objects.all().prefetch_related("lines", "lines__account")
    serializer_class = JournalEntrySerializer


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def trial_balance(request):
    """Trial Balance — har account ka closing debit/credit balance (journals + opening)."""
    rows = []
    total_dr = total_cr = Decimal("0")
    for acc in Account.objects.filter(is_active=True).order_by("code"):
        bal = acc.balance
        if bal == 0:
            continue
        # Debit-nature accounts positive balance => debit column
        if acc.account_type in ("ASSET", "EXPENSE"):
            dr, cr = (bal, Decimal("0")) if bal >= 0 else (Decimal("0"), -bal)
        else:
            dr, cr = (Decimal("0"), bal) if bal >= 0 else (-bal, Decimal("0"))
        total_dr += dr
        total_cr += cr
        rows.append({"code": acc.code, "name": acc.name, "type": acc.account_type,
                     "debit": float(dr), "credit": float(cr)})
    return Response({
        "rows": rows,
        "total_debit": float(total_dr), "total_credit": float(total_cr),
        "balanced": total_dr == total_cr,
    })
