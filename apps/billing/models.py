import uuid
from decimal import Decimal, ROUND_HALF_UP
from django.db import models
from django.db import transaction as db_transaction
from apps.core.models import Unit, Godown
from apps.inventory.models import ItemVariant, Batch, Stock, ItemUnitPrice
from apps.party.models import Party
from apps.tenants.tenancy import OrgOwned

TWO = Decimal("0.01")


def money(x):
    return Decimal(str(x)).quantize(TWO, rounding=ROUND_HALF_UP)


class Voucher(OrgOwned):
    """Sale / Purchase transaction header.

    Deck slides 6-8: multi-unit billing, multi-level discount on without-tax
    amount, item-wise + transaction-wise tax, auto barcode (purchase),
    margin-based sale price (purchase).
    """

    class Type(models.TextChoices):
        SALE = "SALE", "Sale Invoice"
        PURCHASE = "PURCHASE", "Purchase"
        SALE_RETURN = "SALE_RETURN", "Sale Return"
        PURCHASE_RETURN = "PURCHASE_RETURN", "Purchase Return"
        ESTIMATE = "ESTIMATE", "Estimate / Quotation"
        PROFORMA = "PROFORMA", "Proforma Invoice"
        SALE_ORDER = "SALE_ORDER", "Sale Order"
        DELIVERY_CHALLAN = "DELIVERY_CHALLAN", "Delivery Challan"
        CREDIT_NOTE = "CREDIT_NOTE", "Credit Note"
        DEBIT_NOTE = "DEBIT_NOTE", "Debit Note"

    # Stock pe effect: +1 stock badhega, -1 ghatega, 0 koi asar nahi
    STOCK_EFFECT = {
        "PURCHASE": 1, "SALE_RETURN": 1, "CREDIT_NOTE": 1,
        "SALE": -1, "PURCHASE_RETURN": -1, "DEBIT_NOTE": -1, "DELIVERY_CHALLAN": -1,
        "ESTIMATE": 0, "PROFORMA": 0, "SALE_ORDER": 0,
    }

    voucher_type = models.CharField(max_length=20, choices=Type.choices, default=Type.SALE)
    number = models.CharField(max_length=30, blank=True, db_index=True)
    date = models.DateField()
    party = models.ForeignKey(Party, on_delete=models.PROTECT, related_name="vouchers")
    godown = models.ForeignKey(Godown, on_delete=models.PROTECT, related_name="vouchers")

    notes = models.TextField(blank=True)
    is_posted = models.BooleanField(default=False, help_text="Stock update ho chuka?")
    share_uuid = models.UUIDField(default=uuid.uuid4, editable=False,
                                  help_text="Public share link ke liye (token leak ke bina)")

    # Computed totals (transaction-wise) — deck slide 7
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)   # gross before discount
    total_discount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    taxable_value = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    cgst = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    sgst = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    igst = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    cess = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_tax = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    round_off = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    # Company state code (intra/inter-state decide karne ke liye)
    company_state_code = models.CharField(max_length=2, blank=True, default="")

    # Multi-currency (export/SEZ) — base INR, foreign currency display
    currency = models.CharField(max_length=5, default="INR")
    exchange_rate = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal("1"),
                                        help_text="1 foreign currency = ? INR")

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"{self.get_voucher_type_display()} {self.number}"

    @property
    def is_inter_state(self):
        """Party aur company alag state -> IGST; same state -> CGST+SGST."""
        cs = (self.company_state_code or "").strip()
        ps = (self.party.state_code or "").strip()
        if cs and ps:
            return cs != ps
        return False  # default intra-state

    def _next_number(self):
        prefix = {"SALE": "INV", "PURCHASE": "P", "SALE_RETURN": "SR",
                  "PURCHASE_RETURN": "PR", "ESTIMATE": "EST", "PROFORMA": "PI",
                  "SALE_ORDER": "SO", "DELIVERY_CHALLAN": "DC",
                  "CREDIT_NOTE": "CN", "DEBIT_NOTE": "DN"}.get(self.voucher_type, "V")
        last = Voucher.objects.filter(voucher_type=self.voucher_type).exclude(pk=self.pk).count()
        return f"{prefix}/{last + 1:05d}"

    def save(self, *args, **kwargs):
        if not self.number:
            super().save(*args, **kwargs)
            self.number = self._next_number()
            return super().save(update_fields=["number"])
        super().save(*args, **kwargs)

    @property
    def is_bill_of_supply(self):
        """Composition/unregistered business -> GST nahi lagta, Bill of Supply banta hai."""
        from apps.core.models import Company
        company = Company.objects.filter(is_active=True).first()
        return bool(company and not company.charges_gst)

    def recalculate(self, save=True):
        """Saari lines compute karke header totals nikalta hai."""
        inter = self.is_inter_state
        charge_tax = not self.is_bill_of_supply
        sub = disc = taxable = cgst = sgst = igst = cess = Decimal("0")
        for line in self.lines.all():
            line.compute(inter_state=inter, charge_tax=charge_tax, save=True)
            sub += line.gross
            disc += line.discount_total
            taxable += line.taxable_value
            cgst += line.cgst
            sgst += line.sgst
            igst += line.igst
            cess += line.cess
        total_tax = cgst + sgst + igst + cess
        before_round = taxable + total_tax
        grand = before_round.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        self.subtotal = money(sub)
        self.total_discount = money(disc)
        self.taxable_value = money(taxable)
        self.cgst, self.sgst, self.igst = money(cgst), money(sgst), money(igst)
        self.cess = money(cess)
        self.total_tax = money(total_tax)
        self.round_off = money(grand - before_round)
        self.grand_total = money(grand)
        if save:
            self.save(update_fields=[
                "subtotal", "total_discount", "taxable_value", "cgst", "sgst",
                "igst", "cess", "total_tax", "round_off", "grand_total",
            ])

    @db_transaction.atomic
    def post(self):
        """Stock update karta hai (voucher type ke hisaab se +/-).
        - SERVICE items pe stock asar nahi (services/restaurant).
        - ESTIMATE pe koi stock movement nahi (sirf quote).
        - Purchase pe: barcode auto + sale price margin se set.
        """
        if self.is_posted:
            return
        from apps.core.models import Company
        company = Company.objects.filter(is_active=True).first()
        allow_negative = company.negative_stock_allowed if company else True

        effect = self.STOCK_EFFECT.get(self.voucher_type, 0)

        def _move(variant, qty_primary):
            stock, _ = Stock.objects.get_or_create(
                variant=variant, godown=self.godown, batch=None,
                defaults={"quantity": Decimal("0")})
            new_qty = stock.quantity + Decimal(str(effect)) * qty_primary
            if effect < 0 and new_qty < 0 and not allow_negative:
                raise ValueError(
                    f"'{variant.item.name}' ka stock kam hai "
                    f"(available {stock.quantity}, chahiye {qty_primary}). "
                    f"Negative stock settings se allow karein ya stock badhayein.")
            stock.quantity = new_qty
            stock.save(update_fields=["quantity"])

        for line in self.lines.all():
            item = line.variant.item
            if effect != 0 and item.item_type != "SERVICE":
                qty_primary = item.to_primary(
                    Decimal(str(line.qty or 0)) + Decimal(str(line.free_qty or 0)), line.unit)
                if item.is_combo:
                    # Combo/BOM — components ka stock kam karo (combo ka apna stock nahi)
                    for comp in item.components.all():
                        _move(comp.component, Decimal(str(comp.quantity)) * qty_primary)
                else:
                    stock, _ = Stock.objects.get_or_create(
                        variant=line.variant, godown=self.godown, batch=line.batch,
                        defaults={"quantity": Decimal("0")})
                    new_qty = stock.quantity + Decimal(str(effect)) * qty_primary
                    if effect < 0 and new_qty < 0 and not allow_negative:
                        raise ValueError(
                            f"'{item.name}' ka stock kam hai "
                            f"(available {stock.quantity}, chahiye {qty_primary}). "
                            f"Negative stock settings se allow karein ya stock badhayein.")
                    stock.quantity = new_qty
                    stock.save(update_fields=["quantity"])
            if self.voucher_type == "PURCHASE":
                line.apply_purchase_pricing()
        self.is_posted = True
        self.save(update_fields=["is_posted"])

    def convert_to(self, new_type):
        """Estimate/Challan ko Sale Invoice mein convert karta hai (lines copy)."""
        new_v = Voucher.objects.create(
            voucher_type=new_type, date=self.date, party=self.party,
            godown=self.godown, company_state_code=self.company_state_code,
            notes=f"Converted from {self.number}",
        )
        for ln in self.lines.all():
            ln.pk = None
            ln.id = None
            ln.voucher = new_v
            ln.save()
        new_v.recalculate()
        return new_v


