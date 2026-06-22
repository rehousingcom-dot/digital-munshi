"""Dashboard & reports — deck slide 3.
Sab read-only aggregation endpoints. Live data se compute hote hain.
"""
from datetime import timedelta, date
from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.billing.models import Voucher, VoucherLine
from apps.inventory.models import ItemVariant, Stock, ItemUnitPrice
from apps.party.models import Party


def _range(request):
    try:
        days = int(request.query_params.get("days", 30))
    except (TypeError, ValueError):
        days = 30
    end = timezone.localdate()
    start = end - timedelta(days=days - 1)
    return start, end, days


def _sale_lines(start, end):
    return VoucherLine.objects.filter(
        voucher__voucher_type="SALE",
        voucher__is_posted=True,
        voucher__date__gte=start, voucher__date__lte=end,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard(request):
    """Ek hi call mein poora dashboard — frontend ke liye convenient."""
    start, end, days = _range(request)
    sales = Voucher.objects.filter(voucher_type="SALE", is_posted=True,
                                   date__gte=start, date__lte=end)

    # --- Summary KPIs ---
    agg = sales.aggregate(
        total_sales=Coalesce(Sum("grand_total"), Decimal("0")),
        total_taxable=Coalesce(Sum("taxable_value"), Decimal("0")),
        total_tax=Coalesce(Sum("total_tax"), Decimal("0")),
    )
    invoice_count = sales.count()

    # --- Previous period comparison (real trend %) ---
    prev_start = start - timedelta(days=days)
    prev_end = start - timedelta(days=1)
    prev_sales = (Voucher.objects.filter(voucher_type="SALE", is_posted=True,
                  date__gte=prev_start, date__lte=prev_end)
                  .aggregate(t=Coalesce(Sum("grand_total"), Decimal("0")))["t"])
    cur = float(agg["total_sales"]); prev = float(prev_sales)
    sales_change_pct = round(((cur - prev) / prev * 100), 1) if prev > 0 else (100.0 if cur > 0 else 0.0)

    total_purchases = (Voucher.objects.filter(voucher_type="PURCHASE", is_posted=True,
                       date__gte=start, date__lte=end)
                       .aggregate(t=Coalesce(Sum("grand_total"), Decimal("0")))["t"])

    # --- Sales trend (din-wise) --- 'date' already DateField hai
    trend_qs = (sales.values("date")
                .annotate(amount=Sum("grand_total")).order_by("date"))
    sales_trend = [{"date": str(r["date"]), "amount": float(r["amount"] or 0)} for r in trend_qs]

    # --- Item-wise sold (hot / slow selling) ---
    lines = _sale_lines(start, end)
    by_item = (lines.values("variant", "variant__item__name", "variant__item_code")
               .annotate(qty=Sum("qty_primary"), value=Sum("taxable_value"))
               .order_by("-qty"))
    by_item = list(by_item)
    def fmt(rows):
        return [{
            "variant_id": r["variant"],
            "item": r["variant__item__name"],
            "item_code": r["variant__item_code"],
            "qty": float(r["qty"] or 0),
            "value": float(r["value"] or 0),
        } for r in rows]
    hot_selling = fmt(by_item[:10])
    slow_selling = fmt(list(reversed(by_item))[:10])

    # --- Profit trend (taxable sales - cost) ---
    # Cost = ItemUnitPrice.purchase_price (primary unit) * qty_primary
    cost_map = {p["variant"]: p["purchase_price"] for p in
                ItemUnitPrice.objects.values("variant").annotate(
                    purchase_price=Coalesce(Sum("purchase_price"), Decimal("0")))}
    total_profit = Decimal("0")
    for r in by_item:
        cost = Decimal(str(cost_map.get(r["variant"], 0))) * (r["qty"] or Decimal("0"))
        total_profit += (r["value"] or Decimal("0")) - cost

    # --- Slow moving / dead stock: stock > 0 but range mein koi sale nahi ---
    sold_variant_ids = set(r["variant"] for r in by_item)
    in_stock = (Stock.objects.values("variant", "variant__item__name", "variant__item_code")
                .annotate(qty=Sum("quantity")).filter(qty__gt=0))
    dead_stock = [{
        "item": s["variant__item__name"], "item_code": s["variant__item_code"],
        "stock_qty": float(s["qty"] or 0),
    } for s in in_stock if s["variant"] not in sold_variant_ids][:15]

    # --- Stock value (qty * purchase price) ---
    stock_value = Decimal("0")
    for srow in Stock.objects.values("variant").annotate(qty=Sum("quantity")):
        cost = Decimal(str(cost_map.get(srow["variant"], 0)))
        stock_value += (srow["qty"] or Decimal("0")) * cost

    # --- Cash flow: actual receivables (sales - receipts) across all parties ---
    from apps.payments.models import party_balance
    receivables = Decimal("0")
    payables = Decimal("0")
    for p in Party.objects.filter(is_active=True):
        bal = party_balance(p)
        if bal["balance"] > 0:
            receivables += bal["balance"]
        else:
            payables += bal["abs"]

    # --- Top customers (by sales) ---
    top_cust = (sales.values("party__name").annotate(total=Sum("grand_total")).order_by("-total")[:6])
    top_customers = [{"name": r["party__name"], "total": float(r["total"] or 0)} for r in top_cust]

    # --- Top categories (product groups) ---
    cat = (lines.values("variant__item__category__name")
           .annotate(qty=Sum("qty_primary"), value=Sum("taxable_value")).order_by("-value")[:6])
    top_categories = [{"name": r["variant__item__category__name"] or "Uncategorized",
                       "value": float(r["value"] or 0), "qty": float(r["qty"] or 0)} for r in cat]

    # --- Profit trend (daily: taxable - cost) ---
    from collections import defaultdict
    day_tax = defaultdict(float); day_cost = defaultdict(float)
    for l in lines.values("voucher__date", "variant", "taxable_value", "qty_primary"):
        dt = str(l["voucher__date"])
        day_tax[dt] += float(l["taxable_value"] or 0)
        day_cost[dt] += float(cost_map.get(l["variant"], 0)) * float(l["qty_primary"] or 0)
    profit_trend = [{"date": dt, "profit": round(day_tax[dt] - day_cost[dt], 2)} for dt in sorted(day_tax)]

    # --- Cash flow risk: overdue receivables (sales older than 60 days, posted) ---
    overdue_cut = end - timedelta(days=60)
    overdue = (Voucher.objects.filter(voucher_type="SALE", is_posted=True, date__lt=overdue_cut)
               .aggregate(t=Coalesce(Sum("grand_total"), Decimal("0")))["t"])
    cash_flow_risk = float(overdue)

    return Response({
        "period": {"from": str(start), "to": str(end), "days": days},
        "top_customers": top_customers,
        "top_categories": top_categories,
        "cash_flow_risk": cash_flow_risk,
        "profit_trend": profit_trend,
        "summary": {
            "total_sales": float(agg["total_sales"]),
            "total_taxable": float(agg["total_taxable"]),
            "total_tax": float(agg["total_tax"]),
            "total_profit": float(total_profit),
            "invoice_count": invoice_count,
            "sales_change_pct": sales_change_pct,
            "low_stock_count": len(dead_stock),
            "total_purchases": float(total_purchases),
            "stock_value": float(stock_value),
        },
        "sales_trend": sales_trend,
        "hot_selling": hot_selling,
        "slow_selling": slow_selling,
        "dead_stock": dead_stock,
        "cash_flow": {
            "receivables": float(receivables),
            "payables": float(payables),
            "note": "Receivable = customers se baaki; Payable = suppliers ko dena.",
        },
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def gst_report(request):
    """GSTR-style GST summary — deck GST compliance.
    Output tax (sales) vs Input tax (purchases), rate-wise + B2B/B2C split.
    GET /api/reports/gst/?days=30
    """
    from apps.billing.models import VoucherLine, Voucher
    start, end, days = _range(request)

    def summarize(vtype):
        lines = VoucherLine.objects.filter(
            voucher__voucher_type=vtype, voucher__is_posted=True,
            voucher__date__gte=start, voucher__date__lte=end,
        )
        by_rate = (lines.values("tax_percent")
                   .annotate(taxable=Coalesce(Sum("taxable_value"), Decimal("0")),
                             cgst=Coalesce(Sum("cgst"), Decimal("0")),
                             sgst=Coalesce(Sum("sgst"), Decimal("0")),
                             igst=Coalesce(Sum("igst"), Decimal("0")),
                             tax=Coalesce(Sum("tax_amount"), Decimal("0")))
                   .order_by("tax_percent"))
        rows, totals = [], {"taxable": 0.0, "cgst": 0.0, "sgst": 0.0, "igst": 0.0, "tax": 0.0}
        for r in by_rate:
            rows.append({
                "rate": float(r["tax_percent"]),
                "taxable": float(r["taxable"]), "cgst": float(r["cgst"]),
                "sgst": float(r["sgst"]), "igst": float(r["igst"]), "tax": float(r["tax"]),
            })
            for k in totals:
                totals[k] += float(r[k])
        return {"by_rate": rows, "totals": totals}

    # B2B vs B2C (sales) — party ke paas GSTIN hai ya nahi
    sales = Voucher.objects.filter(voucher_type="SALE", is_posted=True,
                                   date__gte=start, date__lte=end)
    b2b = sales.exclude(party__gstin="").aggregate(
        taxable=Coalesce(Sum("taxable_value"), Decimal("0")),
        tax=Coalesce(Sum("total_tax"), Decimal("0")))
    b2c = sales.filter(party__gstin="").aggregate(
        taxable=Coalesce(Sum("taxable_value"), Decimal("0")),
        tax=Coalesce(Sum("total_tax"), Decimal("0")))

    output = summarize("SALE")     # tax collected on sales
    inp = summarize("PURCHASE")    # input tax credit
    net = output["totals"]["tax"] - inp["totals"]["tax"]

    return Response({
        "period": {"from": str(start), "to": str(end), "days": days},
        "output_tax_sales": output,
        "input_tax_purchases": inp,
        "b2b": {"taxable": float(b2b["taxable"]), "tax": float(b2b["tax"])},
        "b2c": {"taxable": float(b2c["taxable"]), "tax": float(b2c["tax"])},
        "net_gst_payable": round(net, 2),
        "note": "Net = Output tax (sales) - Input tax credit (purchases).",
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def low_stock(request):
    """Reorder level se kam stock waale items — restocking alert."""
    from apps.inventory.models import Item, Stock
    rows = []
    for item in Item.objects.filter(item_type="GOODS", reorder_level__gt=0, is_active=True):
        qty = (Stock.objects.filter(variant__item=item)
               .aggregate(q=Coalesce(Sum("quantity"), Decimal("0")))["q"])
        if qty < item.reorder_level:
            rows.append({"item": item.name, "current_stock": float(qty),
                         "reorder_level": float(item.reorder_level),
                         "shortfall": float(item.reorder_level - qty)})
    return Response({"count": len(rows), "items": rows})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def gstr1(request):
    """GSTR-1 style: B2B invoices, B2C summary, HSN summary."""
    from apps.billing.models import Voucher, VoucherLine
    start, end, days = _range(request)
    sales = Voucher.objects.filter(voucher_type="SALE", is_posted=True,
                                   date__gte=start, date__lte=end)
    b2b = [{
        "invoice": v.number, "date": str(v.date), "party": v.party.name,
        "gstin": v.party.gstin, "taxable": float(v.taxable_value), "tax": float(v.total_tax),
        "total": float(v.grand_total),
    } for v in sales.exclude(party__gstin="").select_related("party")]
    b2c = sales.filter(party__gstin="").aggregate(
        taxable=Coalesce(Sum("taxable_value"), Decimal("0")),
        tax=Coalesce(Sum("total_tax"), Decimal("0")))
    # HSN summary
    hsn = (VoucherLine.objects.filter(voucher__in=sales)
           .values("variant__item__hsn_code", "tax_percent")
           .annotate(qty=Coalesce(Sum("qty_primary"), Decimal("0")),
                     taxable=Coalesce(Sum("taxable_value"), Decimal("0")),
                     tax=Coalesce(Sum("tax_amount"), Decimal("0")))
           .order_by("variant__item__hsn_code"))
    hsn_rows = [{"hsn": h["variant__item__hsn_code"] or "-", "rate": float(h["tax_percent"]),
                 "qty": float(h["qty"]), "taxable": float(h["taxable"]), "tax": float(h["tax"])}
                for h in hsn]
    return Response({
        "period": {"from": str(start), "to": str(end)},
        "b2b": {"count": len(b2b), "invoices": b2b},
        "b2c": {"taxable": float(b2c["taxable"]), "tax": float(b2c["tax"])},
        "hsn_summary": hsn_rows,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def profit_and_loss(request):
    """Simplified P&L — Revenue (sales taxable) vs Cost (purchase taxable) = Gross Profit."""
    from apps.billing.models import Voucher
    start, end, days = _range(request)
    def tot(vt):
        return Voucher.objects.filter(voucher_type=vt, is_posted=True, date__gte=start, date__lte=end
                                      ).aggregate(t=Coalesce(Sum("taxable_value"), Decimal("0")))["t"]
    revenue = tot("SALE") - tot("SALE_RETURN")
    purchases = tot("PURCHASE") - tot("PURCHASE_RETURN")
    gross = revenue - purchases
    # Expenses (rent, diesel, salary etc) — net profit ke liye
    expenses = Decimal("0")
    try:
        from apps.cashbank.models import Expense
        for e in Expense.objects.filter(date__gte=start, date__lte=end):
            expenses += Decimal(str(e.amount)) + Decimal(str(e.tax_amount))
    except Exception:
        pass
    net = gross - expenses
    return Response({
        "period": {"from": str(start), "to": str(end)},
        "revenue": float(revenue), "purchases": float(purchases),
        "gross_profit": float(gross), "expenses": float(expenses),
        "net_profit": float(net),
        "note": "Cash-basis simplified P&L (revenue − purchases − expenses).",
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def day_book(request):
    """Ek din/period ke saare vouchers + payments chronological."""
    from apps.billing.models import Voucher
    from apps.payments.models import Payment
    start, end, days = _range(request)
    rows = []
    for v in Voucher.objects.filter(date__gte=start, date__lte=end).select_related("party"):
        rows.append({"date": str(v.date), "type": v.get_voucher_type_display(),
                     "number": v.number, "party": v.party.name, "amount": float(v.grand_total)})
    for p in Payment.objects.filter(date__gte=start, date__lte=end).select_related("party"):
        rows.append({"date": str(p.date), "type": p.get_payment_type_display(),
                     "number": p.number, "party": p.party.name, "amount": float(p.amount)})
    rows.sort(key=lambda r: r["date"])
    return Response({"period": {"from": str(start), "to": str(end)}, "count": len(rows), "entries": rows})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def party_statement(request):
    """Ek party ka ledger — sare transactions running balance ke saath.
    GET /api/reports/party-statement/?party=<id>
    """
    from apps.billing.models import Voucher
    from apps.payments.models import Payment
    pid = request.query_params.get("party")
    party = Party.objects.filter(pk=pid).first()
    if not party:
        return Response({"error": "party not found"}, status=404)
    opening = Decimal(str(party.opening_balance or 0))
    opening_signed = opening if party.opening_balance_type == "DR" else -opening
    entries = []
    for v in Voucher.objects.filter(party=party, is_posted=True):
        eff = 1 if v.voucher_type in ("SALE", "DEBIT_NOTE") else (-1 if v.voucher_type in ("SALE_RETURN", "CREDIT_NOTE", "PURCHASE") else 0)
        if eff:
            entries.append((v.date, v.get_voucher_type_display(), v.number, eff * float(v.grand_total)))
    for p in Payment.objects.filter(party=party):
        eff = -1 if p.payment_type == "RECEIPT" else 1
        entries.append((p.date, p.get_payment_type_display(), p.number, eff * float(p.amount)))
    entries.sort(key=lambda e: str(e[0]))
    bal = float(opening_signed)
    rows = [{"date": "opening", "type": "Opening Balance", "number": "", "debit": 0, "credit": 0, "balance": bal}]
    for d, t, n, amt in entries:
        bal += amt
        rows.append({"date": str(d), "type": t, "number": n,
                     "debit": amt if amt > 0 else 0, "credit": -amt if amt < 0 else 0,
                     "balance": round(bal, 2)})
    return Response({"party": party.name, "closing_balance": round(bal, 2),
                     "closing_type": "To Receive" if bal >= 0 else "To Pay", "entries": rows})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def purchase_register(request):
    """Purchase vouchers list — GST input ke liye."""
    from apps.billing.models import Voucher
    start, end, days = _range(request)
    rows = [{
        "date": str(v.date), "number": v.number, "supplier": v.party.name,
        "gstin": v.party.gstin, "taxable": float(v.taxable_value),
        "tax": float(v.total_tax), "total": float(v.grand_total),
    } for v in Voucher.objects.filter(voucher_type="PURCHASE", is_posted=True,
                                      date__gte=start, date__lte=end).select_related("party")]
    return Response({"period": {"from": str(start), "to": str(end)},
                     "count": len(rows), "purchases": rows})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def receivables_aging(request):
    """Receivables ko age buckets mein (0-30/31-60/61-90/90+ days) — cash-flow ke liye."""
    from apps.billing.models import Voucher
    from django.utils import timezone
    today = timezone.localdate()
    buckets = {"0-30": 0.0, "31-60": 0.0, "61-90": 0.0, "90+": 0.0}
    for v in Voucher.objects.filter(voucher_type="SALE", is_posted=True):
        age = (today - v.date).days
        amt = float(v.grand_total)
        key = "0-30" if age <= 30 else "31-60" if age <= 60 else "61-90" if age <= 90 else "90+"
        buckets[key] += amt
    return Response({"as_on": str(today), "buckets": {k: round(x, 2) for k, x in buckets.items()},
                     "total": round(sum(buckets.values()), 2)})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def stock_valuation(request):
    """Live stock per item per godown, value (purchase price wise)."""
    from apps.inventory.models import ItemUnitPrice
    rows = []
    total_value = Decimal("0")
    qs = Stock.objects.select_related("variant", "variant__item", "godown", "variant__item__primary_unit").filter(quantity__gt=0)
    for s in qs.order_by("variant__item__name"):
        up = ItemUnitPrice.objects.filter(variant=s.variant, unit=s.variant.item.primary_unit).first()
        pp = Decimal(str(up.purchase_price)) if up and up.purchase_price else Decimal("0")
        sp = Decimal(str(up.sale_price)) if up and up.sale_price else Decimal(str(s.variant.item.mrp or 0))
        qty = Decimal(str(s.quantity))
        value = qty * pp
        total_value += value
        rows.append({
            "item": s.variant.item.name,
            "item_code": s.variant.item_code,
            "godown": s.godown.name if s.godown else "-",
            "unit": s.variant.item.primary_unit.short_code if s.variant.item.primary_unit else "",
            "qty": float(qty), "purchase_price": float(pp), "sale_price": float(sp),
            "value": float(value),
        })
    return Response({"count": len(rows), "total_value": float(total_value), "items": rows})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def payment_reminders(request):
    """Overdue customers (receivable) — WhatsApp reminder ke liye list.
    credit_days ke aadhar pe overdue decide. Phone bhi return.
    """
    from apps.party.models import Party
    from apps.payments.models import party_balance
    from apps.billing.models import Voucher
    today = timezone.localdate()
    out = []
    for p in Party.objects.all():
        try:
            b = party_balance(p)
        except Exception:
            continue
        bal = Decimal(str(b.get("balance", 0) or 0))
        if bal <= 0:
            continue  # nothing to receive
        # last unpaid sale date -> days overdue
        last_sale = Voucher.objects.filter(party=p, voucher_type="SALE", is_posted=True).order_by("-date").first()
        days_over = 0
        if last_sale:
            days_over = max(0, (today - last_sale.date).days - int(p.credit_days or 0))
        out.append({
            "party_id": p.id, "name": p.name, "phone": p.phone or "",
            "amount": float(bal), "days_overdue": days_over,
            "credit_days": int(p.credit_days or 0),
        })
    out.sort(key=lambda x: -x["amount"])
    total = sum(x["amount"] for x in out)
    return Response({"count": len(out), "total_receivable": float(total), "parties": out})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def gstr3b(request):
    """GSTR-3B summary: outward (sales) tax liability + inward (purchase) ITC."""
    from apps.billing.models import Voucher
    start, end, days = _range(request)

    def agg(vt):
        return Voucher.objects.filter(voucher_type=vt, is_posted=True,
                                      date__gte=start, date__lte=end).aggregate(
            taxable=Coalesce(Sum("taxable_value"), Decimal("0")),
            cgst=Coalesce(Sum("cgst"), Decimal("0")),
            sgst=Coalesce(Sum("sgst"), Decimal("0")),
            igst=Coalesce(Sum("igst"), Decimal("0")))
    out = agg("SALE")
    inw = agg("PURCHASE")
    out_tax = out["cgst"] + out["sgst"] + out["igst"]
    itc = inw["cgst"] + inw["sgst"] + inw["igst"]
    net = out_tax - itc
    return Response({
        "period": {"from": str(start), "to": str(end)},
        "outward": {"taxable": float(out["taxable"]), "cgst": float(out["cgst"]),
                    "sgst": float(out["sgst"]), "igst": float(out["igst"]), "total_tax": float(out_tax)},
        "inward_itc": {"taxable": float(inw["taxable"]), "cgst": float(inw["cgst"]),
                       "sgst": float(inw["sgst"]), "igst": float(inw["igst"]), "total_itc": float(itc)},
        "net_payable": float(net),
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def hsn_summary(request):
    """HSN/SAC-wise sale summary (GSTR-1 Table 12)."""
    from apps.billing.models import VoucherLine
    start, end, days = _range(request)
    rows = (VoucherLine.objects.filter(voucher__voucher_type="SALE", voucher__is_posted=True,
                                       voucher__date__gte=start, voucher__date__lte=end)
            .values("variant__item__hsn_code", "tax_percent")
            .annotate(qty=Coalesce(Sum("qty_primary"), Decimal("0")),
                      taxable=Coalesce(Sum("taxable_value"), Decimal("0")),
                      cgst=Coalesce(Sum("cgst"), Decimal("0")),
                      sgst=Coalesce(Sum("sgst"), Decimal("0")),
                      igst=Coalesce(Sum("igst"), Decimal("0")))
            .order_by("variant__item__hsn_code"))
    data = [{"hsn": r["variant__item__hsn_code"] or "-", "rate": float(r["tax_percent"]),
             "qty": float(r["qty"]), "taxable": float(r["taxable"]),
             "cgst": float(r["cgst"]), "sgst": float(r["sgst"]), "igst": float(r["igst"]),
             "total": float(r["taxable"] + r["cgst"] + r["sgst"] + r["igst"])} for r in rows]
    return Response({"period": {"from": str(start), "to": str(end)}, "rows": data})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def balance_sheet(request):
    """Simplified Balance Sheet — assets (stock + receivables + cash/bank) vs
    liabilities (payables + loans + capital). Capital balancing figure.
    """
    from apps.billing.models import Voucher
    from apps.payments.models import party_balance
    from apps.party.models import Party
    receivable = payable = Decimal("0")
    for p in Party.objects.all():
        try:
            b = party_balance(p)
            bal = Decimal(str(b.get("balance", 0) or 0))
            if bal >= 0:
                receivable += bal
            else:
                payable += -bal
        except Exception:
            pass
    # stock value approx = sum(qty * purchase_price)
    from apps.inventory.models import Stock, ItemUnitPrice
    stock_value = Decimal("0")
    for s in Stock.objects.select_related("variant", "variant__item").all():
        up = ItemUnitPrice.objects.filter(variant=s.variant,
                                           unit=s.variant.item.primary_unit).first()
        pp = Decimal(str(up.purchase_price)) if up else Decimal("0")
        stock_value += Decimal(str(s.quantity)) * pp
    # cash/bank
    cash_bank = Decimal("0")
    try:
        from apps.cashbank.models import BankAccount, LoanAccount
        cash_bank = sum((a.balance for a in BankAccount.objects.all()), Decimal("0"))
        loans = sum((l.current_balance for l in LoanAccount.objects.all()), Decimal("0"))
    except Exception:
        loans = Decimal("0")
    assets = stock_value + receivable + cash_bank
    liabilities_ex_capital = payable + loans
    capital = assets - liabilities_ex_capital
    return Response({
        "assets": {"stock_value": float(stock_value), "receivables": float(receivable),
                   "cash_and_bank": float(cash_bank), "total": float(assets)},
        "liabilities": {"payables": float(payable), "loans": float(loans),
                        "capital": float(capital), "total": float(assets)},
        "note": "Simplified accrual snapshot — capital balancing figure hai.",
    })
