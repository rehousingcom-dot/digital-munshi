from rest_framework import serializers
from .models import SupplierProfile, SupplierEnquiry, CATEGORIES


class SupplierProfileSerializer(serializers.ModelSerializer):
    name = serializers.CharField(read_only=True)
    org_name = serializers.CharField(source="organization.name", read_only=True)
    category_label = serializers.SerializerMethodField()
    catalog_uuid = serializers.SerializerMethodField()
    catalog_enabled = serializers.SerializerMethodField()

    class Meta:
        model = SupplierProfile
        fields = ["id", "is_listed", "display_name", "name", "org_name", "category",
                  "category_label", "city", "state", "about", "whatsapp", "min_order",
                  "catalog_uuid", "catalog_enabled"]

    def get_category_label(self, obj):
        return dict(CATEGORIES).get(obj.category, obj.category)

    def get_catalog_uuid(self, obj):
        return str(getattr(obj.organization, "catalog_uuid", "") or "")

    def get_catalog_enabled(self, obj):
        return bool(getattr(obj.organization, "catalog_enabled", False))


class SupplierEnquirySerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)

    class Meta:
        model = SupplierEnquiry
        fields = "__all__"
