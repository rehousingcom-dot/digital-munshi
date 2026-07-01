"""Online store orders — customer catalog se cart bana kar order karta hai (login ke
bina). Dukaandar app me order dekhta hai, status update karta hai, aur ek click me
invoice bana sakta hai."""
import uuid
from decimal import Decimal, ROUND_HALF_UP
from django.db import models
from apps.tenants.tenancy import OrgOwned

TWO = Decimal("0.01")


def money(x):
    return Decimal(str(x or 0)).quantize(TWO, rounding=ROUND_HALF_UP)


class Order(OrgOwned):
    class Status(models.TextChoices):
        NEW = "NEW", "New"
        CONFIRMED = "CONFIRMED", "Confirmed"
        PACKED = "PACKED", "Packed"
        DELIVERED = "DELIVERED", "Delivered"
        CANCELLED = "CANCELLED", "Cancelled"

    order_no = models.CharField(max_length=20, blank=True, db_index=True)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    customer_name = models.CharField(max_length=120)
    customer_phone = models.CharField(max_length=15, blank=True)
    customer_address = models.TextField(blank=True)
    note = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.NEW)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    # Links (jab dukaandar action le)
    party = models.ForeignKey("party.Party", on_delete=models.SET_NULL, null=True, blank=True)
    voucher = models.ForeignKey("billing.Voucher", on_delete=models.SET_NULL, null=True, blank=True,
                                related_name="from_order")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.order_no} — {self.customer_name}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.order_no:
            self.order_no = f"ORD{self.id:04d}"
            super().save(update_fields=["order_no"])

    def recompute(self, save=True):
        self.total = money(sum((i.amount for i in self.items.all()), Decimal("0")))
        if save:
            self.save(update_fields=["total"])


class OrderItem(OrgOwned):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey("inventory.ItemVariant", on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    qty = models.DecimalField(max_digits=12, decimal_places=2, default=1)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.name} x {self.qty}"

    @property
    def amount(self):
        return money(self.price * self.qty)
