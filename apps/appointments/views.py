from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.tenants.tenancy import OrgScopedQuerysetMixin
from .models import Appointment
from .serializers import AppointmentSerializer


class AppointmentViewSet(OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        st = self.request.query_params.get("status")
        when = self.request.query_params.get("when")
        if st:
            qs = qs.filter(status=st)
        if when == "today":
            qs = qs.filter(start__date=timezone.localdate())
        elif when == "upcoming":
            qs = qs.filter(start__gte=timezone.now())
        return qs

    @action(detail=True, methods=["post"])
    def set_status(self, request, pk=None):
        a = self.get_object()
        a.status = (request.data.get("status") or "DONE").upper()
        a.save(update_fields=["status"])
        return Response(AppointmentSerializer(a).data)
