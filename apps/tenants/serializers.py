from rest_framework import serializers
from .models import Plan, Subscription


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = ("id", "code", "name", "price_monthly", "price_yearly",
                  "max_users", "max_invoices_per_month", "features")


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)
    days_left = serializers.IntegerField(read_only=True)
    access_allowed = serializers.SerializerMethodField()
    organization_name = serializers.CharField(source="organization.name", read_only=True)

    class Meta:
        model = Subscription
        fields = ("organization_name", "plan", "status", "billing_cycle",
                  "trial_ends_at", "current_period_end", "days_left", "access_allowed")

    def get_access_allowed(self, obj):
        return obj.is_access_allowed()
