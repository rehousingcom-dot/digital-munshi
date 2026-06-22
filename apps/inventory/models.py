from decimal import Decimal
from django.db import models
from apps.core.models import Unit, TaxRate, Godown
from apps.tenants.tenancy import OrgOwned


class Category(OrgOwned):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, blank=True, help_text="Item-code prefix, e.g. ELE")

    class Meta:
        verbose_name_plural = "Categories"
        unique_together = ("organization", "name")
        ordering = ["name"]

    def __str__(self):
        return self.name


class Item(OrgOwned):
    """Master product.

    Deck slide 5 requirements:
    - Primary & secondary unit ALAG (separate) + conversion
    - Sale price har unit-size ke liye alag  -> ItemUnitPrice
    - Item code auto + unique (size/colour/model wise)  -> ItemVariant
    - MRP-wise discount (amount/percent) with batches    -> Batch
    - Stock kis godown mein                              -> Stock
    """
    class ItemType(models.TextChoices):
        GOODS = "GOODS", "Goods (stock tracked)"
        SERVICE = "SERVICE", "Service (no stock)"

    name = models.CharField(max_length=200)
    item_type = models.CharField(max_length=10, choices=ItemType.choices, default=ItemType.GOODS)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="items")
    hsn_code = models.CharField("HSN/SAC", max_length=10, blank=True)
    tax_rate = models.ForeignKey(TaxRate, on_delete=models.SET_NULL, null=True, blank=True)
    reorder_level = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                        help_text="Is se kam stock pe low-stock alert (primary unit)")

    # Units: 1 secondary unit = conversion_factor x primary unit
    # Example: 1 BOX (secondary) = 12 PCS (primary)  -> conversion_factor = 12
    primary_unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name="primary_items")
    secondary_unit = models.ForeignKey(
        Unit, on_delete=models.PROTECT, null=True, blank=True, related_name="secondary_items"
    )
    conversion_factor = models.DecimalField(
        max_digits=12, decimal_places=4, default=Decimal("1"),
        help_text="1 secondary unit = kitne primary unit",
    )

    mrp = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    # Combo / Bundle / Manufacturing BOM — yeh item dusre items se bana hai
    is_combo = models.BooleanField(default=False, help_text="Bundle/BOM — components se bana")

    # Custom fields (Swipe-style) — extra item attributes (JSON key/value)
    custom_fields = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        creating = self._state.adding
        super().save(*args, **kwargs)
        # Naya item -> ek default variant auto-banao (billing mein turant use ho sake)
        if creating and not self.variants.exists():
            ItemVariant.objects.create(item=self)

    def to_primary(self, qty, unit):
        """Kisi bhi unit ki quantity ko primary unit mein convert karta hai."""
        qty = Decimal(str(qty))
        if self.secondary_unit_id and unit and unit.id == self.secondary_unit_id:
            return qty * self.conversion_factor
        return qty


class ItemVariant(OrgOwned):
    """Item ka specific variant (size/colour/model wise) — har variant ka
    UNIQUE auto-generated item_code aur barcode. Deck slide 5 & 8.
    """
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="variants")
    size = models.CharField(max_length=30, blank=True)
    colour = models.CharField(max_length=30, blank=True)
    model = models.CharField(max_length=30, blank=True)

    item_code = models.CharField(max_length=40, blank=True)
    barcode = models.CharField(max_length=40, blank=True)

    class Meta:
        unique_together = ("item", "size", "colour", "model")
        ordering = ["id"]

    def __str__(self):
        bits = [self.item.name] + [b for b in (self.size, self.colour, self.model) if b]
        return " / ".join(bits)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)  # pehle id mile
        changed = False
        if not self.item_code:
            prefix = (self.item.category.code if self.item.category and self.item.category.code else "ITM").upper()
            attr = "".join(filter(None, [self.size, self.colour, self.model]))[:6].upper()
            self.item_code = f"{prefix}-{self.id:05d}" + (f"-{attr}" if attr else "")
            changed = True
        if not self.barcode:
            # Simple internal barcode (EAN-like 13 digit). Purchase pe auto-gen (slide 8).
            self.barcode = f"890{self.id:010d}"[:13]
            changed = True
        if changed:
            super().save(update_fields=["item_code", "barcode"])


