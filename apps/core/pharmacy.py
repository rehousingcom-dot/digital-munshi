"""Pharmacy / expiry management — batch expiry alerts (FEFO). Kaunsi dawai kab
expire ho rahi, kitna stock, kitni value risk pe. Medical store ka sabse bada pain."""
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def expiry_report(request):
    from apps.inventory.models import Stock
    today = timezone.localdate()
    try:
        maxdays = int(request.GET.get("days") or 90)
    except Exception:
        maxdays = 90

    rows = []
    buckets = {"expired": 0.0, "d30": 0.0, "d60": 0.0, "d90": 0.0}
    counts = {"expired": 0, "d30": 0, "d60": 0, "d90": 0}
    qs = (Stock.objects.filter(batch__isnull=False, quantity__gt=0)
          .select_related("batch", "variant__item", "godown"))
    for s in qs[:5000]:
        b = s.batch
        if not b or not b.expiry_date:
            continue
        days = (b.expiry_date - today).days
        if days > maxdays:
            continue
        qty = float(s.quantity or 0)
        mrp = float(b.mrp or 0) or float(getattr(s.variant.item, "mrp", 0) or 0)
        value = qty * mrp
        if days < 0:
            bk = "expired"
        elif days <= 30:
            bk = "d30"
        elif days <= 60:
            bk = "d60"
        else:
            bk = "d90"
        buckets[bk] += value
        counts[bk] += 1
        rows.append({
            "item": s.variant.item.name, "batch": b.batch_no,
            "expiry": b.expiry_date.isoformat(), "days": days,
            "qty": round(qty, 1), "mrp": round(mrp, 2), "value": round(value, 2),
            "godown": s.godown.name if s.godown_id else "",
            "status": "EXPIRED" if days < 0 else ("≤30d" if days <= 30 else ("≤60d" if days <= 60 else "≤90d")),
        })
    rows.sort(key=lambda x: x["days"])
    return Response({
        "count": len(rows),
        "buckets": {k: round(v, 2) for k, v in buckets.items()},
        "counts": counts,
        "at_risk_value": round(sum(buckets.values()), 2),
        "items": rows,
    })
