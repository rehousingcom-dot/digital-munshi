"""Supplier Network — B2B marketplace ka beej.
Dukaandar apne aap ko supplier/wholesaler ke roop me list kar sakte hain; doosre
retailer unhe dhundh kar enquiry/order bhej sakte hain. Ye cross-tenant hai
(sab organizations ki listing ek jagah), isliye ye models tenant-scoped NAHI hain —
directory publicly queryable hai.
"""
from django.db import models
from apps.tenants.models import Organization

CATEGORIES = [
    ("kirana", "Kirana / Grocery"),
    ("wholesale", "Wholesale / Distributor"),
    ("pharmacy", "Pharmacy / Medical"),
    ("garment", "Garment / Textile"),
    ("hardware", "Hardware / Sanitary"),
    ("electronics", "Electronics / Mobile"),
    ("restaurant", "Restaurant / Food supplies"),
    ("stationery", "Stationery / Books"),
    ("cosmetics", "Cosmetics / General"),
    ("agri", "Agri / Seeds / Fertilizer"),
    ("other", "Other"),
]


class SupplierProfile(models.Model):
    organization = models.OneToOneField(Organization, on_delete=models.CASCADE,
                                        related_name="supplier_profile")
    is_listed = models.BooleanField(default=False)
    display_name = models.CharField(max_length=200, blank=True)
    category = models.CharField(max_length=30, choices=CATEGORIES, default="wholesale")
    city = models.CharField(max_length=80, blank=True)
    state = models.CharField(max_length=80, blank=True)
    about = models.TextField(blank=True)
    whatsapp = models.CharField(max_length=15, blank=True)
    min_order = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.display_name or self.organization.name

    @property
    def name(self):
        return self.display_name or self.organization.name


class SupplierEnquiry(models.Model):
    class Status(models.TextChoices):
        NEW = "NEW", "New"
        CONTACTED = "CONTACTED", "Contacted"
        CLOSED = "CLOSED", "Closed"

    supplier = models.ForeignKey(Organization, on_delete=models.CASCADE,
                                 related_name="supplier_enquiries")
    from_org = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="sent_enquiries")
    from_name = models.CharField(max_length=120)
    from_phone = models.CharField(max_length=15, blank=True)
    message = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.NEW)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.from_name} → {self.supplier.name}"
