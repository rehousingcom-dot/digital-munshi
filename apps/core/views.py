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
