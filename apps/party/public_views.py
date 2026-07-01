"""Customer digital khata — public page (Khatabook/OkCredit jaisa).
Customer apne token-link se apna udhaar balance + poora ledger dekh sakta hai,
aur UPI se seedhe pay kar sakta hai. Koi login nahi.
"""
from decimal import Decimal
from urllib.parse import quote
from django.http import Http404
from django.shortcuts import render
from .models import Party


def _org_upi_name(org):
    upi = ""
    try:
        from apps.cashbank.models import BankAccount
        acc = BankAccount.all_objects.filter(organization=org).exclude(upi_id="").order_by("id").first()
        if acc:
            upi = acc.upi_id
    except Exception:
        pass
    name = getattr(org, "name", "Business")
    try:
        from apps.core.models import Company
        c = Company.all_objects.filter(organization=org, is_active=True).first()
        if c and c.name:
            name = c.name
    except Exception:
        pass
    return upi, name


def _ledger(party):
    from apps.billing.models import Voucher
    from apps.payments.models import Payment
    opening = Decimal(str(party.opening_balance or 0))
    bal = float(opening if party.opening_balance_type == "DR" else -opening)
    ent = []
    for v in Voucher.all_objects.filter(party=party, is_posted=True):
        eff = 1 if v.voucher_type in ("SALE", "DEBIT_NOTE") else (-1 if v.voucher_type in ("SALE_RETURN", "CREDIT_NOTE", "PURCHASE") else 0)
        if eff:
            ent.append((str(v.date), v.get_voucher_type_display(), v.number, eff * float(v.grand_total)))
    for p in Payment.all_objects.filter(party=party):
        eff = -1 if p.payment_type == "RECEIPT" else 1
        ent.append((str(p.date), p.get_payment_type_display(), p.number, eff * float(p.amount)))
    ent.sort(key=lambda e: e[0])
    rows = []
    run = bal
    for d, t, n, amt in ent:
        run += amt
        rows.append({"date": d, "type": t, "number": n,
                     "debit": amt if amt > 0 else 0, "credit": -amt if amt < 0 else 0,
                     "balance": round(run, 2)})
    rows.reverse()  # latest upar
    return round(run, 2), rows


def party_khata(request, token):
    party = Party.all_objects.filter(khata_token=token).select_related("organization").first()
    if not party:
        raise Http404("Not found")
    org = party.organization
    closing, rows = _ledger(party)
    upi, biz = _org_upi_name(org)
    owe = closing if closing > 0 else 0  # customer ko itna dena hai
    amt_str = f"{owe:.0f}"
    upi_link = ""
    if upi and owe > 0:
        upi_link = (f"upi://pay?pa={quote(upi)}&pn={quote(biz)}"
                    f"&am={amt_str}&cu=INR&tn={quote('Udhaar payment ' + biz)}")
    ctx = {
        "party": party, "biz": biz, "closing": abs(closing),
        "owe": owe, "to_receive": closing > 0, "rows": rows,
        "upi_link": upi_link, "upi": upi,
    }
    return render(request, "khata_public.html", ctx)
