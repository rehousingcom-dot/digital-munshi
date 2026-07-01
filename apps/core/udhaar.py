"""Udhaar (credit) helpers — UPI pay-link WhatsApp reminder + Bharosa credit score.
Bina kisi paid gateway ke: UPI intent link (upi://pay) banata hai jo mobile pe
ek-tap payment kholta hai. Bharosa score party ke payment behaviour se banta hai.
"""
from decimal import Decimal
from urllib.parse import quote
from django.utils import timezone
from django.db.models import Sum
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


def _org_upi_and_name():
    upi = ""
    try:
        from apps.cashbank.models import BankAccount
        acc = BankAccount.objects.exclude(upi_id="").order_by("id").first()
        if acc:
            upi = acc.upi_id
    except Exception:
        pass
    name = "My Business"
    try:
        from apps.core.models import Company
        c = Company.objects.filter(is_active=True).first()
        if c:
            name = c.name
    except Exception:
        pass
    return upi, name


def bharosa_score(party):
    """Party ka credit-behaviour score (0-100) — kitni imaandaari se chukता hai."""
    from apps.billing.models import Voucher
    from apps.payments.models import Payment, party_balance
    today = timezone.localdate()
    sales = Voucher.objects.filter(party=party, voucher_type="SALE", is_posted=True)
    sales_total = sales.aggregate(s=Sum("grand_total"))["s"] or Decimal("0")
    sales_cnt = sales.count()
    receipts = Payment.objects.filter(party=party, payment_type="RECEIPT").aggregate(s=Sum("amount"))["s"] or Decimal("0")
    bal = party_balance(party)
    outstanding = Decimal(str(bal.get("balance", 0) or 0))

    # days overdue (last sale vs credit days)
    last_sale = sales.order_by("-date").first()
    days_over = 0
    if last_sale and outstanding > 0:
        days_over = max(0, (today - last_sale.date).days - int(party.credit_days or 0))

    score = 60.0
    # payment ratio (kitna chukaya)
    if sales_total > 0:
        ratio = float(receipts) / float(sales_total)
        score += min(25.0, ratio * 25.0)
    else:
        score += 10  # koi udhaar liya hi nahi
    # overdue penalty
    if days_over > 0:
        score -= min(35.0, days_over * 0.6)
    # history bonus
    if sales_cnt >= 5:
        score += 10
    elif sales_cnt >= 2:
        score += 4
    score = max(5, min(99, round(score)))
    if score >= 80:
        label, tone = "Bahut acha", "green"
    elif score >= 60:
        label, tone = "Theek", "blue"
    elif score >= 40:
        label, tone = "Dhyan do", "amber"
    else:
        label, tone = "Risky", "red"
    return {"score": int(score), "label": label, "tone": tone,
            "days_overdue": days_over, "outstanding": float(outstanding),
            "paid_total": float(receipts), "sales_total": float(sales_total),
            "invoices": sales_cnt}


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def bharosa(request):
    from apps.party.models import Party
    pid = request.GET.get("party")
    p = Party.objects.filter(pk=pid).first()
    if not p:
        return Response({"detail": "party not found"}, status=404)
    return Response({"party": p.name, **bharosa_score(p)})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def udhaar_reminder(request):
    """Ek party ke liye WhatsApp reminder + UPI pay-link banata hai.
    ?party=id"""
    from apps.party.models import Party
    from apps.payments.models import party_balance
    pid = request.GET.get("party")
    p = Party.objects.filter(pk=pid).first()
    if not p:
        return Response({"detail": "party not found"}, status=404)
    bal = party_balance(p)
    amount = float(bal.get("balance", 0) or 0)
    upi, biz = _org_upi_and_name()
    amt_str = f"{amount:.0f}"
    upi_link = ""
    if upi:
        upi_link = (f"upi://pay?pa={quote(upi)}&pn={quote(biz)}"
                    f"&am={amt_str}&cu=INR&tn={quote('Bill payment ' + biz)}")
    msg = (f"Namaste {p.name} ji,\n{biz} me aapke ₹{amt_str} baaki hain. "
           f"Kripya jaldi payment karein.")
    if upi_link:
        msg += f"\n\nUPI se pay karein (mobile pe tap): {upi_link}"
    elif upi:
        msg += f"\n\nUPI: {upi}"
    digits = "".join(ch for ch in (p.phone or "") if ch.isdigit())
    wa_to = ("91" + digits[-10:]) if len(digits) >= 10 else digits
    wa_url = f"https://wa.me/{wa_to}?text={quote(msg)}" if wa_to else f"https://wa.me/?text={quote(msg)}"
    return Response({
        "party": p.name, "phone": p.phone or "", "amount": amount,
        "upi_id": upi, "upi_link": upi_link, "message": msg, "wa_url": wa_url,
        "bharosa": bharosa_score(p),
        "upi_configured": bool(upi),
    })
