from django.contrib import admin
from .models import Employee, Attendance, LeaveRequest, SalarySlip


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "designation", "department", "salary_type",
                    "basic_salary", "gross_salary", "is_active")
    search_fields = ("name", "code", "phone")
    list_filter = ("department", "is_active", "salary_type")


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("employee", "date", "status", "check_in", "check_out")
    list_filter = ("status", "date")
    search_fields = ("employee__name",)


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ("employee", "leave_type", "from_date", "to_date", "days", "status")
    list_filter = ("leave_type", "status")


@admin.register(SalarySlip)
class SalarySlipAdmin(admin.ModelAdmin):
    list_display = ("employee", "month", "year", "paid_days", "gross", "deductions",
                    "net_payable", "status")
    list_filter = ("status", "year", "month")
