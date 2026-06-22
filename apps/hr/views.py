from datetime import datetime, date as date_cls
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.tenants.tenancy import OrgScopedQuerysetMixin
from .models import Employee, Attendance, LeaveRequest, SalarySlip
from .serializers import (
    EmployeeSerializer, AttendanceSerializer, LeaveRequestSerializer, SalarySlipSerializer,
)


class EmployeeViewSet(OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer


class AttendanceViewSet(OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Attendance.objects.select_related("employee").all()
    serializer_class = AttendanceSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        d = self.request.query_params.get("date")
        emp = self.request.query_params.get("employee")
        if d:
            qs = qs.filter(date=d)
        if emp:
            qs = qs.filter(employee_id=emp)
        return qs

    @action(detail=False, methods=["post"])
    def check_in(self, request):
        """Employee ka check-in mark — aaj ki attendance PRESENT + check-in time."""
        emp = request.data.get("employee")
        d = request.data.get("date") or str(timezone.localdate())
        t = request.data.get("time") or timezone.localtime().strftime("%H:%M")
        att, _ = Attendance.objects.get_or_create(employee_id=emp, date=d,
                                                  defaults={"status": "PRESENT"})
        att.check_in = t
        att.status = "PRESENT"
        att.save()
        return Response(AttendanceSerializer(att).data)

    @action(detail=False, methods=["post"])
    def check_out(self, request):
        emp = request.data.get("employee")
        d = request.data.get("date") or str(timezone.localdate())
        t = request.data.get("time") or timezone.localtime().strftime("%H:%M")
        att, _ = Attendance.objects.get_or_create(employee_id=emp, date=d,
                                                  defaults={"status": "PRESENT"})
        att.check_out = t
        att.save()
        return Response(AttendanceSerializer(att).data)

    @action(detail=False, methods=["post"])
    def mark(self, request):
        """Manual status mark (PRESENT/ABSENT/HALF_DAY/LEAVE/HOLIDAY)."""
        emp = request.data.get("employee")
        d = request.data.get("date") or str(timezone.localdate())
        status_val = request.data.get("status", "PRESENT")
        att, _ = Attendance.objects.update_or_create(
            employee_id=emp, date=d, defaults={"status": status_val})
        return Response(AttendanceSerializer(att).data)


class LeaveRequestViewSet(OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = LeaveRequest.objects.select_related("employee").all()
    serializer_class = LeaveRequestSerializer

    @action(detail=True, methods=["post"])
    def set_status(self, request, pk=None):
        """Leave approve/reject."""
        lv = self.get_object()
        lv.status = (request.data.get("status") or "APPROVED").upper()
        lv.save()
        return Response(LeaveRequestSerializer(lv).data)


class SalarySlipViewSet(OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = SalarySlip.objects.select_related("employee").all()
    serializer_class = SalarySlipSerializer

    @action(detail=False, methods=["post"])
    def generate(self, request):
        """Ek employee ki ek mahine ki payslip generate (attendance se compute).
        body: employee, year, month, working_days(optional)
        """
        emp_id = request.data.get("employee")
        year = int(request.data.get("year"))
        month = int(request.data.get("month"))
        emp = Employee.objects.filter(pk=emp_id).first()
        if not emp:
            return Response({"detail": "employee not found"}, status=404)
        slip, _ = SalarySlip.objects.get_or_create(
            employee=emp, year=year, month=month,
            defaults={"working_days": request.data.get("working_days") or emp.working_days})
        if request.data.get("working_days"):
            slip.working_days = int(request.data["working_days"])
        slip.compute()
        return Response(SalarySlipSerializer(slip).data)

    @action(detail=False, methods=["post"])
    def generate_all(self, request):
        """Saare active employees ki ek mahine ki payslip ek saath generate."""
        year = int(request.data.get("year"))
        month = int(request.data.get("month"))
        out = []
        for emp in Employee.objects.filter(is_active=True):
            slip, _ = SalarySlip.objects.get_or_create(
                employee=emp, year=year, month=month, defaults={"working_days": emp.working_days})
            slip.compute()
            out.append(SalarySlipSerializer(slip).data)
        return Response({"count": len(out), "payslips": out})

    @action(detail=True, methods=["post"])
    def mark_paid(self, request, pk=None):
        slip = self.get_object()
        slip.status = "PAID"
        slip.paid_on = request.data.get("paid_on") or timezone.localdate()
        slip.pay_mode = request.data.get("pay_mode", "BANK")
        slip.save()
        return Response(SalarySlipSerializer(slip).data)
