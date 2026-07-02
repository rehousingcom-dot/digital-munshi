"""AI reorder suggestions — pichhle 30 din ki sales velocity + current stock se
batata hai kaunsa item khatam hone wala hai aur kitna order karna chahiye.
Bina kisi paid API ke — pure data se."""
import math
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

COVER_DAYS = 30          # itne din ka stock rakhna hai
ALERT_COVER = 12         # itne din se kam cover -> suggest reorder


def compute_reorder():
    from apps.billing.models import VoucherLine
    from apps.inventory.models import Stock, Item
    today = timezone.localdate()
    start = today - timedelta(days=30)

    # 30-din me har variant ki bikri qty
    sold = (VoucherLine.objects.filter(
                voucher__voucher_type="SALE", voucher__is_posted=True,
                voucher__date__gte=start)
            .values("variant", "variant__item__name", "variant__item_code")
            .annotate(qty=Sum("qty_primary")))
    sold_map = {r["variant"]: r for r in sold}

    # stock per variant
    stock_map = {r["variant"]: (r["q"] or Decimal("0")) for r in
                 Stock.objects.values("variant").annotate(q=Sum("quantity"))}
    # reorder level per item (variant ke through)
    reorder_map = {}
    for it in Item.objects.all()[:3000]:
        reorder_map[it.id] = float(getattr(it, "reorder_level", 0) or 0)

    # variant -> item id (for reorder level lookup + name)
    out = []
    seen = set()
    for vid, r in sold_map.items():
        qty30 = float(r["qty"] or 0)
        if qty30 <= 0:
            continue
        velocity = qty30 / 30.0
        stock = float(stock_map.get(vid, 0) or 0)
        cover = (stock / velocity) if velocity > 0 else 999
        if cover <= ALERT_COVER:
            need = max(0, math.ceil(velocity * COVER_DAYS - stock))
            out.append({
                "item": r["variant__item__name"], "code": r["variant__item_code"],
                "stock": round(stock, 1), "sold_30d": round(qty30, 1),
                "per_day": round(velocity, 2), "days_cover": round(cover, 1),
                "suggest_qty": need, "urgency": "high" if cover <= 5 else "medium",
            })
            seen.add(vid)

    # bina bikri ke bhi jo reorder level se neeche hain
    for r in Stock.objects.values("variant", "variant__item", "variant__item__name",
                                  "variant__item_code").annotate(q=Sum("quantity")):
        vid = r["variant"]
        if vid in seen:
            continue
        stock = float(r["q"] or 0)
        rl = reorder_map.get(r["variant__item"], 0)
        if rl > 0 and stock <= rl:
            out.append({
                "item": r["variant__item__name"], "code": r["variant__item_code"],
                "stock": round(stock, 1), "sold_30d": 0, "per_day": 0,
                "days_cover": 0, "suggest_qty": max(1, math.ceil(rl - stock)),
                "urgency": "high" if stock <= 0 else "medium",
            })

    out.sort(key=lambda x: (0 if x["urgency"] == "high" else 1, x["days_cover"]))
    return out


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def reorder_suggestions(request):
    out = compute_reorder()
    return Response({"count": len(out), "items": out})
