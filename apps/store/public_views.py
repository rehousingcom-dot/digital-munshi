"""Public store — order place (cart se) + order tracking. Login nahi."""
import json
from decimal import Decimal
from django.http import JsonResponse, Http404
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from .models import Order, OrderItem, money


@csrf_exempt
def api_place_order(request, catalog_uuid):
    if request.method != "POST":
        return JsonResponse({"detail": "POST only"}, status=405)
    from apps.tenants.models import Organization
    org = Organization.objects.filter(catalog_uuid=catalog_uuid).first()
    if not org or not org.catalog_enabled:
        return JsonResponse({"detail": "Store not found"}, status=404)
    try:
        data = json.loads(request.body or "{}")
    except Exception:
        return JsonResponse({"detail": "bad data"}, status=400)
    name = (data.get("name") or "").strip()
    items = data.get("items") or []
    if not name:
        return JsonResponse({"detail": "Naam daalo"}, status=400)
    if not items:
        return JsonResponse({"detail": "Cart khaali hai"}, status=400)

    order = Order.all_objects.create(
        organization=org, customer_name=name,
        customer_phone=(data.get("phone") or "").strip(),
        customer_address=(data.get("address") or "").strip(),
        note=(data.get("note") or "").strip())
    for it in items[:100]:
        try:
            qty = Decimal(str(it.get("qty") or 1))
            if qty <= 0:
                continue
            OrderItem.all_objects.create(
                organization=org, order=order,
                variant_id=it.get("variant") or None,
                name=(it.get("name") or "Item")[:200],
                price=money(it.get("price") or 0), qty=qty)
        except Exception:
            continue
    order.recompute()
    # Growth: lead bhi bana do
    try:
        from apps.tenants.models import Lead
        Lead.objects.create(name=name, phone=(data.get("phone") or "").strip(),
                            business=org.name, source="store-order",
                            message=f"Online order {order.order_no} — Rs {order.total}")
    except Exception:
        pass
    return JsonResponse({"ok": True, "order_no": order.order_no, "token": str(order.token),
                         "total": str(order.total)})


def order_track(request, token):
    order = Order.all_objects.filter(token=token).prefetch_related("items").select_related("organization").first()
    if not order:
        raise Http404("Order not found")
    steps = ["NEW", "CONFIRMED", "PACKED", "DELIVERED"]
    cur = order.status
    idx = steps.index(cur) if cur in steps else -1
    ctx = {"order": order, "items": order.items.all(), "shop": order.organization.name,
           "steps": steps, "cur_idx": idx, "cancelled": cur == "CANCELLED"}
    return render(request, "order_track.html", ctx)
