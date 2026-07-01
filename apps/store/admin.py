from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_no", "customer_name", "customer_phone", "status", "total", "created_at")
    list_filter = ("status",)
    search_fields = ("order_no", "customer_name", "customer_phone")
    inlines = [OrderItemInline]
