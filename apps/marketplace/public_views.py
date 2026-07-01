"""Public supplier directory (no login) — SEO + lead-gen."""
import json
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from .models import SupplierProfile, SupplierEnquiry, CATEGORIES


def suppliers_directory(request):
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
        qs = qs.filter(Q(display_name__icontains=q) | Q(organization__name__icontains=q))
    suppliers = []
    for p in qs.order_by("-updated_at")[:200]:
        suppliers.append({
            "id": p.organization_id, "name": p.name,
            "category": dict(CATEGORIES).get(p.category, p.category),
            "city": p.city, "state": p.state, "about": p.about,
            "whatsapp": "".join(ch for ch in (p.whatsapp or "") if ch.isdigit()),
            "min_order": p.min_order,
            "catalog": (str(p.organization.catalog_uuid)
                        if getattr(p.organization, "catalog_enabled", False) else ""),
        })
    ctx = {
        "suppliers": suppliers, "count": len(suppliers),
        "categories": [{"code": c, "label": l} for c, l in CATEGORIES],
        "sel_cat": cat or "", "sel_city": city or "", "q": q or "",
    }
    return render(request, "suppliers.html", ctx)


@csrf_exempt
def api_public_enquiry(request, org_id):
    if request.method != "POST":
        return JsonResponse({"detail": "POST only"}, status=405)
    prof = SupplierProfile.objects.filter(organization_id=org_id, is_listed=True).first()
    if not prof:
        return JsonResponse({"detail": "supplier not found"}, status=404)
    try:
        data = json.loads(request.body or "{}")
    except Exception:
        data = request.POST
    name = (data.get("name") or "").strip()
    if not name:
        return JsonResponse({"detail": "Naam daalo"}, status=400)
    SupplierEnquiry.objects.create(
        supplier_id=org_id, from_name=name,
        from_phone=(data.get("phone") or "").strip(),
        message=(data.get("message") or "").strip())
    try:
        from apps.tenants.models import Lead
        Lead.objects.create(name=name, phone=(data.get("phone") or "").strip(),
                            business=prof.name, source="marketplace",
                            message=f"Supplier enquiry → {prof.name}")
    except Exception:
        pass
    return JsonResponse({"ok": True})
