from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("number", "payment_type", "date", "party", "amount", "mode", "reference")
    list_filter = ("payment_type", "mode", "date")
    search_fields = ("number", "party__name", "reference")