class VoucherLine(OrgOwned):
    """Ek transaction line — deck slide 7 ki saari calculations yahin."""
    voucher = models.ForeignKey(Voucher, on_delete=models.CASCADE, related_name="lines")
    variant = models.ForeignKey(ItemVariant, on_delete=models.PROTECT)
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, help_text="Kisi bhi unit se billing")
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.CharField(max_length=255, blank=True, help_text="Line description / note (invoice par print)")

    qty = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    rate = models.DecimalField(max_digits=14, decimal_places=2, default=0, help_text="Price per selected unit")
    price_inclusive_tax = models.BooleanField(default=False, help_text="Rate tax ke saath hai? (with/without tax)")

    # Multi-level discount (deck slide 7) — sab WITHOUT-TAX amount pe apply hote hain
    disc1_pct = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    disc2_pct = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    disc3_pct = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    tax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    cess_percent = models.DecimalField(max_digits=6, decimal_places=2, default=0,
                                       help_text="Additional CESS % (e.g. tobacco, auto)")
    free_qty = models.DecimalField(max_digits=14, decimal_places=4, default=0,
                                   help_text="Free quantity (stock se nikalti, charge nahi)")

    # Purchase only: sale price margin (deck slide 8)
    margin_type = models.CharField(max_length=10, blank=True,
                                   choices=(("AMOUNT", "Amount"), ("PERCENT", "Percent")))
    margin_value = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    # Computed (stored)
    qty_primary = models.DecimalField(max_digits=14, decimal_places=4, default=0,
                                      help_text="Quantity primary unit mein (reporting ke liye)")
    gross = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    discount_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    taxable_value = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    cgst = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    sgst = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    igst = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    cess = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.variant} x {self.qty} {self.unit}"

    def qty_in_primary(self):
        return self.variant.item.to_primary(self.qty, self.unit)

    def compute(self, inter_state=False, charge_tax=True, save=True):
        qty = Decimal(str(self.qty or 0))
        rate = Decimal(str(self.rate or 0))
        taxp = Decimal(str(self.tax_percent or 0)) if charge_tax else Decimal("0")
        gross = rate * qty

        # 1. Without-tax base nikaalo (agar rate inclusive hai to back-calc)
        if self.price_inclusive_tax and taxp > 0:
            base = gross / (Decimal("1") + taxp / Decimal("100"))
        else:
            base = gross

        # 2. Discounts SEQUENTIALLY without-tax amount pe (deck slide 7)
        after = base
        for d in (self.disc1_pct, self.disc2_pct, self.disc3_pct):
            d = Decimal(str(d or 0))
            if d:
                after = after * (Decimal("1") - d / Decimal("100"))
        after = after - Decimal(str(self.discount_amount or 0))
        if after < 0:
            after = Decimal("0")

        taxable = after
        tax_amount = taxable * taxp / Decimal("100")
        # Additional CESS — taxable pe alag se (GST CESS)
        cess_p = Decimal(str(self.cess_percent or 0)) if charge_tax else Decimal("0")
        cess = taxable * cess_p / Decimal("100")

        # 3. Tax split — intra-state CGST+SGST, inter-state IGST
        if inter_state:
            igst = tax_amount
            cgst = sgst = Decimal("0")
        else:
            cgst = sgst = tax_amount / Decimal("2")
            igst = Decimal("0")

        self.qty_primary = self.qty_in_primary()
        self.gross = money(gross)
        self.discount_total = money(base - taxable)
        self.taxable_value = money(taxable)
        self.cgst, self.sgst, self.igst = money(cgst), money(sgst), money(igst)
        self.cess = money(cess)
        self.tax_amount = money(tax_amount)
        self.line_total = money(taxable + tax_amount + cess)
        if save:
            self.save(update_fields=[
                "qty_primary", "gross", "discount_total", "taxable_value", "cgst",
                "sgst", "igst", "cess", "tax_amount", "line_total",
            ])

    def apply_purchase_pricing(self):
        """Purchase pe sale price = cost + margin (amount/percent). Deck slide 8.
        Net cost per primary unit nikaal ke ItemUnitPrice update karta hai.
        """
        if not self.margin_type or not self.qty:
            return
        qty_primary = self.qty_in_primary() or Decimal("1")
        cost_per_primary = (self.taxable_value / qty_primary) if qty_primary else Decimal("0")
        if self.margin_type == "PERCENT":
            sale = cost_per_primary * (Decimal("1") + Decimal(str(self.margin_value)) / Decimal("100"))
        else:
            sale = cost_per_primary + Decimal(str(self.margin_value))
        primary_unit = self.variant.item.primary_unit
        ItemUnitPrice.objects.update_or_create(
            variant=self.variant, unit=primary_unit,
            defaults={"sale_price": money(sale), "purchase_price": money(cost_per_primary)},
        )


