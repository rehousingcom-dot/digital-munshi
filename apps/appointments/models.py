"""Appointments / services booking — salon, clinic, repair shop ke liye.
Customer ka appointment book karo, staff assign karo, status track karo."""
from django.db import models
from apps.tenants.tenancy import OrgOwned


class Appointment(OrgOwned):
    class Status(models.TextChoices):
        BOOKED = "BOOKED", "Booked"
        DONE = "DONE", "Done"
        CANCELLED = "CANCELLED", "Cancelled"
        NO_SHOW = "NO_SHOW", "No show"

    customer_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=15, blank=True)
    service = models.CharField(max_length=150)
    staff = models.CharField(max_length=80, blank=True)
    start = models.DateTimeField()
    duration_min = models.PositiveSmallIntegerField(default=30)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.BOOKED)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["start"]

    def __str__(self):
        return f"{self.customer_name} — {self.service} @ {self.start}"