class ItemUnitPrice(OrgOwned):
    """Sale price har unit-size ke liye alag (deck slide 5 point 3)."""
    variant = models.ForeignKey(ItemVariant, on_delete=models.CASCADE, related_name="unit_prices")
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT)
    sale_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        unique_together = ("variant", "unit")
        ordering = ["id"]

    def __str__(self):
        return f"{self.variant} @ {self.unit}: {self.sale_price}"


class Batch(OrgOwned):
    """Batch-wise MRP & discount (deck slide 5 point 2). Expiry/lot tracking."""
    variant = models.ForeignKey(ItemVariant, on_delete=models.CASCADE, related_name="batches")
    batch_no = models.CharField(max_length=50)
    mrp = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    DISCOUNT_TYPE = (("AMOUNT", "Amount"), ("PERCENT", "Percent"))
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE, default="PERCENT")
    discount_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    expiry_date = models.DateField(null=True, blank=True)
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        unique_together = ("variant", "batch_no")
        ordering = ["id"]

    def __str__(self):
        return f"{self.variant} [{self.batch_no}]"


class ItemComponent(OrgOwned):
    """Combo/Bundle/BOM — parent item kis components se bana (Swipe/Zoho parity).
    Combo bechne pe components ka stock kam hota hai.
    """
    parent = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="components")
    component = models.ForeignKey(ItemVariant, on_delete=models.PROTECT, related_name="used_in")
    quantity = models.DecimalField(max_digits=12, decimal_places=4, default=1,
                                   help_text="Ek combo banane mein kitne component (primary unit)")

    class Meta:
        unique_together = ("parent", "component")
        ordering = ["id"]

    def __str__(self):
        return f"{self.parent.name} ← {self.quantity} x {self.component}"


class SerialNumber(OrgOwned):
    """Serial / IMEI tracking — har piece ka unique number (electronics, mobiles)."""
    class Status(models.TextChoices):
        IN_STOCK = "IN_STOCK", "In Stock"
        SOLD = "SOLD", "Sold"

    variant = models.ForeignKey(ItemVariant, on_delete=models.CASCADE, related_name="serials")
    serial = models.CharField(max_length=80)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.IN_STOCK)
    notes = models.CharField(max_length=120, blank=True)

    class Meta:
        unique_together = ("organization", "serial")
        ordering = ["-id"]

    def __str__(self):
        return f"{self.serial} ({self.status})"


class PriceList(OrgOwned):
    """Named price list — Retail / Wholesale / Distributor etc (Swipe/Zoho parity).
    Billing pe ek price list choose karke uske rates auto-apply hote hain.
    """
    name = models.CharField(max_length=80)
    is_default = models.BooleanField(default=False)

    class Meta:
        unique_together = ("organization", "name")
        ordering = ["name"]

    def __str__(self):
        return self.name


class PriceListItem(OrgOwned):
    """Ek price list mein ek variant ka rate."""
    price_list = models.ForeignKey(PriceList, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(ItemVariant, on_delete=models.CASCADE, related_name="price_list_items")
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        unique_together = ("price_list", "variant")
        ordering = ["id"]

    def __str__(self):
        return f"{self.price_list} · {self.variant}: {self.price}"


class Stock(OrgOwned):
    """Godown-wise quantity (primary unit mein store hoti hai)."""
    variant = models.ForeignKey(ItemVariant, on_delete=models.CASCADE, related_name="stocks")
    godown = models.ForeignKey(Godown, on_delete=models.PROTECT, related_name="stocks")
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.DecimalField(max_digits=14, decimal_places=4, default=0,
                                   help_text="Primary unit mein")

    class Meta:
        unique_together = ("variant", "godown", "batch")
        ordering = ["id"]

    def __str__(self):
        return f"{self.variant} @ {self.godown}: {self.quantity}"
