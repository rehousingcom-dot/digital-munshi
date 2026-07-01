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
                      "type": it.item_type, "code": (v.item_code if v else ""),
                      "variant": (v.id if v else "")})

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
        return JsonResponse({"error": "Enter a valid name and phone number"}, status=400)
    lead = Lead.objects.create(
        name=name[:120], phone=phone[:20],
        business=(request.POST.get("business") or "")[:160],
        message=(request.POST.get("message") or "")[:1000],
        source=(request.POST.get("source") or "")[:120],
    )
    _notify_lead_email(lead)
    return JsonResponse({"ok": True, "message": "Thank you! We will contact you soon."})


_L_EN = {"cta1": "Get started free →", "cta2": "Book a demo", "why": "Why choose Digital Munshi?",
         "faq": "Frequently Asked Questions (FAQ)", "explore": "Explore more", "bycity": "By city:",
         "readmore": "Read more", "trydm": "Try Digital Munshi — free",
         "trydesc": "Billing, GST, inventory, accounting — in one app. 7-day free trial.",
         "startfree": "Start free →", "features": "Features", "read": "Read →",
         "blogsub": "GST, billing and business tips — in simple language."}
_L_HI = {"cta1": "Free me shuru karo →", "cta2": "Demo book karo", "why": "Digital Munshi kyun choose karein?",
         "faq": "Aksar poochhe jaane wale sawaal (FAQ)", "explore": "Aur dekho", "bycity": "City me:",
         "readmore": "Aur padho", "trydm": "Digital Munshi try karo — free",
         "trydesc": "Billing, GST, inventory, accounting — ek app me. 7 din free trial.",
         "startfree": "Free shuru karo →", "features": "Features", "read": "Padho →",
         "blogsub": "GST, billing aur business tips — aasan bhasha me."}


def _mods(lang):
    if lang == "hi":
        from . import marketing_hi as m
        return m, _L_HI, "hi", "/hi"
    from . import marketing as m
    return m, _L_EN, "en", ""


def _keyword_page(request, slug, lang):
    from django.shortcuts import render
    from django.http import HttpResponseNotFound
    m, L, lc, pre = _mods(lang)
    page = m.KEYWORD_PAGES.get(slug)
    if not page:
        return HttpResponseNotFound("Page not found")
    other = [(s, kp["h1"]) for s, kp in m.KEYWORD_PAGES.items() if s != slug]
    cities = list(m.CITIES.items())
    alt = ("/software/%s/" % slug) if lang == "hi" else ("/hi/software/%s/" % slug)
    return render(request, "keyword_page.html",
                  {"p": page, "slug": slug, "other": other, "why": m._WHY,
                   "cities": cities, "L": L, "lang": lc, "pre": pre, "alt": alt})


def keyword_page(request, slug):
    return _keyword_page(request, slug, "en")


def keyword_page_hi(request, slug):
    return _keyword_page(request, slug, "hi")


def _city_page(request, slug, lang):
    from django.shortcuts import render
    from django.http import HttpResponseNotFound
    m, L, lc, pre = _mods(lang)
    data = m.city_page_data(slug)
    if not data:
        return HttpResponseNotFound("City page not found")
    software = [(s, kp["h1"]) for s, kp in m.KEYWORD_PAGES.items()]
    alt = ("/billing-software-in-%s/" % slug) if lang == "hi" else ("/hi/billing-software-in-%s/" % slug)
    return render(request, "city_page.html",
                  {"c": data, "software": software, "L": L, "lang": lc, "pre": pre, "alt": alt})


def city_page(request, slug):
    return _city_page(request, slug, "en")


def city_page_hi(request, slug):
    return _city_page(request, slug, "hi")


def _blog_index(request, lang):
    from django.shortcuts import render
    m, L, lc, pre = _mods(lang)
    posts = [(s, p["title"], p["desc"]) for s, p in m.BLOG_POSTS.items()]
    alt = "/blog/" if lang == "hi" else "/hi/blog/"
    return render(request, "blog_index.html", {"posts": posts, "L": L, "lang": lc, "pre": pre, "alt": alt})


def blog_index(request):
    return _blog_index(request, "en")


def blog_index_hi(request):
    return _blog_index(request, "hi")


def _blog_post(request, slug, lang):
    from django.shortcuts import render
    from django.http import HttpResponseNotFound
    m, L, lc, pre = _mods(lang)
    post = m.BLOG_POSTS.get(slug)
    if not post:
        return HttpResponseNotFound("Post not found")
    other = [(s, p["title"]) for s, p in m.BLOG_POSTS.items() if s != slug]
    return render(request, "blog_post.html",
                  {"post": post, "slug": slug, "other": other, "L": L, "lang": lc, "pre": pre})


def blog_post(request, slug):
    return _blog_post(request, slug, "en")


def blog_post_hi(request, slug):
    return _blog_post(request, slug, "hi")


def _comparison(request, slug, lang):
    from django.shortcuts import render
    from django.http import HttpResponseNotFound
    m, L, lc, pre = _mods(lang)
    comps = getattr(m, "COMPARISONS", None)
    from . import marketing as EN
    comps = EN.COMPARISONS  # comparisons English-only for now
    c = comps.get(slug)
    if not c:
        return HttpResponseNotFound("Not found")
    other = [(s, cc["h1"]) for s, cc in comps.items() if s != slug]
    return render(request, "comparison_page.html", {"c": c, "slug": slug, "other": other})


def comparison_page(request, slug):
    return _comparison(request, slug, "en")


def tools_index(request):
    from django.shortcuts import render
    return render(request, "tools_index.html", {})


def tool_gst_calculator(request):
    from django.shortcuts import render
    return render(request, "tool_gst_calculator.html", {})


def tool_invoice_generator(request):
    from django.shortcuts import render
    return render(request, "tool_invoice_generator.html", {})


def tool_hsn_finder(request):
    from django.shortcuts import render
    return render(request, "tool_hsn_finder.html", {})


def _tool(request, tmpl):
    from django.shortcuts import render
    return render(request, tmpl, {})


def tool_emi(request):
    return _tool(request, "tool_emi.html")


def tool_discount(request):
    return _tool(request, "tool_discount.html")


def tool_margin(request):
    return _tool(request, "tool_margin.html")


def tool_words(request):
    return _tool(request, "tool_words.html")


def tool_barcode(request):
    return _tool(request, "tool_barcode.html")


def tool_upi_qr(request):
    return _tool(request, "tool_upi_qr.html")


def tool_chit(request):
    return _tool(request, "tool_chit.html")
