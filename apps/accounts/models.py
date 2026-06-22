from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user with a simple role for RBAC.

    Role-based access — har user ka ek role hota hai jo decide karta hai
    wo kaunse modules/actions use kar sakta hai.
    """

    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin (Owner)"
        ACCOUNTANT = "ACCOUNTANT", "Accountant / Munshi"
        OPERATOR = "OPERATOR", "Billing Operator"
        VIEWER = "VIEWER", "Viewer"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.OPERATOR)
    phone = models.CharField(max_length=15, blank=True)
    organization = models.ForeignKey(
        "tenants.Organization", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="members",
    )

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class AuditLog(models.Model):
    """Har important change ka record — kis user ne kya kiya (compliance + trust)."""
    organization = models.ForeignKey("tenants.Organization", on_delete=models.CASCADE,
                                     null=True, blank=True, related_name="audit_logs")
    user = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=10)   # CREATE / UPDATE / DELETE
    model = models.CharField(max_length=50)
    object_id = models.CharField(max_length=40, blank=True)
    summary = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} {self.model}#{self.object_id} by {self.user}"
