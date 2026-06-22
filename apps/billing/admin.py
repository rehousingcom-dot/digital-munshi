from django.contrib import admin
from django.utils.html import format_html
from .models import Voucher, VoucherLine


class VoucherLineInline(admin.TabularInline):
    model = VoucherLine
    extra = 1
    fields = ("variant", "unit", "batch", "qty", "rate", "price_inclusive_tax",
              "disc1_pct", "disc2_pct", "disc3_pct", "discount_amount", "tax_percent",
              "taxable_value", "tax_amount", "line_total")
    readonly_fields = ("taxable_value", "tax_amount", "line_total")


@admin.register(Voucher)
class VoucherAdmin(admin.ModelAdmin):
    list_display = ("number", "voucher_type", "date", "party", "godown",
                    "taxable_value", "total_tax", "grand_total", "is_posted")
    list_filter = ("voucher_type", "is_posted", "date")
    search_fields = ("number", "party__name")
    inlines = [VoucherLineInline]
    readonly_fields = ("number", "subtotal", "total_discount", "taxable_value",
                       "cgst", "sgst", "igst", "total_tax", "round_off", "grand_total")
    actions = ["recalc_action", "post_action"]

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        form.instance.recalculate()

    @admin.action(description="Recalculate totals")
    def recalc_action(self, request, queryset):
        for v in queryset:
            v.recalculate()

    @admin.action(description="Post to stock")
    def post_action(self, request, queryset):
        for v in queryset:
            v.post()
