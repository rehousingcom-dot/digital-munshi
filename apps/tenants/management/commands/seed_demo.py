"""Demo business + sample data — local testing ke liye ek hi command.
Login: demo / demo12345
Run: python manage.py seed_demo
"""
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from apps.tenants.services import signup_organization
from apps.tenants.tenancy import set_current_org, clear_current_org

User = get_user_model()


class Command(BaseCommand):
    help = "Demo business + sample items/parties/sales banata hai (login: demo/demo12345)."

    def handle(self, *args, **options):
        if User.objects.filter(username="demo").exists():
            self.stdout.write(self.style.WARNING("Demo already exists (login: demo / demo12345)."))
            return

        user, org, sub = signup_organization(
            username="demo", password="demo12345", email="demo@example.com",
            org_name="Demo Kirana Store", business_type="RETAIL",
        )
        set_current_org(org)
        try:
            from apps.core.models import Unit, TaxRate, Godown
            from apps.inventory.models import Item, Category
            from apps.party.models import Party
            from apps.billing.models import Voucher, VoucherLine

            pcs = Unit.objects.get(short_code="PCS")
            gst18 = TaxRate.objects.get(name="GST 18%")
            gst5 = TaxRate.objects.get(name="GST 5%")
            godown = Godown.objects.get(name="Main Store")
            cat = Category.objects.create(name="Grocery", code="GRO")

            items = []
            for nm, mrp, tax in [("Parle-G Biscuit", 10, gst18), ("Tata Salt 1kg", 28, gst5),
                                 ("Surf Excel 500g", 60, gst18), ("Amul Butter 100g", 55, gst18),
                                 ("Maggi Noodles", 14, gst18)]:
                it = Item.objects.create(name=nm, category=cat, primary_unit=pcs,
                                         tax_rate=tax, mrp=mrp, reorder_level=20)
                items.append(it)

            customers = [Party.objects.create(name=n, party_type="CUSTOMER", phone=p, state_code="09")
                         for n, p in [("Sharma Ji", "9876500001"), ("Verma Store", "9876500002"),
                                      ("Walk-in Customer", "")]]
            Party.objects.create(name="HUL Distributor", party_type="SUPPLIER", state_code="09")

            # Purchase stock for all items
            sup = Party.objects.get(name="HUL Distributor")
            for it in items:
                pv = Voucher.objects.create(voucher_type="PURCHASE", date=date.today() - timedelta(days=7),
                                            party=sup, godown=godown, company_state_code="09")
                VoucherLine.objects.create(voucher=pv, variant=it.variants.first(), unit=pcs,
                                           qty=100, rate=float(it.mrp) * 0.7, tax_percent=18,
                                           margin_type="PERCENT", margin_value=30)
                pv.recalculate(); pv.post()

            # Some sales over last few days
            for d in range(5):
                cust = customers[d % len(customers)]
                sv = Voucher.objects.create(voucher_type="SALE", date=date.today() - timedelta(days=d),
                                            party=cust, godown=godown, company_state_code="09")
                for it in items[:3]:
                    VoucherLine.objects.create(voucher=sv, variant=it.variants.first(), unit=pcs,
                                               qty=5 + d, rate=float(it.mrp), tax_percent=18, disc1_pct=5)
                sv.recalculate(); sv.post()

            self.stdout.write(self.style.SUCCESS(
                "Demo ready! Login: demo / demo12345  |  Items: %d, Sales added." % len(items)))
        finally:
            clear_current_org()
