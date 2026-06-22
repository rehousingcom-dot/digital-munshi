from decimal import Decimal, ROUND_HALF_UP
from django.db import models
from apps.tenants.tenancy import OrgOwned
from apps.party.models import Party

TWO = Decimal("0.01")


def money(x):
    return Decimal(str(x or 0)).quantize(TWO, rounding=ROUND_HALF_UP)


class BankAccount(OrgOwned):
    """Bank account ya Cash-in-hand (Vyapar 'Cash & Bank').
    account_type=CASH -> cash drawer; BANK -> bank/UPI account.
    """
    class Kind(models.TextChoices):
        CASH = "CASH", "Cash in Hand"
        BANK = "BANK", "Bank Account"

    name = models.CharField(max_length=120)
    account_type = models.CharField(max_length=10, choices=Kind.choices, default=Kind.BANK)
    account_no = models.CharField(max_length=30, blank=True)
    ifsc = models.CharField(max_length=15, blank=True)
    bank_name = models.CharField(max_length=120, blank=True)
    upi_id = models.CharField(max_length=80, blank=True)
    opening_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["account_type", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_account_type_display()})"

    @property
    def balance(self):
        agg = self.transactions.aggregate(
            inflow=models.Sum("amount", filter=models.Q(direction="IN")),
            outflow=models.Sum("amount", filter=models.Q(direction="OUT")),
        )
        bal = Decimal(str(self.opening_balance))
        bal += Decimal(str(agg["inflow"] or 0)) - Decimal(str(agg["outflow"] or 0))
        return money(bal)


class BankTransaction(OrgOwned):
    """Bank/cash mein paisa aaya (IN) ya gaya (OUT). Adjust/deposit/withdraw/transfer."""
    class Direction(models.TextChoices):
        IN = "IN", "Money In"
        OUT = "OUT", "Money Out"

    account = models.ForeignKey(BankAccount, on_delete=models.CASCADE, related_name="transactions")
    date = models.DateField()
    direction = models.CharField(max_length=3, choices=Direction.choices, default=Direction.IN)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    mode = models.CharField(max_length=20, blank=True, default="CASH")
    party = models.ForeignKey(Party, on_delete=models.SET_NULL, null=True, blank=True)
    reference = models.CharField(max_length=80, blank=True)
    notes = models.CharField(max_length=200, blank=True)
    reconciled = models.BooleanField(default=False, help_text="Bank statement se match ho gaya?")

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"{self.account.name} {self.direction} {self.amount}"


class Cheque(OrgOwned):
    """Post-dated cheque tracking — receivable (customer se) / payable (supplier ko)."""
    class Kind(models.TextChoices):
        RECEIVABLE = "RECEIVABLE", "Receivable (customer se)"
        PAYABLE = "PAYABLE", "Payable (supplier ko)"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CLEARED = "CLEARED", "Cleared"
        BOUNCED = "BOUNCED", "Bounced"

    cheque_type = models.CharField(max_length=12, choices=Kind.choices, default=Kind.RECEIVABLE)
    party = models.ForeignKey(Party, on_delete=models.SET_NULL, null=True, blank=True)
    cheque_no = models.CharField(max_length=30)
    bank_name = models.CharField(max_length=120, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    issue_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    notes = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["due_date", "-id"]

    def __str__(self):
        return f"{self.cheque_no} — {self.amount} ({self.status})"


class LoanAccount(OrgOwned):
    """Business loan with auto EMI calculation (reducing-balance)."""
    lender = models.CharField(max_length=120)
    account_no = models.CharField(max_length=40, blank=True)
    principal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    interest_rate = models.DecimalField(max_digits=6, decimal_places=2, default=0,
                                        help_text="Annual % rate")
    tenure_months = models.PositiveIntegerField(default=12)
    start_date = models.DateField(null=True, blank=True)
    current_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    notes = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"{self.lender} — {self.principal}"

    @property
    def emi(self):
        """Monthly EMI = P*r*(1+r)^n / ((1+r)^n - 1), r = monthly rate."""
        P = Decimal(str(self.principal or 0))
        n = int(self.tenure_months or 0)
        annual = Decimal(str(self.interest_rate or 0))
        if P <= 0 or n <= 0:
            return Decimal("0.00")
        if annual == 0:
            return money(P / n)
        r = annual / Decimal("1200")  # monthly fraction
        factor = (Decimal("1") + r) ** n
        emi = P * r * factor / (factor - Decimal("1"))
        return money(emi)

    @property
    def total_payable(self):
        return money(self.emi * Decimal(str(self.tenure_months or 0)))

    @property
    def total_interest(self):
        return money(self.total_payable - Decimal(str(self.principal or 0)))

    def save(self, *args, **kwargs):
        if self._state.adding and not self.current_balance:
            self.current_balance = self.principal
        super().save(*args, **kwargs)


class ExpenseCategory(OrgOwned):
    """Expense head — rent, electricity, salary, diesel, labour, packing, etc."""
    name = models.CharField(max_length=80)

    class Meta:
        verbose_name_plural = "Expense categories"
        unique_together = ("organization", "name")
        ordering = ["name"]

    def __str__(self):
        return self.name


class Expense(OrgOwned):
    """Business expense (money out) — P&L ko accurate karta hai.
    Movers ke liye: diesel, labour, packing material; kirana ke liye: rent, bijli.
    """
    date = models.DateField()
    category = models.ForeignKey(ExpenseCategory, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="expenses")
    party = models.ForeignKey(Party, on_delete=models.SET_NULL, null=True, blank=True,
                              help_text="Vendor (optional)")
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0,
                                     help_text="GST/ITC portion (optional)")
    mode = models.CharField(max_length=20, default="CASH")
    reference = models.CharField(max_length=80, blank=True)
    notes = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"{self.category} — {self.amount}"

    @property
    def total(self):
        return money(Decimal(str(self.amount)) + Decimal(str(self.tax_amount)))
