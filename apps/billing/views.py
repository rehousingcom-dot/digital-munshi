import re
from urllib.parse import quote
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.tenants.tenancy import OrgScopedQuerysetMixin
from apps.core.models import Company
from .models import Voucher, RecurringInvoice
from .serializers import VoucherSerializer, RecurringInvoiceSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes


class RecurringInvoiceViewSet(OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = RecurringInvoice.objects.all().select_related("source_voucher", "source_voucher__party")
    serializer_class = RecurringInvoiceSerializer

    @action(detail=True, methods=["post"])
    def generate_now(self, request, pk=None):
        """Abhi ek invoice generate karo (next_run advance)."""
        ri = self.get_object()
        v = ri.generate_one()
        return Response({"status": "generated", "number": v.number,
                         "grand_total": str(v.grand_total), "next_run": str(ri.next_run)})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def run_due_recurring(request):
    """Saare due recurring invoices generate karo (scheduled task se call hoga)."""
    done = []
    for ri in RecurringInvoice.objects.filter(is_active=True):
        if ri.due():
            try:
                v = ri.generate_one()
                done.append({"name": ri.name, "number": v.number})
            except Exception:
                pass
    return Response({"generated": len(done), "invoices": done})


class VoucherViewSet(OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Voucher.objects.all().prefetch_related("lines")
    serializer_class = VoucherSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        vtype = self.request.query_params.get("type")
        if vtype:
            qs = qs.filter(voucher_type=vtype.upper())
        return qs

    def update(self, request, *args, **kwargs):
        """Posted voucher edit allow nahi — stock galat ho jaata. Pehle return/cancel karein."""
        obj = self.get_object()
        if obj.is_posted:
            return Response(
                {"detail": "Yeh voucher post (stock-updated) ho chuka hai, edit nahi ho sakta."},
                status=400)
        return super().update(request, *args, **kwargs)

    @action(detail=True, methods=["post"])
    def post_to_stock(self, request, pk=None):
        """Voucher ko stock mein post karta hai (quantity update)."""
        voucher = self.get_object()
        try:
            voucher.post()
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)
        return Response({"status": "posted", "is_posted": voucher.is_posted,
                         "grand_total": str(voucher.grand_total)})

    @action(detail=True, methods=["post"])
    def convert(self, request, pk=None):
        """Estimate/Challan ko Sale Invoice mein convert karta hai."""
        voucher = self.get_object()
        new_type = (request.data.get("to") or "SALE").upper()
        returns = request.data.get("returns") or {}
        try:
            new_v = voucher.convert_to(new_type, returns=returns)
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)
        return Response({"status": "converted", "new_id": new_v.id,
                         "number": new_v.number, "grand_total": str(new_v.grand_total)})

    @action(detail=True, methods=["get"])
    def einvoice_json(self, request, pk=None):
        """E-Invoice (IRN) government-schema JSON — GSP/portal pe upload ready."""
        from .einvoice import einvoice_json
        v = self.get_object()
        company = Company.objects.filter(is_active=True).first()
        return Response(einvoice_json(v, company))

    @action(detail=True, methods=["get"])
    def eway_json(self, request, pk=None):
        """E-Way Bill government-schema JSON."""
        from .einvoice import eway_json
        v = self.get_object()
        company = Company.objects.filter(is_active=True).first()
        transport = {
            "transporter_id": request.query_params.get("transporter_id", ""),
            "vehicle_no": request.query_params.get("vehicle_no", ""),
            "distance": request.query_params.get("distance", ""),
        }
        return Response(eway_json(v, company, transport))

    @action(detail=True, methods=["post"])
    def email(self, request, pk=None):
        """Invoice email se bhejo (party email pe). SMTP configured ho to actually send."""
        from django.core.mail import send_mail
        from django.conf import settings
        v = self.get_object()
        to = (request.data.get("to") or v.party.email or "").strip()
        if not to:
            return Response({"detail": "Party ka email nahi hai"}, status=400)
        company = Company.objects.filter(is_active=True).first()
        biz = company.name if company else "Digital Munshi"
        public_url = request.build_absolute_uri(f"/invoice/{v.id}/?share={v.share_uuid}")
        subject = f"{biz} — {v.get_voucher_type_display()} {v.number}"
        body = (f"Namaste {v.party.name},\n\nAapka {v.get_voucher_type_display()} {v.number} "
                f"taiyaar hai.\nAmount: Rs. {v.grand_total}\n\nDekhein: {public_url}\n\nDhanyavaad,\n{biz}")
        sent = False
        try:
            send_mail(subject, body, getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@digitalmunshi.in"),
                      [to], fail_silently=True)
            sent = True
        except Exception:
            sent = False
        return Response({"to": to, "sent": sent, "subject": subject,
                         "note": "Dev mode: console backend. Production me SMTP set karein."})

    @action(detail=True, methods=["get"])
    def share_link(self, request, pk=None):
        """Public invoice link + WhatsApp share link (wa.me) — document seedha
        client ko WhatsApp pe bhejne ke liye. Token leak nahi hota (share_uuid se).
        """
        v = self.get_object()
        public_url = request.build_absolute_uri(f"/invoice/{v.id}/?share={v.share_uuid}")
        pdf_url = request.build_absolute_uri(f"/invoice/{v.id}/pdf/?share={v.share_uuid}")
        company = Company.objects.filter(is_active=True).first()
        biz = company.name if company else "Hamari dukaan"
        doc = v.get_voucher_type_display()
        msg = (f"Namaste {v.party.name},\n{biz} se aapka {doc} *{v.number}* "
               f"taiyaar hai.\nAmount: Rs. {v.grand_total}\nDekhein: {public_url}")
        # Customer ka WhatsApp number (digits only). Khaali ho to wa.me bina number.
        digits = re.sub(r"\D", "", v.party.phone or "")
        if digits and len(digits) == 10:
            digits = "91" + digits  # default India country code
        wa = f"https://wa.me/{digits}?text={quote(msg)}" if digits else f"https://wa.me/?text={quote(msg)}"
        # Agar Cloud API token set ho to auto-send try kare (groundwork)
        from apps.tenants.whatsapp_gateway import send_document
        api_result = send_document(company, digits, msg)
        return Response({
            "public_url": public_url, "pdf_url": pdf_url,
            "whatsapp_url": wa, "to": v.party.name, "phone": v.party.phone,
            "auto_send": api_result,
        })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def transactions_export(request):
    """All transactions (invoices/vouchers) CSV export — data backup."""
    import csv
    from django.http import HttpResponse
    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = 'attachment; filename="transactions.csv"'
    w = csv.writer(resp)
    w.writerow(["date", "type", "number", "party", "taxable_value", "cgst", "sgst",
                "igst", "cess", "total_tax", "round_off", "grand_total", "notes"])
    qs = Voucher.objects.select_related("party").all()
    vt = request.GET.get("type")
    if vt:
        qs = qs.filter(voucher_type=vt)
    for v in qs:
        w.writerow([v.date, v.get_voucher_type_display(), v.number,
                    v.party.name if v.party_id else "", v.taxable_value, v.cgst, v.sgst,
                    v.igst, v.cess, v.total_tax, v.round_off, v.grand_total,
                    (v.notes or "").replace("\n", " ")])
    return resp
