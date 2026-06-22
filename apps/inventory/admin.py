from django.contrib import admin
from .models import (
    Category, Item, ItemVariant, ItemUnitPrice, Batch, Stock,
)


class ItemUnitPriceInline(admin.TabularInline):
    model = ItemUnitPrice
    extra = 1


class ItemVariantInline(admin.TabularInline):
    model = ItemVariant
    extra = 1
    readonly_fields = ("item_code", "barcode")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "code")


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "hsn_code", "primary_unit",
                    "secondary_unit", "conversion_factor", "mrp", "is_active")
    list_filter = ("category", "is_active", "tax_rate")
    search_fields = ("name", "hsn_code")
    inlines = [ItemVariantInline]


@admin.register(ItemVariant)
class ItemVariantAdmin(admin.ModelAdmin):
    list_display = ("item", "size", "colour", "model", "item_code", "barcode")
    search_fields = ("item__name", "item_code", "barcode")
    readonly_fields = ("item_code", "barcode")
    inlines = [ItemUnitPriceInline]


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ("variant", "batch_no", "mrp", "discount_type",
                    "discount_value", "expiry_date")
    search_fields = ("batch_no", "variant__item__name")


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ("variant", "godown", "batch", "quantity")
    list_filter = ("godown",)
    search_fields = ("variant__item__name",)
