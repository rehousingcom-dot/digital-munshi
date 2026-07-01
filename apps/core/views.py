from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.tenants.tenancy import OrgScopedQuerysetMixin
from apps.accounts.permissions import RolePermission
from .models import Company, Setting, Unit, TaxRate, Godown
from .business_presets import BUSINESS_TYPES
from .serializers import (
    CompanySerializer, SettingSerializer, UnitSerializer,
    TaxRateSerializer, GodownSerializer,
)


@api_view(["GET", "PUT"])
@permission_classes([IsAuthenticated, RolePermission])
def business_profile(request):
    """Current business ka profile + settings. GET dekhne ke liye, PUT update.
    Agar business_type badla -> uske presets apply ho jaate hain.
    """
    company = Company.objects.filter(is_active=True).first()
    if not company:
        company = Company.objects.create(name=getattr(request.user.organization, "name", "My Business"))
    if request.method == "PUT":
        data = request.data
        new_type = data.get("business_type")
        if new_type and new_type != company.business_type:
            company.apply_business_type(new_type)  # presets reset
        # Editable fields
        editable = [
            "name", "legal_name", "gstin", "address", "phone", "email", "state", "state_code",
            "gst_scheme", "invoice_prefix", "terms",
            # item settings
            "sell_type", "enable_stock_maintenance", "enable_manufacturing",
            "show_low_stock_dialog", "enable_item_category", "enable_default_unit",
            "party_wise_rate", "enable_description", "item_wise_tax", "item_wise_discount",
            "update_sale_price_from_transaction", "quantity_decimals", "enable_wholesale_price",
            "enable_mrp", "calculate_tax_on_mrp",
            "enable_batch", "enable_exp_date", "enable_mfg_date", "enable_model_no", "enable_size",
            "enable_godown", "enable_barcode", "enable_serial", "default_price_inclusive",
            "negative_stock_allowed", "default_item_type",
            # whatsapp
            "whatsapp_enabled", "whatsapp_business_number", "whatsapp_api_token",
            "whatsapp_phone_id",
        ]
        for f in editable:
            if f in data:
                setattr(company, f, data[f])
        company.save()
    data = CompanySerializer(company).data
    data["business_type_choices"] = [{"code": c, "label": l} for c, l in BUSINESS_TYPES]
    return Response(data)


@api_view(["POST"])
@permission_classes([IsAuthenticated, RolePermission])
def upload_logo(request):
    """Invoice logo upload (multipart 'logo' field)."""
    company = Company.objects.filter(is_active=True).first()
    if not company:
        return Response({"detail": "company not found"}, status=404)
    f = request.FILES.get("logo")
    if not f:
        return Response({"detail": "'logo' file bhejein"}, status=400)
    company.logo = f
    company.save()
    return Response({"status": "ok", "logo": company.logo.url if company.logo else None})


@api_view(["POST"])
@permission_classes([IsAuthenticated, RolePermission])
def upload_signature(request):
    """Authorised signatory image upload (multipart 'signature' field) — invoice par print."""
    company = Company.objects.filter(is_active=True).first()
    if not company:
        return Response({"detail": "company not found"}, status=404)
    f = request.FILES.get("signature")
    if not f:
        return Response({"detail": "'signature' file bhejein"}, status=400)
    company.signature = f
    company.save()
    return Response({"status": "ok", "signature": company.signature.url if company.signature else None})


