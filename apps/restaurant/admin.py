from django.contrib import admin
from .models import Table, RestOrder, RestOrderItem


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ("name", "seats", "area", "is_active")


class RestOrderItemInline(admin.TabularInline):
    model = RestOrderItem
    extra = 0


@admin.register(RestOrder)
class RestOrderAdmin(admin.ModelAdmin):
    list_display = ("order_no", "table", "status", "total", "created_at")
    list_filter = ("status",)
    inlines = [RestOrderItemInline]
