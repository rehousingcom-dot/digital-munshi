"""WhatsApp marketing broadcast — customers ko offers/festival messages.
Cloud API configured ho to auto-send; warna har customer ka wa.me link deta hai
(dukaandar ek-ek tap karke bheje). {name} placeholder personalize hota hai.
"""
from urllib.parse import quote
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def broadcast(request):
    from apps.party.models import Party
    from apps.core.models import Company
    text = (request.data.get("message") or "").strip()
    if not text:
        return Response({"detail": "Message likho"}, status=400)
    ids = request.data.get("party_ids")  # list ya None => sab customers
    auto = bool(request.data.get("auto"))  # cloud API se auto-send karna hai?

    qs = Party.objects.filter(party_type__in=["CUSTOMER", "BOTH"]).exclude(phone="")
    if ids:
        qs = qs.filter(id__in=ids)

    company = Company.objects.filter(is_active=True).first()
    token = getattr(company, "whatsapp_api_token", "") if company else ""
    phone_id = getattr(company, "whatsapp_phone_id", "") if company else ""
    cloud = bool(token and phone_id)

    out, sent = [], 0
    for p in qs[:500]:
        msg = text.replace("{name}", p.name).replace("{naam}", p.name)
        digits = "".join(c for c in (p.phone or "") if c.isdigit())
        to = ("91" + digits[-10:]) if len(digits) >= 10 else digits
        wa = f"https://wa.me/{to}?text={quote(msg)}" if to else ""
        s = False
        if auto and cloud and to:
            try:
                from apps.tenants.whatsapp_gateway import send_via_cloud_api
                send_via_cloud_api(token, phone_id, to, msg)
                s = True
                sent += 1
            except Exception:
                s = False
        out.append({"id": p.id, "name": p.name, "phone": p.phone, "wa_url": wa, "sent": s})
    return Response({"cloud": cloud, "auto": auto, "sent": sent,
                     "count": len(out), "recipients": out})
