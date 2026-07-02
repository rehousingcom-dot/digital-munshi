"""Restaurant module — tables + running orders + KOT. Waiter table pe order leta hai,
kitchen ko KOT jaata hai, end me settle karke sale invoice ban jaata hai."""
from decimal import Decimal, ROUND_HALF_UP
from django.db import models
from apps.tenants.tenancy import OrgOwned

TWO = Decimal("0.01")


def money(x):
    return Decimal(str(x or 0)).quantize(TWO, rounding=ROUND_HALF_UP)


class Table(OrgOwned):
    name = models.CharField(max_length=40)          # e.g. T1, Cabin 2
    seats = models.PositiveSmallIntegerField(default=4)
    area = models.CharField(max_length=40, blank=True)  # AC / Garden / Roof
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name

    @property
    def running_order(self):
        return self.orders.filter(status="RUNNING").first()


class RestOrder(OrgOwned):
    class Status(models.TextChoices):
        RUNNING = "RUNNING", "Running"
        BILLED = "BILLED", "Billed"
        CANCELLED = "CANCELLED", "Cancelled"

    table = models.ForeignKey(Table, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name="orders")
    order_no = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.RUNNING)
    guests = models.PositiveSmallIntegerField(default=1)
    note = models.CharField(max_length=200, blank=True)
    voucher = models.ForeignKey("billing.Voucher", on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.order_no} ({self.table.name if self.table_id else '-'})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.order_no:
            self.order_no = f"KOT{self.id:04d}"
            super().save(update_fields=["order_no"])

    @property
    def total(self):
        return money(sum((i.amount for i in self.items.all()), Decimal("0")))


class RestOrderItem(OrgOwned):
    order = models.ForeignKey(RestOrder, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey("inventory.ItemVariant", on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    qty = models.DecimalField(max_digits=8, decimal_places=2, default=1)
    kot_sent = models.BooleanField(default=False)
    note = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.name} x {self.qty}"

    @property
    def amount(self):
        return money(self.price * self.qty)
