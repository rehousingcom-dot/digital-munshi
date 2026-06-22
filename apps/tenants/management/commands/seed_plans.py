"""Default subscription plans banata hai. Admin se prices edit ho sakti hain.
Run: python manage.py seed_plans
"""
from django.core.management.base import BaseCommand
from apps.tenants.models import Plan

PLANS = [
    dict(code="basic", name="Basic", price_monthly=399, price_yearly=3999,
         max_users=3, max_invoices_per_month=0, sort_order=1,
         features=["Billing", "Inventory", "Party ledger", "GST reports"]),
    dict(code="pro", name="Pro", price_monthly=799, price_yearly=7999,
         max_users=10, max_invoices_per_month=0, sort_order=2,
         features=["Sab Basic ka", "Multi-godown", "Dashboard analytics", "Invoice PDF"]),
    dict(code="premium", name="Premium", price_monthly=1499, price_yearly=14999,
         max_users=0, max_invoices_per_month=0, sort_order=3,
         features=["Sab Pro ka", "Unlimited users", "Priority support"]),
]


class Command(BaseCommand):
    help = "Seed default subscription plans."

    def handle(self, *args, **options):
        for p in PLANS:
            Plan.objects.update_or_create(code=p["code"], defaults=p)
        self.stdout.write(self.style.SUCCESS(f"{Plan.objects.count()} plans ready."))
