from io import BytesIO
from django.http import HttpResponse, Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string

from apps.core.models import Company
from apps.tenants.tenancy import get_current_org
from apps.billing.utils import amount_in_words
from .models import SalarySlip


def _ctx(slip):
    company = Company.objects.filter(is_active=True).first()
    return {"s": slip, "emp": slip.employee, "company": company,
            "amount_words": amount_in_words(slip.net_payable)}


def payslip_html(request, pk):
    if get_current_org() is None:
        return HttpResponseForbidden("Login required (token missing).")
    slip = get_object_or_404(SalarySlip, pk=pk)
    return render(request, "payslip.html", _ctx(slip))


def payslip_pdf(request, pk):
    if get_current_org() is None:
        return HttpResponseForbidden("Login required (token missing).")
    try:
        from xhtml2pdf import pisa
    except ImportError:
        raise Http404("xhtml2pdf not installed")
    slip = get_object_or_404(SalarySlip, pk=pk)
    html = render_to_string("payslip.html", _ctx(slip))
    buf = BytesIO()
    pisa.CreatePDF(src=html, dest=buf)
    buf.seek(0)
    resp = HttpResponse(buf.read(), content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="payslip_{slip.employee.code}_{slip.month}_{slip.year}.pdf"'
    return resp
