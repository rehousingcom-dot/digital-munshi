"""Signup + new-organization provisioning."""
from django.contrib.auth import get_user_model
from django.db import transaction

from .models import Organization, Plan, Subscription

User = get_user_model()

DEFAULT_UNITS = [
    ("Pieces", "PCS", False), ("Box", "BOX", False), ("Dozen", "DOZ", False),
    ("Kilogram", "KG", True), ("Gram", "GM", True), ("Litre", "LTR", True),
    ("Metre", "MTR", True), ("Packet", "PKT", False),
]
DEFAULT_TAXES = [("GST 0%", 0), ("GST 5%", 5), ("GST 12%", 12), ("GST 18%", 18), ("GST 28%", 28)]


def provision_default_masters(org, business_type="GENERAL"):
    """Naye organization ke liye default units, GST slabs, godown, company.
    Company ko business_type ke hisaab se configure karta hai.
    """
    from apps.core.models import Unit, TaxRate, Godown, Company
    for name, code, dec in DEFAULT_UNITS:
        Unit.all_objects.get_or_create(organization=org, short_code=code,
                                       defaults={"name": name, "allow_decimal": dec})
    for name, pct in DEFAULT_TAXES:
        TaxRate.all_objects.get_or_create(organization=org, name=name, defaults={"percent": pct})
    Godown.all_objects.get_or_create(organization=org, name="Main Store")
    company, created = Company.all_objects.get_or_create(
        organization=org, defaults={"name": org.name})
    company.apply_business_type(business_type)
    company.save()
    try:
        from apps.accounting.models import seed_accounts
        seed_accounts(org)
    except Exception:
        pass


@transaction.atomic
def signup_organization(*, username, password, email, org_name, phone="", business_type="GENERAL",
                        referral_code=None):
    """Naya business register: user + organization + 7-day trial + default masters.
    referral_code diya ho to referrer + naye dono ko 30 din free bonus."""
    if User.objects.filter(username=username).exists():
        raise ValueError("Username pehle se exist karta hai.")
    org = Organization.objects.create(name=org_name)
    user = User.objects.create_user(
        username=username, password=password, email=email,
        role=User.Role.ADMIN, phone=phone, organization=org,
    )
    org.owner = user
    org.save(update_fields=["owner"])
    org.ensure_referral_code()

    default_plan = Plan.objects.filter(is_active=True).order_by("sort_order").first()
    sub = Subscription.start_trial(org, plan=default_plan)
    provision_default_masters(org, business_type=business_type)

    # Referral bonus — dono ko 30 din free
    code = (referral_code or "").strip().upper()
    if code:
        referrer = Organization.objects.filter(referral_code=code).exclude(pk=org.pk).first()
        if referrer:
            org.referred_by = referrer
            org.save(update_fields=["referred_by"])
            try:
                sub.grant_bonus(30)
                rsub = getattr(referrer, "subscription", None)
                if rsub:
                    rsub.grant_bonus(30)
            except Exception:
                pass
    return user, org, sub
