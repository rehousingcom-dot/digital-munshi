import uuid as _uuid
from datetime import timedelta
from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils import timezone

TRIAL_DAYS = 7


class Organization(models.Model):
    """Ek tenant = ek business jo hamara SaaS use karta hai. Data isolation
    iss organization ke around hota hai.
    """
    name = models.CharField(max_length=200)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                              null=True, blank=True, related_name="owned_orgs")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # Online catalog (public shop link)
    catalog_uuid = models.UUIDField(default=_uuid.uuid4, editable=False, unique=True)
    catalog_enabled = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Plan(models.Model):
    """Subscription plan — pricing aur limits. Admin se edit ho sakta hai."""
    code = models.CharField(max_length=30, unique=True)   # e.g. basic, pro
    name = models.CharField(max_length=80)
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price_yearly = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_users = models.PositiveIntegerField(default=5)
    max_invoices_per_month = models.PositiveIntegerField(default=0, help_text="0 = unlimited")
    features = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "price_monthly"]

    def __str__(self):
        return self.name

    def price_for(self, cycle):
        return self.price_yearly if cycle == "YEARLY" else self.price_monthly


class Subscription(models.Model):
    """Ek organization ka ek subscription. Trial se shuru, payment ke baad active."""

    class Status(models.TextChoices):
        TRIAL = "TRIAL", "Trial"
        ACTIVE = "ACTIVE", "Active"
        PAST_DUE = "PAST_DUE", "Past Due"
        EXPIRED = "EXPIRED", "Expired"
        CANCELLED = "CANCELLED", "Cancelled"

    class Cycle(models.TextChoices):
        MONTHLY = "MONTHLY", "Monthly"
        YEARLY = "YEARLY", "Yearly"

    organization = models.OneToOneField(Organization, on_delete=models.CASCADE, related_name="subscription")
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.TRIAL)
    billing_cycle = models.CharField(max_length=10, choices=Cycle.choices, default=Cycle.MONTHLY)

    trial_ends_at = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.organization.name} — {self.status}"

    @classmethod
    def start_trial(cls, organization, plan=None):
        return cls.objects.create(
            organization=organization, plan=plan, status=cls.Status.TRIAL,
            trial_ends_at=timezone.now() + timedelta(days=TRIAL_DAYS),
        )

    @property
    def access_until(self):
        if self.status == self.Status.TRIAL:
            return self.trial_ends_at
        if self.status in (self.Status.ACTIVE, self.Status.PAST_DUE):
            return self.current_period_end
        return None

    def is_access_allowed(self):
        """Trial valid hai ya paid period chal raha hai?"""
        if self.status == self.Status.CANCELLED:
            return False
        until = self.access_until
        return bool(until and until >= timezone.now())

    @property
    def days_left(self):
        until = self.access_until
        if not until:
            return 0
        delta = until - timezone.now()
        return max(0, delta.days + (1 if delta.seconds > 0 else 0))

    def activate(self, plan, cycle):
        """Payment success ke baad — plan set karke period extend karta hai."""
        now = timezone.now()
        base = self.current_period_end if (self.current_period_end and self.current_period_end > now) else now
        days = 365 if cycle == self.Cycle.YEARLY else 30
        self.plan = plan
        self.billing_cycle = cycle
        self.status = self.Status.ACTIVE
        self.current_period_end = base + timedelta(days=days)
        self.save()

    def refresh_status(self):
        """Agar trial/period khatam ho gaya to EXPIRED mark karta hai."""
        if self.status in (self.Status.TRIAL, self.Status.ACTIVE, self.Status.PAST_DUE):
            if not self.is_access_allowed():
                self.status = self.Status.EXPIRED
                self.save(update_fields=["status"])
        return self.status


class SubscriptionPayment(models.Model):
    """Har subscription payment ka record (Razorpay order/payment)."""

    class Status(models.TextChoices):
        CREATED = "CREATED", "Created"
        PAID = "PAID", "Paid"
        FAILED = "FAILED", "Failed"

    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name="payments")
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True)
    cycle = models.CharField(max_length=10, default="MONTHLY")
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    gateway = models.CharField(max_length=20, default="razorpay")
    gateway_order_id = models.CharField(max_length=80, blank=True)
    gateway_payment_id = models.CharField(max_length=80, blank=True)
    gateway_signature = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.CREATED)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.subscription.organization.name} — {self.amount} ({self.status})"


class Lead(models.Model):
    """Marketing website se aaya lead (public form). Tenant-scoped nahi — SaaS owner ke liye."""
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=20)
    business = models.CharField(max_length=160, blank=True)
    message = models.TextField(blank=True)
    source = models.CharField(max_length=120, blank=True, help_text="Kaunse page se aaya")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.phone})"
