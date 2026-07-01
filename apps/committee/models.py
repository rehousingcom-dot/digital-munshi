"""Committee / BC / Chit fund management.

Ek committee (BC/kitty) me kuch members milkar har month paise jama karte hain,
aur har month ek "boli" (bid/discount) lagti hai — jo sabse zyada discount deta hai
woh us month ki poori rakam (minus boli) le jaata hai. Baaki members us month kam
bharte hain. Coupon organizer ke hote hain (collection me add hote hain).

per_head (har member ka us month ka contribution) =
    (total_value - boli + coupon_total) / members_count
"""
import uuid
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, timedelta
from django.db import models
from apps.tenants.tenancy import OrgOwned

TWO = Decimal("0.01")


def money(x):
    return Decimal(str(x or 0)).quantize(TWO, rounding=ROUND_HALF_UP)


class Committee(OrgOwned):
    """Ek BC/committee scheme — total value, members, coupons, rules."""

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        CLOSED = "CLOSED", "Closed"

    name = models.CharField(max_length=120)
    total_value = models.DecimalField(max_digits=14, decimal_places=2, default=0,
                                      help_text="Poori committee ki value (e.g. 600000)")
    members_count = models.PositiveSmallIntegerField(default=12,
                                      help_text="Members / months (usually same)")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    # Organizer coupons — collection me add hote hain, coupon holders ko jaate hain
    coupon1 = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("2000"))
    coupon2 = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("1000"))
    coupon1_holder = models.CharField(max_length=120, blank=True)
    coupon2_holder = models.CharField(max_length=120, blank=True)

    # Rules
    bid_increment = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("1000"),
                                        help_text="Boli minimum itne ke multiple me")
    late_fee_per_day = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("500"))
    bid_day = models.PositiveSmallIntegerField(default=5, help_text="Har month is din boli lagti hai")
    due_day = models.PositiveSmallIntegerField(default=10, help_text="Is din tak payment; baad me late fee")

    status = models.CharField(max_length=8, choices=Status.choices, default=Status.ACTIVE)
    notes = models.TextField(blank=True)

    # Public sharing (online boli + join link)
    public_uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    bidding_open = models.BooleanField(default=False)
    open_month = models.PositiveSmallIntegerField(null=True, blank=True,
                                                  help_text="Kaunse month ki boli abhi khuli hai")
    bid_close_at = models.DateTimeField(null=True, blank=True,
                                        help_text="Is time ke baad boli nahi lag sakti (deadline)")
    allow_join = models.BooleanField(default=True, help_text="Public join link se log apply kar sakte hain")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.total_value})"

    def bidding_live(self):
        """Boli abhi lag sakti hai? (khuli hai AUR deadline nahi nikli)."""
        if not self.bidding_open or not self.open_month:
            return False
        if self.bid_close_at:
            from django.utils import timezone
            return timezone.now() <= self.bid_close_at
        return True

    @property
    def coupon_total(self):
        return money(self.coupon1 + self.coupon2)

    @property
    def monthly_base(self):
        n = self.members_count or 1
        return money(self.total_value / n)

    def per_head_for(self, bid_amount):
        """Kisi boli pe har member ka contribution."""
        n = self.members_count or 1
        collection = money(self.total_value) - money(bid_amount) + self.coupon_total
        return money(collection / n)


class CommitteeMember(OrgOwned):
    """Committee ka ek member."""
    committee = models.ForeignKey(Committee, on_delete=models.CASCADE, related_name="members")
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=15, blank=True)
    # Personal secure link ke liye token — sirf yahi member apni boli/statement dekh sake
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    # Optional link to an existing party/customer
    party = models.ForeignKey("party.Party", on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name


class CommitteeRound(OrgOwned):
    """Ek month ki boli/round."""
    committee = models.ForeignKey(Committee, on_delete=models.CASCADE, related_name="rounds")
    month_no = models.PositiveSmallIntegerField()
    date = models.DateField(null=True, blank=True)
    winner = models.ForeignKey(CommitteeMember, on_delete=models.SET_NULL, null=True, blank=True,
                               related_name="wins")
    bid_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0,
                                     help_text="Boli/discount (jitna loss dekar uthaya)")

    # Computed
    net_payable = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    coupon_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    collection = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    per_head = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        unique_together = ("committee", "month_no")
        ordering = ["month_no"]

    def __str__(self):
        return f"{self.committee.name} — month {self.month_no}"

    def compute(self, save=True):
        c = self.committee
        n = c.members_count or 1
        self.net_payable = money(c.total_value) - money(self.bid_amount)
        self.coupon_total = c.coupon_total
        self.collection = money(self.net_payable + self.coupon_total)
        self.per_head = money(self.collection / n)
        if save:
            self.save()

    def due_date(self):
        if not self.date:
            return None
        try:
            return self.date.replace(day=self.committee.due_day)
        except ValueError:
            return self.date


class CommitteePayment(OrgOwned):
    """Ek member ka ek round me contribution + late fee tracking."""
    round = models.ForeignKey(CommitteeRound, on_delete=models.CASCADE, related_name="payments")
    member = models.ForeignKey(CommitteeMember, on_delete=models.CASCADE, related_name="payments")
    amount_due = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    late_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    paid_on = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ("round", "member")
        ordering = ["member_id"]

    def __str__(self):
        return f"{self.member.name} — R{self.round.month_no} — {self.amount_paid}/{self.amount_due}"

    @property
    def total_due(self):
        return money(self.amount_due + self.late_fee)

    @property
    def status(self):
        if self.amount_paid <= 0:
            return "PENDING"
        if self.amount_paid + Decimal("0.01") >= self.total_due:
            return "PAID"
        return "PARTIAL"

    def compute_late_fee(self, save=True):
        """paid_on aur due_date se late fee nikalta hai (₹X/day)."""
        due = self.round.due_date()
        if due and self.paid_on and self.paid_on > due:
            days = (self.paid_on - due).days
            self.late_fee = money(self.committee_late_rate * days)
        else:
            self.late_fee = money(0)
        if save:
            self.save()

    @property
    def committee_late_rate(self):
        return self.round.committee.late_fee_per_day


class CommitteeBid(OrgOwned):
    """Online boli — member public link se apni bid daalta hai (transparency)."""
    committee = models.ForeignKey(Committee, on_delete=models.CASCADE, related_name="bids")
    month_no = models.PositiveSmallIntegerField()
    member = models.ForeignKey(CommitteeMember, on_delete=models.CASCADE, related_name="bids")
    bid_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0,
                                     help_text="Jitna discount/loss dekar uthana chahta hai")

    class Meta:
        unique_together = ("committee", "month_no", "member")
        ordering = ["-bid_amount"]

    def __str__(self):
        return f"{self.member.name} R{self.month_no} bid {self.bid_amount}"


class CommitteeJoinRequest(OrgOwned):
    """Public join link se aaya naya member request (growth loop)."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    committee = models.ForeignKey(Committee, on_delete=models.CASCADE, related_name="join_requests")
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=15, blank=True)
    message = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} → {self.committee.name} ({self.status})"
