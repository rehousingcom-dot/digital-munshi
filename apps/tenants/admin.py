from django.contrib import admin
from .models import Organization, Plan, Subscription, SubscriptionPayment, Lead


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "is_active", "created_at")
    search_fields = ("name",)


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "price_monthly", "price_yearly", "max_users", "is_active")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("organization", "plan", "status", "billing_cycle",
                    "trial_ends_at", "current_period_end")
    list_filter = ("status", "billing_cycle")


@admin.register(SubscriptionPayment)
class SubscriptionPaymentAdmin(admin.ModelAdmin):
    list_display = ("subscription", "plan", "cycle", "amount", "status", "paid_at")
    list_filter = ("status", "gateway")


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "business", "source", "created_at")
    search_fields = ("name", "phone", "business")
    list_filter = ("created_at",)
    readonly_fields = ("created_at",)
