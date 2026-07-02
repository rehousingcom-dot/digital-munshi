import csv
from io import TextIOWrapper
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.clickjacking import xframe_options_exempt
from apps.tenants.tenancy import set_current_org


@xframe_options_exempt
def customer_portal(request, share):
    """Public customer portal — party apna ledger/outstanding dekh sakta hai (login ke bina)."""
    party = Party.all_objects.filter(share_uuid=share).first()
    if not party:
        return HttpResponse("Portal link invalid", status=404)
    set_current_org(party.organization)
    from apps.payments.models import party_balance
    from apps.billing.models import Voucher
    try:
        bal = party_balance(party)
    except Exception:
        bal = {"abs": 0, "label": "—"}
    invoices = Voucher.all_objects.filter(party=party, organization=party.organization,
                                          voucher_type="SALE").order_by("-date")[:30]
    from apps.core.models import Company
    company = Company.all_objects.filter(organization=party.organization, is_active=True).first()
    return render(request, "portal.html", {
        "party": party, "balance": bal, "invoices": invoices, "company": company,
    })
from rest_framework import viewsets, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.tenants.tenancy import OrgScopedQuerysetMixin
from .models import Party, PartyDocument
from .serializers import PartySerializer, PartyDocumentSerializer
from .validators import GSTIN_REGEX, gstin_checksum_ok, gstin_info


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def parties_export(request):
    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = 'attachment; filename="parties.csv"'
    w = csv.writer(resp)
    w.writerow(["name", "party_type", "gstin", "phone", "email", "city", "state", "opening_balance", "opening_balance_type"])
    for p in Party.objects.all():
        w.writerow([p.name, p.party_type, p.gstin, p.phone, p.email, p.city, p.state,
                    p.opening_balance, p.opening_balance_type])
    return resp


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def parties_import(request):
    f = request.FILES.get("file")
    if not f:
        return Response({"detail": "CSV file 'file' field me bhejein"}, status=400)
    reader = csv.DictReader(TextIOWrapper(f.file, encoding="utf-8"))
    created = 0
    for row in reader:
        name = (row.get("name") or "").strip()
        if not name:
            continue
        Party.objects.create(
            name=name, party_type=(row.get("party_type") or "CUSTOMER").strip().upper(),
            gstin=(row.get("gstin") or "").strip(), phone=(row.get("phone") or "").strip(),
            email=(row.get("email") or "").strip(), city=(row.get("city") or "").strip(),
            state=(row.get("state") or "").strip(),
        )
        created += 1
    return Response({"created": created})


class PartyViewSet(OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Party.objects.all().prefetch_related("documents")
    serializer_class = PartySerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "legal_name", "gstin", "phone"]

    POINT_VALUE = 1  # ₹1 per loyalty point
    MIN_REDEEM = 100  # min points to redeem

    @action(detail=True, methods=["post"])
    def redeem_points(self, request, pk=None):
        """Loyalty points redeem karo → rupee discount value milta hai.
        body: {points}  (default = saare available points)"""
        p = self.get_object()
        avail = int(p.loyalty_points or 0)
        req = request.data.get("points")
        pts = int(req) if req not in (None, "") else avail
        if pts <= 0:
            return Response({"detail": "Kuch points redeem karne ke liye chahiye"}, status=400)
        if pts > avail:
            return Response({"detail": f"Sirf {avail} points available"}, status=400)
        if avail >= self.MIN_REDEEM and pts < self.MIN_REDEEM:
            return Response({"detail": f"Minimum {self.MIN_REDEEM} points redeem karo"}, status=400)
        value = pts * self.POINT_VALUE
        p.loyalty_points = avail - pts
        p.save(update_fields=["loyalty_points"])
        return Response({"redeemed_points": pts, "value": value,
                         "remaining_points": p.loyalty_points,
                         "detail": f"{pts} points = ₹{value} discount. Bill me ₹{value} kam kar do."})

    @action(detail=False, methods=["get"])
    def check_duplicate(self, request):
        """Deck slide 4: duplicate party name warning.
        GET /api/parties/check_duplicate/?name=Ram%20Traders
        """
        name = request.query_params.get("name", "").strip()
        gstin = request.query_params.get("gstin", "").strip().upper()
        qs = Party.objects.none()
        if name:
            qs = Party.objects.filter(name__iexact=name)
        matches = list(qs.values("id", "name", "gstin", "phone", "city"))
        gstin_match = None
        if gstin:
            g = Party.objects.filter(gstin=gstin).values("id", "name").first()
            gstin_match = g
        return Response({
            "name_exists": bool(matches),
            "name_matches": matches,
            "gstin_exists": bool(gstin_match),
            "gstin_match": gstin_match,
        })

    @action(detail=False, methods=["get"])
    def verify_gstin(self, request):
        """Deck slide 4: GSTIN verify -> legal name + address + state auto-fill.
        GET /api/parties/verify_gstin/?gstin=06CBZPN8878H1ZH

        Format + checksum verify hota hai aur structured info (state, PAN) return.
        Production me yahan real GST API (e.g. gst.gov.in / 3rd-party) plug hoga jo
        legal_name + principal address bhi laayega — dev-mode me state/PAN decode + hint.
        """
        g = request.query_params.get("gstin", "").strip().upper()
        if not g:
            return Response({"valid": False, "detail": "GSTIN bhejein"}, status=400)
        fmt_ok = bool(GSTIN_REGEX.match(g))
        sum_ok = gstin_checksum_ok(g)
        if not (fmt_ok and sum_ok):
            return Response({
                "valid": False, "format_ok": fmt_ok, "checksum_ok": sum_ok,
                "detail": "GSTIN format ya checksum galat hai",
            })
        info = gstin_info(g)
        # Same-org me pehle se koi party isi GSTIN se? to uska data suggest
        existing = Party.objects.filter(gstin=g).values(
            "id", "name", "legal_name", "address", "city", "state", "pincode").first()
        legal_name = (existing or {}).get("legal_name") or ""
        trade_name = ""
        address = (existing or {}).get("address") or ""
        city = (existing or {}).get("city") or ""
        pincode = (existing or {}).get("pincode") or ""
        source = "existing_record" if existing else "decoded"
        # Real GST API (agar key configured ho) — legal name + address auto
        api_data = _gst_api_lookup(g)
        if api_data:
            legal_name = api_data.get("legal_name") or legal_name
            trade_name = api_data.get("trade_name") or ""
            address = api_data.get("address") or address
            city = api_data.get("city") or city
            pincode = api_data.get("pincode") or pincode
            if api_data.get("state"):
                info["state"] = api_data["state"]
            source = "gst_api"
        info.update({
            "valid": True, "format_ok": True, "checksum_ok": True,
            "legal_name": legal_name, "trade_name": trade_name,
            "address": address, "city": city, "pincode": pincode,
            "existing_party": existing, "source": source,
        })
        return Response(info)


