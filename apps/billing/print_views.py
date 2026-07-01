import uuid
from io import BytesIO
from django.http import HttpResponse, Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string

from apps.core.models import Company
from apps.tenants.tenancy import get_current_org
from .models import Voucher
from .utils import amount_in_words


def _forbidden_if_no_org():
    """Invoice sirf token/session waale us hi organization ko dikhe — cross-tenant block."""
    return get_current_org() is None


def _get_voucher(request, pk):
    """Voucher laata hai — ya to org-scoped (login), ya public share link (?share=uuid).
    Public link customer ko WhatsApp pe bhej sakte hain, bina token leak kiye.
    """
    share = request.GET.get("share")
    if share:
        try:
            uuid.UUID(str(share))
        except (ValueError, TypeError):
            return None
        return Voucher.all_objects.filter(pk=pk, share_uuid=share).first()
    if _forbidden_if_no_org():
        return None
    return get_object_or_404(Voucher, pk=pk)


def _upi_qr_data_uri(upi_id, name, amount):
    """UPI payment QR (upi://pay...) ko base64 PNG data-URI banata hai — invoice par print hota hai."""
    if not upi_id:
        return None
    try:
        import base64, qrcode
        s = f"upi://pay?pa={upi_id}&pn={name or 'Merchant'}&am={amount}&cu=INR"
        img = qrcode.make(s)
        b = BytesIO()
        img.save(b, format="PNG")
        return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()
    except Exception:
        return None


def _bank_for(voucher):
    """Invoice par dikhane ke liye org ka pehla active bank account."""
    try:
        from apps.cashbank.models import BankAccount
        return BankAccount.all_objects.filter(
            organization_id=voucher.organization_id, account_type="BANK", is_active=True
        ).first()
    except Exception:
        return None


def _context(voucher):
    company = Company.objects.filter(is_active=True).first()
    if voucher.voucher_type == "SALE":
        title = "TAX INVOICE" if (company and company.charges_gst) else "BILL OF SUPPLY"
    else:
        title = voucher.get_voucher_type_display().upper()
    bank = _bank_for(voucher)
    upi_id = (bank.upi_id if bank else "") or ""
    payee = (company.name if company else "") or (bank.name if bank else "")
    return {
        "v": voucher,
        "company": company,
        "lines": voucher.lines.select_related("variant", "variant__item", "unit").all(),
        "title": title,
        "amount_words": amount_in_words(voucher.grand_total),
        "is_igst": voucher.igst and voucher.igst > 0,
        "bank": bank,
        "upi_qr": _upi_qr_data_uri(upi_id, payee, voucher.grand_total),
    }


def invoice_html(request, pk):
    """Print-ready invoice. Login (org) ya public ?share=<uuid> se accessible."""
    voucher = _get_voucher(request, pk)
    if voucher is None:
        return HttpResponseForbidden("Login required ya galat share link.")
    return render(request, "invoice.html", _context(voucher))


def invoice_pdf(request, pk):
    """Direct PDF download. Login (org) ya public ?share=<uuid> se accessible."""
    voucher = _get_voucher(request, pk)
    if voucher is None:
        return HttpResponseForbidden("Login required ya galat share link.")
    try:
        from xhtml2pdf import pisa
    except ImportError:
        raise Http404("xhtml2pdf not installed (pip install xhtml2pdf)")
    html = render_to_string("invoice.html", _context(voucher))
    buf = BytesIO()
    pisa.CreatePDF(src=html, dest=buf)
    buf.seek(0)
    resp = HttpResponse(buf.read(), content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="{voucher.number.replace("/", "-")}.pdf"'
    return resp
