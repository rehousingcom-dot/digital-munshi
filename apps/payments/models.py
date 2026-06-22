from decimal import Decimal
from django.db import models
from django.db.models import Sum
from apps.tenants.tenancy import OrgOwned
from apps.party.models import Party


class Payment(OrgOwned):
    """Receipt (customer se paisa aaya) / Payment (supplier ko diya).

    Party ke ledger balance ko affect karta hai — receivables/payables
    exact track hote hain.
    """

    class Type(models.TextChoices):
        RECEIPT = "RECEIPT", "Receipt (customer se)"
        PAYMENT = "PAYMENT", "Payment (supplier ko)"

    class Mode(models.TextChoices):
        CASH = "CASH", "Cash"
        BANK = "BANK", "Bank"
        UPI = "UPI", "UPI"
        CHEQUE = "CHEQUE", "Cheque"

    payment_type = models.CharField(max_length=10, choices=Type.choices, default=Type.RECEIPT)
    number = models.CharField(max_length=30, blank=True, db_index=True)
    date = models.DateField()
    party = models.ForeignKey(Party, on_delete=models.PROTECT, related_name="payments")
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    mode = models.CharField(max_length=10, choices=Mode.choices, default=Mode.CASH)
    reference = models.CharField(max_length=80, blank=True, help_text="Cheque/UPI ref no.")
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"{self.get_payment_type_display()} {self.number} - {self.amount}"

    def save(self, *args, **kwargs):
        if not self.number:
            super().save(*args, **kwargs)
            prefix = "RCT" if self.payment_type == "RECEIPT" else "PAY"
            n = Payment.objects.filter(payment_type=self.payment_type).count()
            self.number = f"{prefix}/{n:05d}"
            return super().save(update_fields=["number"])
        super().save(*args, **kwargs)


class PaymentAllocation(OrgOwned):
    """Payment ka kaunsa hissa kis invoice pe laga — invoice-wise settlement."""
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="allocations")
    voucher = models.ForeignKey("billing.Voucher", on_delete=models.CASCADE, related_name="allocations")
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.payment.number} -> {self.voucher.number}: {self.amount}"


def party_balance(party: Party) -> dict:
    """Party ka current outstanding nikalta hai.

    Customer (debtor): opening_DR + sales - receipts  = receivable
    Supplier (creditor): opening_CR + purchases - payments = payable
    """
    from apps.billing.models import Voucher

    opening = Decimal(str(party.opening_balance or 0))
    opening_signed = opening if party.opening_balance_type == "DR" else -opening

    sales = Voucher.objects.filter(party=party, voucher_type="SALE", is_posted=True
                                   ).aggregate(s=Sum("grand_total"))["s"] or Decimal("0")
    sale_ret = Voucher.objects.filter(party=party, voucher_type="SALE_RETURN", is_posted=True
                                      ).aggregate(s=Sum("grand_total"))["s"] or Decimal("0")
    purchases = Voucher.objects.filter(party=party, voucher_type="PURCHASE", is_posted=True
                                       ).aggregate(s=Sum("grand_total"))["s"] or Decimal("0")
    pur_ret = Voucher.objects.filter(party=party, voucher_type="PURCHASE_RETURN", is_posted=True
                                     ).aggregate(s=Sum("grand_total"))["s"] or Decimal("0")
    receipts = Payment.objects.filter(party=party, payment_type="RECEIPT"
                                      ).aggregate(s=Sum("amount"))["s"] or Decimal("0")
    payue = Payment.objects.filter(party=party, payment_type="PAYMENT"
                                   ).aggregate(s=Sum("amount"))["s"] or Decimal("0")

    # +ve = party hum se le chuka / hume dena (receivable); -ve = hume dena hai (payable)
    balance = (opening_signed + sales - sale_ret - receipts) - (purchases - pur_ret - payue)
    return {
        "balance": balance,
        "type": "DR" if balance >= 0 else "CR",
        "label": "To Receive" if balance >= 0 else "To Pay",
        "abs": abs(balance),
    }
