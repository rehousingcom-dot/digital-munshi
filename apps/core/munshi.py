"""AI Munshi — in-app assistant. Dukaandar sawal poochta hai (Hindi/English),
Munshi existing data se jawab deta hai. Bina kisi paid API ke — rule/intent based,
taaki fast aur free rahe. Voice input frontend (Web Speech) se aata hai.
"""
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


def _m(x):
    return "₹" + f"{float(x or 0):,.0f}"


NUM_WORDS = {
    "ek": 1, "do": 2, "teen": 3, "tin": 3, "char": 4, "chaar": 4, "paanch": 5, "panch": 5,
    "chhe": 6, "che": 6, "chah": 6, "saat": 7, "sat": 7, "aath": 8, "ath": 8, "nau": 9,
    "das": 10, "dus": 10, "gyarah": 11, "barah": 12, "adha": 0.5, "aadha": 0.5,
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "dozen": 12,
}
UNIT_WORDS = {"kilo", "kg", "gram", "gm", "packet", "pkt", "piece", "pcs", "pc", "dozen",
              "litre", "liter", "ltr", "box", "peti", "adad", "nag"}


def _period(ql):
    today = timezone.localdate()
    if any(w in ql for w in ["kal", "yesterday"]):
        d = today - timedelta(days=1)
        return d, d, "kal"
    if any(w in ql for w in ["mahine", "maheene", "month", "mah "]):
        return today.replace(day=1), today, "is mahine"
    if any(w in ql for w in ["hafte", "week", "saptah"]):
        return today - timedelta(days=6), today, "is hafte"
    return today, today, "aaj"


def _sales_answer(ql):
    from apps.billing.models import Voucher
    start, end, label = _period(ql)
    qs = Voucher.objects.filter(voucher_type="SALE", is_posted=True, date__gte=start, date__lte=end)
    agg = qs.aggregate(t=Sum("grand_total"))
    total = agg["t"] or Decimal("0")
    cnt = qs.count()
    return f"{label.capitalize()} ki bikri: {_m(total)} — {cnt} bill." + (
        "" if cnt else " Abhi tak koi sale nahi.")


def _receivable_answer(ql):
    from apps.party.models import Party
    from apps.payments.models import party_balance
    rows = []
    for p in Party.objects.all()[:500]:
        try:
            b = party_balance(p)
        except Exception:
            continue
        if b.get("balance", 0) and b["balance"] > 0:
            rows.append((p.name, float(b["balance"])))
    rows.sort(key=lambda x: -x[1])
    if not rows:
        return "Kisi ka udhaar baaki nahi — sab clear! ✅"
    total = sum(r[1] for r in rows)
    top = rows[:5]
    lines = "\n".join(f"• {n} — {_m(v)}" for n, v in top)
    return f"Kul udhaar (receivable): {_m(total)} — {len(rows)} party.\nSabse zyada:\n{lines}"


def _lowstock_answer(ql):
    from apps.inventory.models import Item, Stock
    from django.db.models import Sum as S
    low = []
    stock_map = {r["variant__item"]: r["q"] for r in
                 Stock.objects.values("variant__item").annotate(q=S("quantity"))}
    for it in Item.objects.all()[:1000]:
        reorder = float(getattr(it, "reorder_level", 0) or 0)
        cur = float(stock_map.get(it.id, 0) or 0)
        if reorder > 0 and cur <= reorder:
            low.append((it.name, cur, reorder))
    if not low:
        return "Koi item low-stock me nahi — sab theek. 👍"
    lines = "\n".join(f"• {n} — stock {c:g} (reorder {r:g})" for n, c, r in low[:8])
    return f"Low stock items ({len(low)}):\n{lines}"


def _expense_answer(ql):
    start, end, label = _period(ql)
    try:
        from apps.cashbank.models import Expense
        t = Expense.objects.filter(date__gte=start, date__lte=end).aggregate(t=Sum("amount"))["t"] or 0
        return f"{label.capitalize()} ka kharch: {_m(t)}."
    except Exception:
        return "Kharch data abhi available nahi."


def _profit_answer(ql):
    from apps.billing.models import Voucher
    start, end, label = _period(ql)
    sale = Voucher.objects.filter(voucher_type="SALE", is_posted=True, date__gte=start, date__lte=end).aggregate(t=Sum("grand_total"))["t"] or Decimal("0")
    pur = Voucher.objects.filter(voucher_type="PURCHASE", is_posted=True, date__gte=start, date__lte=end).aggregate(t=Sum("grand_total"))["t"] or Decimal("0")
    return f"{label.capitalize()}: bikri {_m(sale)}, khareed {_m(pur)}, farak {_m(sale - pur)}. (Exact profit ke liye Reports → P&L dekho.)"


def _top_customer_answer(ql):
    from apps.billing.models import Voucher
    start, end, label = _period(ql)
    rows = (Voucher.objects.filter(voucher_type="SALE", is_posted=True, date__gte=start, date__lte=end,
                                   party__isnull=False)
            .values("party__name").annotate(t=Sum("grand_total")).order_by("-t")[:5])
    if not rows:
        return f"{label.capitalize()} koi customer sale nahi."
    lines = "\n".join(f"• {r['party__name']} — {_m(r['t'])}" for r in rows)
    return f"{label.capitalize()} ke top customers:\n{lines}"


