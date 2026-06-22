from rest_framework import viewsets, serializers, mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.tenants.tenancy import get_current_org
from .models import AuditLog, User


class StaffSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ("id", "username", "email", "role", "phone", "is_active", "password")


class StaffViewSet(viewsets.ModelViewSet):
    """Owner apne business ke staff users banaye/manage kare (Admin/Accountant/Operator/Viewer).
    Sirf ADMIN role (ya platform staff) access kar sakta hai — RolePermission se enforce.
    """
    serializer_class = StaffSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        org = get_current_org()
        return (User.objects.filter(organization=org).exclude(is_superuser=True).order_by("username")
                if org else User.objects.none())

    def _is_admin(self, request):
        u = request.user
        return u.is_staff or u.is_superuser or getattr(u, "role", "") == "ADMIN"

    def _limit_info(self, org):
        """Plan ke hisaab se user limit + current usage."""
        sub = getattr(org, "subscription", None)
        plan = getattr(sub, "plan", None)
        max_users = int(getattr(plan, "max_users", 0) or 0)
        used = User.objects.filter(organization=org).exclude(is_superuser=True).count()
        return used, max_users, (getattr(plan, "name", "") or "")

    @action(detail=False, methods=["get"])
    def meta(self, request):
        """Frontend ke liye: kitne users add ho chuke / plan limit."""
        org = get_current_org()
        used, max_users, plan_name = self._limit_info(org) if org else (0, 0, "")
        return Response({"used": used, "max_users": max_users, "plan": plan_name,
                         "can_add": max_users == 0 or used < max_users})

    def create(self, request, *args, **kwargs):
        if not self._is_admin(request):
            return Response({"detail": "Sirf Admin staff add kar sakta hai."}, status=403)
        org = get_current_org()
        used, max_users, plan_name = self._limit_info(org)
        if max_users and used >= max_users:
            return Response({"detail": f"Aapke '{plan_name}' plan mein max {max_users} users allowed hain "
                                        f"({used} use ho chuke). Zyada users ke liye plan upgrade karein."},
                            status=403)
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        if User.objects.filter(username=ser.validated_data.get("username")).exists():
            return Response({"detail": "Yeh username pehle se exist karta hai — dusra naam chunein."}, status=400)
        pwd = ser.validated_data.pop("password", None) or User.objects.make_random_password()
        user = User(organization=org, **ser.validated_data)
        user.set_password(pwd)
        user.save()
        out = StaffSerializer(user).data
        out["temp_password"] = pwd
        return Response(out, status=201)

    def update(self, request, *args, **kwargs):
        if not self._is_admin(request):
            return Response({"detail": "Sirf Admin edit kar sakta hai."}, status=403)
        instance = self.get_object()
        pwd = request.data.get("password")
        ser = self.get_serializer(instance, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        if pwd:
            instance.set_password(pwd); instance.save()
        return Response(self.get_serializer(instance).data)


class AuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.username", default="", read_only=True)

    class Meta:
        model = AuditLog
        fields = ("id", "action", "model", "object_id", "summary", "user_name", "created_at")


class AuditLogViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """Read-only — current org ke audit logs (admin/accountant dekh sakte hain)."""
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        org = get_current_org()
        return AuditLog.objects.filter(organization=org) if org else AuditLog.objects.none()
