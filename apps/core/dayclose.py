"""Day-close / cash register — din ke end pe cash tally. Cash receipts, cash
payments/expenses, expected closing cash, aur actual counted cash se difference."""
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def day_close(request):
    from apps.payments.models import Payment
    d = request.GET.get("date") or str(timezone.localdate())
    rows = []
    cash_in = Decimal("0")
    cash_out = Decimal("0")

    for p in Payment.objects.filter(date=d, mode="CASH").select_related("party"):
        amt = Decimal(str(p.amount or 0))
        if p.payment_type == "RECEIPT":
            cash_in += amt
            rows.append({"time": "", "type": "Receipt", "party": p.party.name if p.party_id else "",
                         "in": float(amt), "out": 0})
        else:
            cash_out += amt
            rows.append({"type": "Payment", "party": p.party.name if p.party_id else "",
                         "in": 0, "out": float(amt)})

    try:
        from apps.cashbank.models import Expense
        for e in Expense.objects.filter(date=d, mode__iexact="CASH"):
            amt = Decimal(str(e.amount or 0)) + Decimal(str(getattr(e, "tax_amount", 0) or 0))
            cash_out += amt
            rows.append({"type": "Expense", "party": (e.category.name if e.category_id else "") if hasattr(e, "category_id") else "",
                         "in": 0, "out": float(amt)})
    except Exception:
        pass

    net = cash_in - cash_out
    return Response({
        "date": d,
        "cash_in": float(cash_in), "cash_out": float(cash_out),
        "net": float(net), "rows": rows, "count": len(rows),
    })
