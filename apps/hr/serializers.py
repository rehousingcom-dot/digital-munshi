from rest_framework import serializers
from .models import Employee, Attendance, LeaveRequest, SalarySlip


class EmployeeSerializer(serializers.ModelSerializer):
    gross_salary = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    code = serializers.CharField(read_only=True)

    class Meta:
        model = Employee
        fields = "__all__"


class AttendanceSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.name", read_only=True)

    class Meta:
        model = Attendance
        fields = "__all__"


class LeaveRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.name", read_only=True)
    days = serializers.IntegerField(read_only=True)

    class Meta:
        model = LeaveRequest
        fields = "__all__"


class SalarySlipSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.name", read_only=True)
    month_name = serializers.CharField(read_only=True)

    class Meta:
        model = SalarySlip
        fields = "__all__"
        read_only_fields = ("present_days", "paid_days", "lop_days", "earned_basic",
                            "earned_hra", "earned_allowances", "gross", "net_payable")