class CompanyViewSet(OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer


class SettingViewSet(OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Setting.objects.all()
    serializer_class = SettingSerializer


class UnitViewSet(OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Unit.objects.all()
    serializer_class = UnitSerializer


class TaxRateViewSet(OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = TaxRate.objects.all()
    serializer_class = TaxRateSerializer


class GodownViewSet(OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Godown.objects.all()
    serializer_class = GodownSerializer


def catalog_shop(request, catalog_uuid):
    """Public online catalog — login ke bina. Customer products dekh ke
    WhatsApp pe order bhej sakta hai (dukaan ke number pe)."""
    from django.shortcuts import render
    from django.http import HttpResponse
    from apps.tenants.models import Organization
    from apps.core.models import Company
    from apps.inventory.models import Item, ItemUnitPrice

    org = Organization.objects.filter(catalog_uuid=catalog_uuid).first()
    if not org or not org.catalog_enabled:
        return HttpResponse("Catalog not found or disabled", status=404)

    company = (Company.all_objects.filter(organization=org, is_active=True).first()
               or Company.all_objects.filter(organization=org).first())

    items = []
    for it in (Item.all_objects.filter(organization=org)
               .prefetch_related("variants", "variants__unit_prices")):
        v = it.variants.all().first()
        price = float(it.mrp or 0)
        if v:
            up = None
            for x in v.unit_prices.all():
                if it.primary_unit_id and x.unit_id == it.primary_unit_id:
                    up = x
                    break
            if up and up.sale_price:
                price = float(up.sale_price)
        img = ""
        try:
            if it.image:
                img = it.image.url
        except Exception:
            img = ""
        items.append({"name": it.name, "price": price, "img": img,
                      "type": it.item_type, "code": (v.item_code if v else "")})

    wa = ""
    if company:
        raw = (company.whatsapp_business_number or company.phone or "").strip()
        digits = "".join(c for c in raw if c.isdigit())
        if len(digits) == 10:
            digits = "91" + digits
        wa = digits

    logo = ""
    try:
        if company and company.logo:
            logo = company.logo.url
    except Exception:
        logo = ""

    ctx = {
        "shop_name": (company.name if company else org.name),
        "shop_phone": (company.phone if company else ""),
        "shop_address": (company.address if company else ""),
        "wa": wa, "logo": logo, "items": items, "catalog_uuid": str(catalog_uuid),
    }
    return render(request, "catalog.html", ctx)


def landing(request):
    """Public marketing landing page (SEO) — pricing plans ke saath. Signup ke liye
    app pe le jaata hai. Search engines ke liye server-rendered."""
    from django.shortcuts import render
    from apps.tenants.models import Plan
    plans = list(Plan.objects.filter(is_active=True).order_by("sort_order", "price_monthly"))
    return render(request, "landing.html", {"plans": plans})


def _notify_lead_email(lead):
    """Naya lead aane par owner ko email (Resend)."""
    from django.conf import settings
    key = getattr(settings, "RESEND_API_KEY", "")
    to = getattr(settings, "LEADS_EMAIL", "") or getattr(settings, "BACKUP_EMAIL", "")
    if not key or not to:
        return
    try:
        import requests
        requests.post("https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"from": getattr(settings, "RESEND_FROM", "onboarding@resend.dev"), "to": [to],
                  "subject": f"🔔 Naya Lead: {lead.name} ({lead.phone})",
                  "text": f"Naam: {lead.name}\nPhone: {lead.phone}\nBusiness: {lead.business}\n"
                          f"Message: {lead.message}\nPage: {lead.source}\n\nWhatsApp: https://wa.me/91{lead.phone[-10:]}"},
            timeout=10)
    except Exception:
        pass


from django.views.decorators.csrf import csrf_exempt as _csrf_exempt


@_csrf_exempt
def lead_create(request):
    """Public lead form submit (marketing pages se). Save + owner ko email notify."""
    from django.http import JsonResponse
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)
    from apps.tenants.models import Lead
    name = (request.POST.get("name") or "").strip()
    phone = (request.POST.get("phone") or "").strip()
    if not name or len(phone) < 8:
        return JsonResponse({"error": "Naam aur sahi phone number daalo"}, status=400)
    lead = Lead.objects.create(
        name=name[:120], phone=phone[:20],
        business=(request.POST.get("business") or "")[:160],
        message=(request.POST.get("message") or "")[:1000],
        source=(request.POST.get("source") or "")[:120],
    )
    _notify_lead_email(lead)
    return JsonResponse({"ok": True, "message": "Dhanyavaad! Hum jaldi contact karenge."})


def keyword_page(request, slug):
    from django.shortcuts import render
    from django.http import HttpResponseNotFound
    from .marketing import KEYWORD_PAGES, _WHY, CITIES
    page = KEYWORD_PAGES.get(slug)
    if not page:
        return HttpResponseNotFound("Page not found")
    other = [(s, kp["h1"]) for s, kp in KEYWORD_PAGES.items() if s != slug]
    cities = list(CITIES.items())
    return render(request, "keyword_page.html",
                  {"p": page, "slug": slug, "other": other, "why": _WHY, "cities": cities})


def city_page(request, slug):
    from django.shortcuts import render
    from django.http import HttpResponseNotFound
    from .marketing import city_page_data, KEYWORD_PAGES
    data = city_page_data(slug)
    if not data:
        return HttpResponseNotFound("City page not found")
    software = [(s, kp["h1"]) for s, kp in KEYWORD_PAGES.items()]
    return render(request, "city_page.html", {"c": data, "software": software})


def blog_index(request):
    from django.shortcuts import render
    from .marketing import BLOG_POSTS
    posts = [(s, p["title"], p["desc"]) for s, p in BLOG_POSTS.items()]
    return render(request, "blog_index.html", {"posts": posts})


def blog_post(request, slug):
    from django.shortcuts import render
    from django.http import HttpResponseNotFound
    from .marketing import BLOG_POSTS
    post = BLOG_POSTS.get(slug)
    if not post:
        return HttpResponseNotFound("Post not found")
    other = [(s, p["title"]) for s, p in BLOG_POSTS.items() if s != slug]
    return render(request, "blog_post.html", {"post": post, "slug": slug, "other": other})
