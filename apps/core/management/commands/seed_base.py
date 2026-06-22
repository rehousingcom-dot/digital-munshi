"""Pehli baar setup: basic units, GST tax slabs, ek default godown banata hai.
Run: python manage.py seed_base
"""
from django.core.management.base import BaseCommand
from apps.core.models import Unit, TaxRate, Godown, Company


class Command(BaseCommand):
    help = "Seed basic master data (units, GST tax rates, default godown)."

    def handle(self, *args, **options):
        units = [
            ("Pieces", "PCS", False), ("Box", "BOX", False), ("Dozen", "DOZ", False),
            ("Kilogram", "KG", True), ("Gram", "GM", True), ("Litre", "LTR", True),
            ("Metre", "MTR", True), ("Packet", "PKT", False),
        ]
        for name, code, dec in units:
            Unit.objects.get_or_create(short_code=code, defaults={"name": name, "allow_decimal": dec})

        for name, pct in [("GST 0%", 0), ("GST 5%", 5), ("GST 12%", 12),
                          ("GST 18%", 18), ("GST 28%", 28)]:
            TaxRate.objects.get_or_create(name=name, defaults={"percent": pct})

        Godown.objects.get_or_create(name="Main Store")
        if not Company.objects.exists():
            Company.objects.create(name="My Business")

        self.stdout.write(self.style.SUCCESS(
            "Seed done: %d units, %d tax rates, godown ready." % (
                Unit.objects.count(), TaxRate.objects.count())))
