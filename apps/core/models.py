from django.db import models
from apps.tenants.tenancy import OrgOwned
from .business_presets import BUSINESS_TYPES, preset_for


class TimeStamped(models.Model):
    """Base model — har record mein created/updated time. Reuse everywhere."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Company(OrgOwned):
    """Business / firm details (GST entity) + business profile/settings.
    Deck slide 2: 'all changes for any type from setting option.'
    """

    class GSTScheme(models.TextChoices):
        REGULAR = "REGULAR", "Regular (GST charge)"
        COMPOSITION = "COMPOSITION", "Composition (Bill of Supply)"
        UNREGISTERED = "UNREGISTERED", "Unregistered / No GST"

    name = models.CharField(max_length=200)
    legal_name = models.CharField(max_length=200, blank=True)
    gstin = models.CharField("GSTIN", max_length=15, blank=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    state = models.CharField(max_length=50, blank=True)
    state_code = models.CharField(max_length=2, blank=True, help_text="GST state code (intra/inter-state)")
    is_active = models.BooleanField(default=True)

    # Business profile
    business_type = models.CharField(max_length=20, choices=BUSINESS_TYPES, default="GENERAL")
    gst_scheme = models.CharField(max_length=15, choices=GSTScheme.choices, default=GSTScheme.REGULAR)

    # ---- Item Settings (Vyapar-style granular toggles) ----
    sell_type = models.CharField(max_length=10, default="BOTH",
                                 help_text="PRODUCT / SERVICE / BOTH")
    enable_stock_maintenance = models.BooleanField(default=True)
    enable_manufacturing = models.BooleanField(default=False)
    show_low_stock_dialog = models.BooleanField(default=True)
    enable_item_category = models.BooleanField(default=True)
    enable_default_unit = models.BooleanField(default=False)
    party_wise_rate = models.BooleanField(default=False)
    enable_description = models.BooleanField(default=False)
    item_wise_tax = models.BooleanField(default=True)
    item_wise_discount = models.BooleanField(default=True)
    update_sale_price_from_transaction = models.BooleanField(default=False)
    quantity_decimals = models.PositiveSmallIntegerField(default=2)
    enable_wholesale_price = models.BooleanField(default=False)

    # MRP / Price
    enable_mrp = models.BooleanField(default=True)
    calculate_tax_on_mrp = models.BooleanField(default=False)

    # Tracking
    enable_batch = models.BooleanField(default=True)
    enable_exp_date = models.BooleanField(default=False)
    enable_mfg_date = models.BooleanField(default=False)
    enable_model_no = models.BooleanField(default=False)
    enable_size = models.BooleanField(default=False)
    enable_godown = models.BooleanField(default=True)
    enable_barcode = models.BooleanField(default=True)
    enable_serial = models.BooleanField(default=False)
    default_price_inclusive = models.BooleanField(default=False, help_text="MRP/inclusive billing")
    negative_stock_allowed = models.BooleanField(default=True)
    default_item_type = models.CharField(max_length=10, default="GOODS")

    # Invoice preferences
    invoice_prefix = models.CharField(max_length=10, blank=True, default="")
    terms = models.TextField(blank=True, help_text="Invoice ke neeche terms & conditions")
    logo = models.ImageField(upload_to="company_logos/", blank=True, null=True)
    signature = models.ImageField(upload_to="company_signatures/", blank=True, null=True,
                                  help_text="Authorised signatory — invoice par print hoga")

    # WhatsApp sharing
    whatsapp_enabled = models.BooleanField(default=True)
    whatsapp_business_number = models.CharField(max_length=15, blank=True,
                                                help_text="Aapka WhatsApp number (countrycode ke saath, e.g. 9198...)")
    whatsapp_api_token = models.CharField(max_length=255, blank=True,
                                          help_text="(Optional) WhatsApp Business Cloud API token — auto-send ke liye")
    whatsapp_phone_id = models.CharField(max_length=40, blank=True,
                                         help_text="WhatsApp Cloud API Phone Number ID")

    class Meta:
        verbose_name_plural = "Companies"

    def __str__(self):
        return self.name

    def apply_business_type(self, business_type):
        """Type ke hisaab se default toggles set karta hai."""
        self.business_type = business_type
        for k, v in preset_for(business_type).items():
            setattr(self, k, v)

    @property
    def charges_gst(self):
        return self.gst_scheme == self.GSTScheme.REGULAR


class Setting(OrgOwned):
    """Settings-driven design — deck slide 2: 'All changes will be from setting option.'
    Key-value store so naye options bina code change ke add ho sakein.
    """
    key = models.CharField(max_length=100)
    value = models.JSONField(default=dict, blank=True)
    label = models.CharField(max_length=200, blank=True)
    group = models.CharField(max_length=50, blank=True, help_text="e.g. billing, inventory, tax")

    class Meta:
        unique_together = ("organization", "key")
        ordering = ["key"]

    def __str__(self):
        return self.key


class Unit(OrgOwned):
    """Measurement unit — PCS, BOX, KG, etc. Primary/secondary unit support
    inventory module mein conversion ke through hota hai.
    """
    name = models.CharField(max_length=50)
    short_code = models.CharField(max_length=10)
    allow_decimal = models.BooleanField(default=False, help_text="KG/Litre ke liye True")

    class Meta:
        unique_together = (("organization", "short_code"), ("organization", "name"))
        ordering = ["short_code"]

    def __str__(self):
        return self.short_code


class TaxRate(OrgOwned):
    """GST tax slabs — 0/5/12/18/28%. Item se link hota hai."""
    name = models.CharField(max_length=50)
    percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["percent"]

    def __str__(self):
        return f"{self.name} ({self.percent}%)"


class Godown(OrgOwned):
    """Storage location / warehouse — deck slide 5: 'stock will be store which godown.'"""
    name = models.CharField(max_length=100)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("organization", "name")
        ordering = ["name"]

    def __str__(self):
        return self.name