def _gst_api_lookup(gstin):
    """Real GST API se legal name + address (agar GSTIN_API_KEY configured ho).
    Default: Appyflow-style endpoint. Key na ho ya fail ho to None (decode-only fallback).
    Production me yahan apni GSP/3rd-party API daalein.
    """
    import os
    key = os.environ.get("GSTIN_API_KEY", "")
    if not key:
        return None
    try:
        import requests
        url = os.environ.get("GSTIN_API_URL", "https://appyflow.in/api/verifyGST")
        r = requests.get(url, params={"gstNo": gstin, "key_secret": key}, timeout=6)
        d = r.json()
        tp = d.get("taxpayerInfo") or d.get("data") or {}
        if not tp:
            return None
        pradr = (tp.get("pradr") or {}).get("addr") or {}
        addr_bits = [pradr.get(k) for k in ("bno", "bnm", "st", "loc", "city", "stcd") if pradr.get(k)]
        return {
            "legal_name": tp.get("lgnm", ""),
            "trade_name": tp.get("tradeNam", ""),
            "address": ", ".join([b for b in addr_bits if b]),
            "city": pradr.get("loc", "") or pradr.get("dst", ""),
            "pincode": str(pradr.get("pncd", "") or ""),
            "state": pradr.get("stcd", ""),
        }
    except Exception:
        return None


class PartyDocumentViewSet(OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = PartyDocument.objects.all()
    serializer_class = PartyDocumentSerializer


def _party_ledger(party):
    """Party ka ledger rows + closing balance (party_statement report jaisa)."""
    from decimal import Decimal
    from apps.billing.models import Voucher
    from apps.payments.models import Payment
    opening = Decimal(str(party.opening_balance or 0))
    opening_signed = opening if party.opening_balance_type == "DR" else -opening
    entries = []
    for v in Voucher.all_objects.filter(organization=party.organization, party=party, is_posted=True):
        eff = 1 if v.voucher_type in ("SALE", "DEBIT_NOTE") else (
            -1 if v.voucher_type in ("SALE_RETURN", "CREDIT_NOTE", "PURCHASE") else 0)
        if eff:
            entries.append((v.date, v.get_voucher_type_display(), v.number, eff * float(v.grand_total)))
    for p in Payment.all_objects.filter(organization=party.organization, party=party):
        eff = -1 if p.payment_type == "RECEIPT" else 1
        entries.append((p.date, p.get_payment_type_display(), p.number, eff * float(p.amount)))
    entries.sort(key=lambda e: str(e[0]))
    bal = float(opening_signed)
    rows = [{"date": "Opening", "type": "Opening Balance", "number": "", "debit": "", "credit": "", "balance": round(bal, 2)}]
    for d, t, n, amt in entries:
        bal += amt
        rows.append({"date": str(d), "type": t, "number": n,
                     "debit": round(amt, 2) if amt > 0 else "",
                     "credit": round(-amt, 2) if amt < 0 else "",
                     "balance": round(bal, 2)})
    return rows, round(bal, 2)


def party_statement_doc(request, pk):
    """Party ledger — print-ready HTML ya PDF. Public via ?share=<uuid> (WhatsApp ke liye)."""
    import uuid as _uuid
    from io import BytesIO
    from django.template.loader import render_to_string
    from django.http import HttpResponseForbidden
    from apps.core.models import Company

    share = request.GET.get("share")
    party = None
    if share:
        try:
            _uuid.UUID(str(share))
            party = Party.all_objects.filter(pk=pk, share_uuid=share).first()
        except (ValueError, TypeError):
            party = None
    if not party:
        return HttpResponseForbidden("Galat ya missing share link.")

    rows, closing = _party_ledger(party)
    company = (Company.all_objects.filter(organization=party.organization, is_active=True).first()
               or Company.all_objects.filter(organization=party.organization).first())
    ctx = {"party": party, "rows": rows, "closing": closing,
           "closing_type": "To Receive (Dr)" if closing >= 0 else "To Pay (Cr)",
           "company": company}

    if request.GET.get("format") == "pdf":
        try:
            from xhtml2pdf import pisa
        except ImportError:
            return HttpResponse("PDF engine not available", status=500)
        html = render_to_string("statement.html", ctx)
        buf = BytesIO()
        pisa.CreatePDF(src=html, dest=buf)
        buf.seek(0)
        resp = HttpResponse(buf.read(), content_type="application/pdf")
        resp["Content-Disposition"] = f'attachment; filename="statement-{party.name}.pdf"'
        return resp
    return render(request, "statement.html", ctx)