def _parse_bill(q):
    """Voice/text se items nikaalo aur quick total banao.
    e.g. 'do kilo cheeni, ek parle-g' → matched items + total."""
    from apps.inventory.models import Item
    items = list(Item.objects.all()[:2000])
    names = [(it, it.name.lower()) for it in items]
    # chunks: comma / 'aur' / 'and'
    import re
    raw = re.split(r"[,]|\baur\b|\band\b|\bplus\b", q.lower())
    lines, total = [], Decimal("0")
    for chunk in raw:
        chunk = chunk.strip()
        if not chunk:
            continue
        # qty
        qty = None
        mnum = re.search(r"(\d+(?:\.\d+)?)", chunk)
        if mnum:
            qty = float(mnum.group(1))
        else:
            for w, v in NUM_WORDS.items():
                if re.search(r"\b" + w + r"\b", chunk):
                    qty = v
                    break
        if qty is None:
            qty = 1
        # match item by longest name substring present in chunk
        best = None
        cleaned = chunk
        for w in list(NUM_WORDS) + list(UNIT_WORDS):
            cleaned = re.sub(r"\b" + re.escape(w) + r"\b", " ", cleaned)
        cleaned = re.sub(r"[0-9]", " ", cleaned).strip()
        for it, nm in names:
            if nm and (nm in chunk or (len(cleaned) >= 2 and cleaned in nm) or _tok_match(cleaned, nm)):
                if best is None or len(nm) > len(best[1]):
                    best = (it, nm)
        if best:
            it = best[0]
            price = Decimal(str(it.mrp or 0))
            amt = price * Decimal(str(qty))
            total += amt
            lines.append({"item": it.name, "qty": qty, "price": float(price), "amount": float(amt)})
        else:
            lines.append({"item": cleaned or chunk, "qty": qty, "price": None, "amount": None, "unmatched": True})
    return lines, float(total)


def _tok_match(cleaned, nm):
    if not cleaned:
        return False
    toks = [w for w in cleaned.split() if len(w) >= 3]
    return any(w in nm for w in toks)


@api_view(["POST", "GET"])
@permission_classes([IsAuthenticated])
def munshi_ask(request):
    q = (request.data.get("q") if request.method == "POST" else request.GET.get("q")) or ""
    q = str(q).strip()
    ql = q.lower()
    if not ql:
        return Response({"answer": _help()})

    # Bill / parcha banao
    if any(w in ql for w in ["bill", "parcha", "parchi", "banao", "bana do", "invoice bana"]):
        lines, total = _parse_bill(q)
        matched = [l for l in lines if not l.get("unmatched")]
        if matched:
            txt = "\n".join(f"• {l['qty']:g} × {l['item']} = {_m(l['amount'])}" for l in matched)
            un = [l["item"] for l in lines if l.get("unmatched")]
            extra = ("\nNahi mile: " + ", ".join(un)) if un else ""
            return Response({"answer": f"Parcha:\n{txt}\n———\nTotal: {_m(total)}{extra}\n(POS me jaakar isse bill bana sakte ho.)",
                             "bill": {"lines": lines, "total": total}})
        return Response({"answer": "Koi item match nahi hua. Items pehle add karo ya naam saaf bolo."})

    if any(w in ql for w in ["udhaar", "udhar", "receivable", "baaki", "outstanding", "len", "credit", "kaun", "vasool"]):
        return Response({"answer": _receivable_answer(ql)})
    if any(w in ql for w in ["low stock", "lowstock", "kam stock", "khatam", "stock kam", "reorder"]):
        return Response({"answer": _lowstock_answer(ql)})
    if any(w in ql for w in ["kharch", "kharcha", "expense", "expenses", "spent"]):
        return Response({"answer": _expense_answer(ql)})
    if any(w in ql for w in ["profit", "munafa", "kamaya", "kamai", "fayda", "margin"]):
        return Response({"answer": _profit_answer(ql)})
    if any(w in ql for w in ["top customer", "best customer", "sabse zyada", "top party", "grahak"]):
        return Response({"answer": _top_customer_answer(ql)})
    if any(w in ql for w in ["sale", "bikri", "becha", "sell", "revenue", "kitna bika", "kitni bikri"]):
        return Response({"answer": _sales_answer(ql)})

    return Response({"answer": _help()})


def _help():
    return ("Namaste! Main aapka Munshi hoon. Poochh sakte ho:\n"
            "• \"Aaj ki bikri kitni hui?\"\n"
            "• \"Kaun udhaar me sabse peeche hai?\"\n"
            "• \"Is mahine ka kharch?\"\n"
            "• \"Low stock kya hai?\"\n"
            "• \"Top customer kaun?\"\n"
            "• \"Parcha: do kilo cheeni, ek Parle-G\"")
