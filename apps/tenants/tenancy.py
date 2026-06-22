"""Multi-tenant core: har request ke current organization ko thread-local mein
rakhta hai, aur ek manager + base model deta hai jo data ko automatically
us organization tak hi seemit (scope) kar deta hai.
"""
import threading
from django.db import models

_state = threading.local()


def set_current_org(org):
    _state.org = org


def get_current_org():
    return getattr(_state, "org", None)


def clear_current_org():
    _state.org = None


class TenantManager(models.Manager):
    """Default manager jo queryset ko current organization se filter karta hai.
    Agar koi org set nahi (e.g. Django admin superuser), to sab dikhata hai.
    """

    def get_queryset(self):
        qs = super().get_queryset()
        org = get_current_org()
        if org is not None:
            return qs.filter(organization=org)
        return qs


class OrgScopedQuerysetMixin:
    """DRF viewsets ke liye — har request pe manager se FRESH queryset leta hai
    taaki current organization ka filter lage (class-level queryset import-time
    pe freeze ho jaata hai, isliye yeh zaroori hai). Saath mein audit logging.
    """

    def get_queryset(self):
        return self.queryset.model._default_manager.all()

    def _audit(self, action, instance):
        try:
            from apps.accounts.models import AuditLog
            AuditLog.objects.create(
                organization=get_current_org(),
                user=getattr(self.request, "user", None) if getattr(self.request, "user", None) and self.request.user.is_authenticated else None,
                action=action, model=instance.__class__.__name__,
                object_id=str(getattr(instance, "pk", "")), summary=str(instance)[:255],
            )
        except Exception:
            pass  # audit kabhi main flow ko todna nahi chahiye

    def perform_create(self, serializer):
        obj = serializer.save()
        self._audit("CREATE", obj)

    def perform_update(self, serializer):
        obj = serializer.save()
        self._audit("UPDATE", obj)

    def perform_destroy(self, instance):
        self._audit("DELETE", instance)
        instance.delete()


class OrgOwned(models.Model):
    """Base model — har business record ek organization (tenant) ka hota hai.
    Save pe organization automatically current tenant se set ho jaata hai.
    """
    organization = models.ForeignKey(
        "tenants.Organization", on_delete=models.CASCADE, null=True, blank=True,
        related_name="%(app_label)s_%(class)s_set",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()
    all_objects = models.Manager()  # unscoped (internal/admin use)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.organization_id is None:
            org = get_current_org()
            if org is not None:
                self.organization = org
        super().save(*args, **kwargs)
