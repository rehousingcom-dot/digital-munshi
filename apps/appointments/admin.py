from django.contrib import admin
from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("customer_name", "service", "staff", "start", "status", "price")
    list_filter = ("status",)
    search_fields = ("customer_name", "phone", "service")
