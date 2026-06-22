from django.contrib import admin
from .models import Company, Setting, Unit, TaxRate, Godown


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "gstin", "state", "phone", "is_active")
    search_fields = ("name", "legal_name", "gstin")


@admin.register(Setting)
class SettingAdmin(admin.ModelAdmin):
    list_display = ("key", "label", "group")
    list_filter = ("group",)
    search_fields = ("key", "label")


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ("short_code", "name", "allow_decimal")
    search_fields = ("name", "short_code")


@admin.register(TaxRate)
class TaxRateAdmin(admin.ModelAdmin):
    list_display = ("name", "percent", "is_active")


@admin.register(Godown)
class GodownAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    search_fields = ("name",)
