"""Public (no-login) committee pages — online boli + join request.
Committee ko uske public_uuid se resolve karte hain (tenant token ke bina)."""
import json
from io import BytesIO
from django.http import JsonResponse, HttpResponse, Http404, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string

from apps.tenants.tenancy import get_current_org
from .models import Committee, CommitteeMember, CommitteeBid, CommitteeJoinRequest, money


def _get_committee(public_uuid):
    return Committee.all_objects.filter(public_uuid=public_uuid).first()


def committee_public(request, public_uuid):
    """Online boli + join page (public) — results, live bids, history sabko dikhe."""
    c = _get_committee(public_uuid)
    if not c:
        raise Http404("Committee not found")
    members = list(c.members.all().values("id", "name"))
    # Completed rounds (history) — sabke liye transparent
    done = []
    for r in c.rounds.filter(winner__isnull=False).order_by("month_no"):
        done.append({
            "month_no": r.month_no, "winner": r.winner.name if r.winner else "—",
            "bid": money(r.bid_amount), "net_payable": money(r.net_payable),
            "per_head": money(r.per_head),
        })
    # Live bids (jab boli khuli ho)
    live = []
    if c.bidding_open and c.open_month:
        for b in c.bids.filter(month_no=c.open_month).select_related("member").order_by("-bid_amount"):
            live.append({"name": b.member.name, "bid": money(b.bid_amount)})
    ctx = {
        "c": c, "members": members,
        "per_head_base": money(c.monthly_base),
        "coupon_total": money(c.coupon_total),
        "done": done, "live": live,
        "months_left": max(0, (c.members_count or 0) - len(done)),
    }
    return render(request, "committee_public.html", ctx)


@csrf_exempt
def api_public_bid(request, public_uuid):
    """Member apni boli daalta hai. body: {member, bid_amount}"""
    if request.method != "POST":
        return JsonResponse({"detail": "POST only"}, status=405)
    c = _get_committee(public_uuid)
    if not c or not c.bidding_open or not c.open_month:
        return JsonResponse({"detail": "Boli abhi band hai"}, status=400)
    try:
        data = json.loads(request.body or "{}")
    except Exception:
        data = request.POST
    mid = data.get("member")
    amt = data.get("bid_amount")
    m = CommitteeMember.all_objects.filter(committee=c, id=mid).first()
    if not m:
        return JsonResponse({"detail": "Member select karo"}, status=400)
    if not amt:
        return JsonResponse({"detail": "Boli amount daalo"}, status=400)
    bid, _ = CommitteeBid.all_objects.update_or_create(
        committee=c, month_no=c.open_month, member=m,
        defaults={"bid_amount": money(amt), "organization": c.organization})
    return JsonResponse({"ok": True, "member": m.name, "bid": str(money(amt)),
                         "month": c.open_month})


@csrf_exempt
def api_public_join(request, public_uuid):
    """Naya member join request. body: {name, phone, message}"""
    if request.method != "POST":
        return JsonResponse({"detail": "POST only"}, status=405)
    c = _get_committee(public_uuid)
    if not c or not c.allow_join:
        return JsonResponse({"detail": "Join abhi band hai"}, status=400)
    try:
        data = json.loads(request.body or "{}")
    except Exception:
        data = request.POST
    name = (data.get("name") or "").strip()
    if not name:
        return JsonResponse({"detail": "Naam daalo"}, status=400)
    CommitteeJoinRequest.all_objects.create(
        committee=c, name=name, phone=(data.get("phone") or "").strip(),
        message=(data.get("message") or "").strip(), organization=c.organization)
    # Growth: platform lead bhi bana do
    try:
        from apps.tenants.models import Lead
        Lead.objects.create(name=name, phone=(data.get("phone") or "").strip(),
                            business=c.name, source="committee-join",
                            message=f"Committee '{c.name}' join request")
    except Exception:
        pass
    return JsonResponse({"ok": True})


# ---- Member statement (token-protected, like payslip) ----
def _member_or_403(pk):
    if get_current_org() is None:
        return None
    return CommitteeMember.objects.filter(pk=pk).select_related("committee").first()


def member_statement_html(request, pk):
    if get_current_org() is None:
        return HttpResponseForbidden("Login required (token missing).")
    from .views import member_statement_data
    m = get_object_or_404(CommitteeMember, pk=pk)
    return render(request, "committee_statement.html", member_statement_data(m))


def member_statement_pdf(request, pk):
    if get_current_org() is None:
        return HttpResponseForbidden("Login required (token missing).")
    try:
        from xhtml2pdf import pisa
    except ImportError:
        raise Http404("xhtml2pdf not installed")
    from .views import member_statement_data
    m = get_object_or_404(CommitteeMember, pk=pk)
    html = render_to_string("committee_statement.html", member_statement_data(m))
    buf = BytesIO()
    pisa.CreatePDF(src=html, dest=buf)
    buf.seek(0)
    resp = HttpResponse(buf.read(), content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="committee_{m.name}_statement.pdf"'
    return resp
