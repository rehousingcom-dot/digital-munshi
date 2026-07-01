import uuid
from decimal import Decimal
from django.db import models
from apps.tenants.tenancy import OrgOwned
from .validators import validate_gstin


class Party(OrgOwned):
    """Customer / Supplier master.

    Deck slide 4 requirements:
    - sundry debtors / creditors (opening balance + type)
    - GSTIN verify (format + checksum; address & legal name fields)
    - duplicate party name handling (warning via API check)
    - documents upload (PartyDocument)
    """

    class Type(models.TextChoices):
        CUSTOMER = "CUSTOMER", "Customer (Debtor)"
        SUPPLIER = "SUPPLIER", "Supplier (Creditor)"
        BOTH = "BOTH", "Both"

    class BalanceType(models.TextChoices):
        DEBIT = "DR", "To Receive (Debit)"
        CREDIT = "CR", "To Pay (Credit)"

    name = models.CharField(max_length=200, db_index=True)
    legal_name = models.CharField(max_length=200, blank=True, help_text="GST registered legal name")
    party_type = models.CharField(max_length=10, choices=Type.choices, default=Type.CUSTOMER)
    # Customer digital khata — public link (customer apna udhaar + pay dekh sake)
    khata_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    gstin = models.CharField("GSTIN", max_length=15, blank=True, validators=[validate_gstin])
    pan = models.CharField("PAN", max_length=10, blank=True)

    phone = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=80, blank=True)
    state = models.CharField(max_length=50, blank=True)
    state_code = models.CharField(max_length=2, blank=True, help_text="GST state code, e.g. 09 (UP)")
    pincode = models.CharField(max_length=6, blank=True)

    # Sundry debtors / creditors — opening balance
    opening_balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    opening_balance_type = models.CharField(max_length=2, choices=BalanceType.choices, default=BalanceType.DEBIT)

    # Credit control
    credit_limit = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    credit_days = models.PositiveIntegerField(default=0)
    loyalty_points = models.IntegerField(default=0, help_text="Har Rs 100 bikri pe 1 point (auto)")

    # Custom fields (Swipe-style) — extra business-specific data (JSON key/value)
    custom_fields = models.JSONField(default=dict, blank=True)
    group = models.CharField(max_length=80, blank=True, help_text="Party group (e.g. Dealers, VIP)")
    share_uuid = models.UUIDField(default=uuid.uuid4, editable=False,
                                  help_text="Customer portal public link")

    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Parties"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.gstin:
            self.gstin = self.gstin.strip().upper()
            # State code GSTIN ke pehle 2 digit se auto-fill
            if not self.state_code:
                self.state_code = self.gstin[:2]
        super().save(*args, **kwargs)


def party_doc_path(instance, filename):
    return f"party_documents/{instance.party_id}/{filename}"


class PartyDocument(OrgOwned):
    """Party ke documents — Aadhaar, GST cert, agreement, etc. (deck slide 4 point 1)."""
    party = models.ForeignKey(Party, on_delete=models.CASCADE, related_name="documents")
    title = models.CharField(max_length=120)
    file = models.FileField(upload_to=party_doc_path)

    def __str__(self):
        return f"{self.party.name} — {self.title}"
