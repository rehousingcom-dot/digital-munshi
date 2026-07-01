"""Proactive AI alerts — Munshi khud dhyan dilata hai: kya khatam hone wala hai,
kiska udhaar bada/purana hai, sale gir to nahi rahi. Sab existing data se, bina
kisi paid API ke."""
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


def _m(x):
    return "₹" + f"{float(x or 0):,.0f}"


def compute_alerts():
    out = []
    today = timezone.localdate()

    # 1) Out / low stock
    try:
        from apps.inventory.models import Item, Stock
        from django.db.models import Sum as S
        stock_map = {r["variant__item"]: r["q"] for r in
                     Stock.objects.values("variant__item").annotate(q=S("quantity"))}
        low = []
        for it in Item.objects.all()[:1500]:
            reorder = float(getattr(it, "reorder_level", 0) or 0)
            if reorder <= 0:
                continue
            cur = float(stock_map.get(it.id, 0) or 0)
            if cur <= 0:
                low.append((it.name, cur, 2))
            elif cur <= reorder:
                low.append((it.name, cur, 1))
        low.sort(key=lambda x: (-x[2], x[1]))
        for name, cur, sev in low[:5]:
            if sev == 2:
                out.append({"level": "high", "icon": "📦", "text": f"{name} — stock KHATAM (0)"})
            else:
                out.append({"level": "warn", "icon": "📦", "text": f"{name} — sirf {cur:g} bacha, order karo"})
    except Exception:
        pass

    # 2) Bada / purana udhaar
    try:
        from apps.party.models import Party
        from apps.payments.models import party_balance
        from apps.billing.models import Voucher
        rows = []
        for p in Party.objects.all()[:500]:
            try:
                b = party_balance(p)
            except Exception:
                continue
            bal = float(b.get("balance", 0) or 0)
            if bal <= 0:
                continue
            last = Voucher.objects.filter(party=p, voucher_type="SALE", is_posted=True).order_by("-date").first()
            days = max(0, (today - last.date).days - int(p.credit_days or 0)) if last else 0
            rows.append((p.name, bal, days))
        rows.sort(key=lambda x: -(x[1] * (1 + x[2] / 30.0)))
        for name, bal, days in rows[:4]:
            if days > 0:
                out.append({"level": "high" if days > 30 else "warn", "icon": "💰",
                            "text": f"{name} ka {_m(bal)} udhaar {days} din se baaki"})
            else:
                out.append({"level": "warn", "icon": "💰", "text": f"{name} ka {_m(bal)} udhaar baaki"})
    except Exception:
        pass

    # 3) Sale trend — aaj vs pichhle 7 din ka average
    try:
        from apps.billing.models import Voucher
        def day_total(d):
            return Voucher.objects.filter(voucher_type="SALE", is_posted=True, date=d).aggregate(t=Sum("grand_total"))["t"] or Decimal("0")
        tot7 = Decimal("0")
        for i in range(1, 8):
            tot7 += day_total(today - timedelta(days=i))
        avg = tot7 / 7 if tot7 else Decimal("0")
        tdy = day_total(today)
        if avg > 0 and tdy < avg * Decimal("0.5"):
            out.append({"level": "warn", "icon": "📉",
                        "text": f"Aaj ki sale ({_m(tdy)}) hafte ke average ({_m(avg)}) se kaafi kam"})
        elif tdy > avg * Decimal("1.5") and avg > 0:
            out.append({"level": "good", "icon": "📈",
                        "text": f"Aaj ki sale ({_m(tdy)}) average se zyada — badhiya!"})
    except Exception:
        pass

    return out


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def alerts(request):
    a = compute_alerts()
    return Response({"count": len(a), "alerts": a})
