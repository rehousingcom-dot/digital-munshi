"""Naye plans (Starter/Pro/Business) upsert + purane (basic/premium) hide.
Deploy pe migrate ke saath prod DB me apne aap lag jaayega."""
from django.db import migrations

PLANS = [
    dict(code="starter", name="Starter", price_monthly=149, price_yearly=1499,
         max_users=1, max_invoices_per_month=0, sort_order=1,
         features=["GST billing & invoice", "Inventory & stock", "Udhaar / khata",
                   "POS billing", "WhatsApp share"]),
    dict(code="pro", name="Pro", price_monthly=299, price_yearly=2999,
         max_users=3, max_invoices_per_month=0, sort_order=2,
         features=["Sab Starter ka", "Accounting & GSTR reports", "Committee / BC",
                   "Reports & analytics", "3 users"]),
    dict(code="business", name="Business", price_monthly=499, price_yearly=4999,
         max_users=0, max_invoices_per_month=0, sort_order=3,
         features=["Sab Pro ka", "Multi-firm", "HR & Payroll",
                   "Supplier marketplace", "Unlimited users + priority support"]),
]
RETIRE = ["basic", "premium"]


def apply(apps, schema_editor):
    Plan = apps.get_model("tenants", "Plan")
    for p in PLANS:
        Plan.objects.update_or_create(code=p["code"], defaults={**p, "is_active": True})
    Plan.objects.filter(code__in=RETIRE).update(is_active=False)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0004_organization_referral'),
    ]

    operations = [
        migrations.RunPython(apply, noop),
    ]
