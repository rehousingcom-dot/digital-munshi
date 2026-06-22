"""Role-based access control.

Roles (accounts.User.Role):
- ADMIN      : sab kuch (owner)
- ACCOUNTANT : billing, inventory, party, payments, reports — settings bhi
- OPERATOR   : billing/inventory/party (day-to-day) — settings/staff nahi
- VIEWER     : sirf read (koi change nahi)
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS

# In paths ko sirf ADMIN/ACCOUNTANT change kar sakte hain (settings-type)
ADMIN_ONLY_WRITE = ("/api/business-profile", "/api/staff", "/api/companies", "/api/settings")


class RolePermission(BasePermission):
    message = "Aapke role ko is action ki permission nahi hai."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if user.is_superuser or user.is_staff:
            return True
        role = getattr(user, "role", "VIEWER")

        # Read sabko allowed
        if request.method in SAFE_METHODS:
            return True

        # Writes:
        if role == "VIEWER":
            return False
        if role in ("ADMIN", "ACCOUNTANT"):
            return True
        # OPERATOR — settings/staff type endpoints nahi
        if role == "OPERATOR":
            path = request.path
            return not path.startswith(ADMIN_ONLY_WRITE)
        return False