class RecurringInvoice(OrgOwned):
    """Subscription / recurring invoice — ek source invoice ko schedule pe
    auto-generate karta hai (Zoho/Swipe parity). Movers ke monthly contracts,
    rent, AMC etc ke liye.
    """
    class Frequency(models.TextChoices):
        WEEKLY = "WEEKLY", "Weekly"
        MONTHLY = "MONTHLY", "Monthly"
        QUARTERLY = "QUARTERLY", "Quarterly"
        YEARLY = "YEARLY", "Yearly"

    name = models.CharField(max_length=120, help_text="e.g. 'Sharma Ji - Monthly AMC'")
    source_voucher = models.ForeignKey(Voucher, on_delete=models.CASCADE, related_name="recurrences",
                                       help_text="Is invoice ko template ki tarah clone karta hai")
    frequency = models.CharField(max_length=10, choices=Frequency.choices, default=Frequency.MONTHLY)
    start_date = models.DateField()
    next_run = models.DateField()
    end_date = models.DateField(null=True, blank=True, help_text="Khaali = chalta rahega")
    is_active = models.BooleanField(default=True)
    auto_post = models.BooleanField(default=True, help_text="Generate ke saath stock bhi post ho")
    generated_count = models.PositiveIntegerField(default=0)
    last_generated = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["next_run"]

    def __str__(self):
        return f"{self.name} ({self.get_frequency_display()})"

    def _advance(self, d):
        from datetime import timedelta
        if self.frequency == "WEEKLY":
            return d + timedelta(days=7)
        # month-based: add months safely
        months = {"MONTHLY": 1, "QUARTERLY": 3, "YEARLY": 12}.get(self.frequency, 1)
        m = d.month - 1 + months
        year = d.year + m // 12
        month = m % 12 + 1
        import calendar
        day = min(d.day, calendar.monthrange(year, month)[1])
        return d.replace(year=year, month=month, day=day)

    def due(self, today=None):
        from django.utils import timezone
        today = today or timezone.localdate()
        if not self.is_active:
            return False
        if self.end_date and self.next_run > self.end_date:
            return False
        return self.next_run <= today

    def generate_one(self):
        """Source invoice clone karke naya Voucher banata hai, next_run advance."""
        from django.utils import timezone
        src = self.source_voucher
        new_v = Voucher.objects.create(
            voucher_type="SALE", date=self.next_run, party=src.party,
            godown=src.godown, company_state_code=src.company_state_code,
            notes=f"Recurring: {self.name}",
        )
        for ln in src.lines.all():
            ln.pk = None
            ln.id = None
            ln.voucher = new_v
            ln.save()
        new_v.recalculate()
        if self.auto_post:
            try:
                new_v.post()
            except Exception:
                pass
        self.generated_count += 1
        self.last_generated = self.next_run
        self.next_run = self._advance(self.next_run)
        self.save(update_fields=["generated_count", "last_generated", "next_run"])
        return new_v
