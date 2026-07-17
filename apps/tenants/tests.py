"""Automated test suite — core SaaS + billing flows.
Run: python manage.py test
"""
from datetime import date, timedelta
from django.test import TestCase
from django.utils import timezone
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.tenants.models import Subscription, Plan
from apps.tenants.management.commands.seed_plans import PLANS


def _seed_plans():
    for p in PLANS:
        Plan.objects.update_or_create(code=p["code"], defaults=p)


class SaaSFlowTests(TestCase):
    def setUp(self):
        _seed_plans()
        self.c = APIClient()

    def _signup(self, username, org, btype="RETAIL"):
        # Signup ab email + OTP maangta hai (feature: mobile/OTP verification).
        # Test me OTP seedhe cache me daal do (locmem cache), phir wahi bhej do.
        email = username + "@test.com"
        cache.set("otp:" + email, "123456", 600)
        r = self.c.post("/api/signup/", {"username": username, "password": "pass12345",
                                         "org_name": org, "business_type": btype,
                                         "email": email, "otp": "123456"}, format="json")
        self.assertEqual(r.status_code, 201)
        return r.json()["tokens"]["access"]

    def _auth(self, token):
        self.c.credentials(HTTP_AUTHORIZATION="Bearer " + token)

    def test_signup_creates_trial_and_masters(self):
        tok = self._signup("u1", "Org1")
        self._auth(tok)
        sub = self.c.get("/api/subscription/").json()
        self.assertEqual(sub["status"], "TRIAL")
        self.assertTrue(sub["access_allowed"])
        units = self.c.get("/api/units/?page_size=500").json()
        self.assertEqual(units["count"], 8)

    def test_tenant_isolation(self):
        ta = self._signup("a", "A Co")
        tb = self._signup("b", "B Co")
        self._auth(ta)
        u = self.c.get("/api/units/?page_size=500").json()["results"][0]["id"]
        self.c.post("/api/items/", {"name": "ItemA", "primary_unit": u, "mrp": 10}, format="json")
        self.assertEqual(self.c.get("/api/items/").json()["count"], 1)
        self._auth(tb)
        self.assertEqual(self.c.get("/api/items/").json()["count"], 0)

    def test_billing_calculation_and_stock(self):
        tok = self._signup("biz", "Biz", "WHOLESALE")
        self._auth(tok)
        u = self.c.get("/api/units/?page_size=500").json()["results"][0]["id"]
        g = self.c.get("/api/godowns/").json()["results"][0]["id"]
        it = self.c.post("/api/items/", {"name": "Pen", "primary_unit": u, "mrp": 10}, format="json").json()
        v = it["variants"][0]["id"]
        sup = self.c.post("/api/parties/", {"name": "Sup", "party_type": "SUPPLIER"}, format="json").json()["id"]
        # purchase 100 units
        pur = self.c.post("/api/vouchers/", {"voucher_type": "PURCHASE", "date": str(date.today()),
            "party": sup, "godown": g, "lines": [{"variant": v, "unit": u, "qty": "100", "rate": "7", "tax_percent": "18"}]}, format="json").json()
        self.c.post(f"/api/vouchers/{pur['id']}/post_to_stock/")
        # sale 10 with 10% disc, 18% tax -> taxable 90, tax 16.2
        cust = self.c.post("/api/parties/", {"name": "Cust", "party_type": "CUSTOMER", "state_code": "09"}, format="json").json()["id"]
        s = self.c.post("/api/vouchers/", {"voucher_type": "SALE", "date": str(date.today()),
            "party": cust, "godown": g, "company_state_code": "09",
            "lines": [{"variant": v, "unit": u, "qty": "10", "rate": "10", "disc1_pct": "10", "tax_percent": "18"}]}, format="json").json()
        self.assertEqual(s["taxable_value"], "90.00")
        self.assertEqual(s["total_tax"], "16.20")

    def test_subscription_expiry_and_pay(self):
        tok = self._signup("exp", "Exp Co")
        self._auth(tok)
        sub = Subscription.objects.get(organization__name="Exp Co")
        sub.trial_ends_at = timezone.now() - timedelta(days=1)
        sub.save()
        self.assertEqual(self.c.get("/api/items/").status_code, 402)
        o = self.c.post("/api/subscription/create_order/", {"plan_code": "starter", "cycle": "MONTHLY"}, format="json").json()
        self.c.post("/api/subscription/verify/", {"razorpay_order_id": o["order_id"]}, format="json")
        self.assertEqual(self.c.get("/api/items/").status_code, 200)

    def test_role_permissions(self):
        from apps.accounts.models import User
        from apps.tenants.models import Organization
        tok = self._signup("owner", "Role Co")
        self._auth(tok)
        u = self.c.get("/api/units/?page_size=500").json()["results"][0]["id"]
        org = Organization.objects.get(name="Role Co")
        User.objects.create_user("viewer", "v@v.com", "pass12345", role="VIEWER", organization=org)
        vt = self.c.post("/api/auth/token/", {"username": "viewer", "password": "pass12345"}, format="json").json()["access"]
        self._auth(vt)
        self.assertEqual(self.c.get("/api/items/").status_code, 200)            # read ok
        r = self.c.post("/api/items/", {"name": "X", "primary_unit": u, "mrp": 1}, format="json")
        self.assertEqual(r.status_code, 403)                                    # write blocked

    def test_composition_bill_of_supply(self):
        tok = self._signup("comp", "Comp Co")
        self._auth(tok)
        self.c.put("/api/business-profile/", {"gst_scheme": "COMPOSITION"}, format="json")
        u = self.c.get("/api/units/?page_size=500").json()["results"][0]["id"]
        g = self.c.get("/api/godowns/").json()["results"][0]["id"]
        it = self.c.post("/api/items/", {"name": "Sugar", "primary_unit": u, "mrp": 40}, format="json").json()
        v = it["variants"][0]["id"]
        cust = self.c.post("/api/parties/", {"name": "C", "party_type": "CUSTOMER"}, format="json").json()["id"]
        s = self.c.post("/api/vouchers/", {"voucher_type": "SALE", "date": str(date.today()),
            "party": cust, "godown": g, "lines": [{"variant": v, "unit": u, "qty": "10", "rate": "40", "tax_percent": "18"}]}, format="json").json()
        self.assertEqual(s["total_tax"], "0.00")   # composition -> no tax

    def test_hr_payroll(self):
        tok = self._signup("hr", "HR Co")
        self._auth(tok)
        emp = self.c.post("/api/employees/", {"name": "Worker", "basic_salary": "15000",
            "hra": "5000", "allowances": "2000", "deductions": "1000", "working_days": 30}, format="json").json()
        self.assertTrue(emp["code"].startswith("EMP"))
        eid = emp["id"]
        # 15 present days
        for d in range(1, 16):
            self.c.post("/api/attendance/mark/", {"employee": eid, "date": f"2026-06-{d:02d}", "status": "PRESENT"}, format="json")
        slip = self.c.post("/api/payslips/generate/", {"employee": eid, "year": 2026, "month": 6, "working_days": 30}, format="json").json()
        # 15/30 paid -> basic 7500, gross 11000, net 10000
        self.assertEqual(slip["paid_days"], "15.0")
        self.assertEqual(slip["net_payable"], "10000.00")
