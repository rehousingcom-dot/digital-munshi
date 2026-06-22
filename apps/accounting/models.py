from decimal import Decimal, ROUND_HALF_UP
from django.db import models
from apps.tenants.tenancy import OrgOwned

TWO = Decimal("0.01")


def money(x):
    return Decimal(str(x or 0)).quantize(TWO, rounding=ROUND_HALF_UP)


# Default chart of accounts (har naye firm ko milega)
DEFAULT_ACCOUNTS = [
    ("1000", "Cash", "ASSET"), ("1010", "Bank", "ASSET"),
    ("1100", "Accounts Receivable (Debtors)", "ASSET"), ("1200", "Stock / Inventory", "ASSET"),
    ("2000", "Accounts Payable (Creditors)", "LIABILITY"), ("2100", "GST Payable", "LIABILITY"),
    ("2200", "Loans", "LIABILITY"), ("3000", "Capital", "EQUITY"),
    ("4000", "Sales Revenue", "INCOME"), ("4100", "Other Income", "INCOME"),
    ("5000", "Purchases / COGS", "EXPENSE"), ("5100", "Rent", "EXPENSE"),
    ("5200", "Salary & Wages", "EXPENSE"), ("5300", "Electricity", "EXPENSE"),
    ("5400", "Transport / Diesel", "EXPENSE"), ("5900", "Other Expenses", "EXPENSE"),
]


class Account(OrgOwned):
    """Chart of Accounts — ledger head (Zoho parity)."""
    class Type(models.TextChoices):
        ASSET = "ASSET", "Asset"
        LIABILITY = "LIABILITY", "Liability"
        EQUITY = "EQUITY", "Equity"
        INCOME = "INCOME", "Income"
        EXPENSE = "EXPENSE", "Expense"

    code = models.CharField(max_length=20)
    name = models.CharField(max_length=120)
    account_type = models.CharField(max_length=12, choices=Type.choices, default=Type.EXPENSE)
    opening_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("organization", "code")
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} · {self.name}"

    @property
    def balance(self):
        agg = self.journal_lines.aggregate(
            d=models.Sum("debit"), c=models.Sum("credit"))
        debit = Decimal(str(agg["d"] or 0))
        credit = Decimal(str(agg["c"] or 0))
        ob = Decimal(str(self.opening_balance))
        # Asset/Expense => debit positive; Liability/Equity/Income => credit positive
        if self.account_type in ("ASSET", "EXPENSE"):
            return money(ob + debit - credit)
        return money(ob + credit - debit)


class JournalEntry(OrgOwned):
    """Manual journal (double-entry) — debit total == credit total."""
    date = models.DateField()
    narration = models.CharField(max_length=255, blank=True)
    reference = models.CharField(max_length=80, blank=True)
    tags = models.CharField(max_length=120, blank=True, help_text="Reporting tags (comma-separated)")

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"JE {self.id} - {self.date}"

    @property
    def total_debit(self):
        return money(sum((Decimal(str(l.debit)) for l in self.lines.all()), Decimal("0")))

    @property
    def total_credit(self):
        return money(sum((Decimal(str(l.credit)) for l in self.lines.all()), Decimal("0")))

    @property
    def is_balanced(self):
        return self.total_debit == self.total_credit


class JournalLine(OrgOwned):
    journal = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name="lines")
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="journal_lines")
    debit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    notes = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"{self.account.code} Dr {self.debit} Cr {self.credit}"


def seed_accounts(org):
    """Naye org ke liye default chart of accounts."""
    for code, name, atype in DEFAULT_ACCOUNTS:
        Account.all_objects.get_or_create(
            organization=org, code=code,
            defaults={"name": name, "account_type": atype})
