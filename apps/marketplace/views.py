from decimal import Decimal, InvalidOperation
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import SupplierProfile, SupplierEnquiry, CATEGORIES
from .serializers import SupplierProfileSerializer, SupplierEnquirySerializer


def _org(request):
    return getattr(request.user, "organization", None)


@api_view(["GET", "PUT"])
@permission_classes([IsAuthenticated])
def profile(request):
    """Meri supplier listing — dekho/edit karo (opt-in)."""
    org = _org(request)
    if not org:
        return Response({"detail": "no org"}, status=400)
    prof, _ = SupplierProfile.objects.get_or_create(
        organization=org, defaults={"display_name": org.name})
    if request.method == "PUT":
        d = request.data
        if "is_listed" in d:
            prof.is_listed = bool(d.get("is_listed"))
        for f in ["display_name", "category", "city", "state", "about", "whatsapp"]:
            if f in d:
                setattr(prof, f, (d.get(f) or ""))
        if "min_order" in d:
            try:
                prof.min_order = Decimal(str(d.get("min_order") or 0))
            except (InvalidOperation, ValueError, TypeError):
                prof.min_order = Decimal("0")
        if not prof.display_name:
            prof.display_name = org.name
        prof.save()
    data = SupplierProfileSerializer(prof).data
    data["categories"] = [{"code": c, "label": l} for c, l in CATEGORIES]
    return Response(data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def suppliers(request):
    """Listed suppliers browse — retailer ke liye. Filters: category, city, q."""
    qs = SupplierProfile.objects.filter(is_listed=True).select_related("organization")
    cat = request.GET.get("category")
    city = request.GET.get("city")
    q = request.GET.get("q")
    if cat:
        qs = qs.filter(category=cat)
    if city:
        qs = qs.filter(city__icontains=city)
    if q:
        from django.db.models import Q
        qs = qs.filter(Q(display_name__icontains=q) | Q(organization__name__icontains=q) |
                       Q(about__icontains=q))
    return Response({
        "count": qs.count(),
        "categories": [{"code": c, "label": l} for c, l in CATEGORIES],
        "suppliers": SupplierProfileSerializer(qs.order_by("-updated_at")[:200], many=True).data,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def enquiries(request):
    """Mujhe (supplier) jo enquiries aayi hain."""
    org = _org(request)
    if not org:
        return Response({"detail": "no org"}, status=400)
    qs = SupplierEnquiry.objects.filter(supplier=org)
    return Response(SupplierEnquirySerializer(qs, many=True).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def enquiry_status(request, pk):
    org = _org(request)
    e = SupplierEnquiry.objects.filter(pk=pk, supplier=org).first()
    if not e:
        return Response({"detail": "not found"}, status=404)
    e.status = (request.data.get("status") or "CONTACTED").upper()
    e.save(update_fields=["status"])
    return Response(SupplierEnquirySerializer(e).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def send_enquiry(request):
    """App ke andar se supplier ko enquiry bhejo. body: {supplier, message}"""
    org = _org(request)
    sup_id = request.data.get("supplier")
    prof = SupplierProfile.objects.filter(organization_id=sup_id, is_listed=True).first()
    if not prof:
        return Response({"detail": "supplier not found"}, status=404)
    SupplierEnquiry.objects.create(
        supplier_id=sup_id, from_org=org,
        from_name=(org.name if org else "A shop"),
        from_phone=request.data.get("phone", ""),
        message=request.data.get("message", ""))
    return Response({"ok": True})
