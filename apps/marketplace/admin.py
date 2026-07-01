from django.contrib import admin
from .models import SupplierProfile, SupplierEnquiry


@admin.register(SupplierProfile)
class SupplierProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "city", "is_listed", "whatsapp")
    list_filter = ("is_listed", "category")
    search_fields = ("display_name", "organization__name", "city")


@admin.register(SupplierEnquiry)
class SupplierEnquiryAdmin(admin.ModelAdmin):
    list_display = ("from_name", "supplier", "from_phone", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("from_name", "from_phone")
