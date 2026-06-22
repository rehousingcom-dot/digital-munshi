import calendar
from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from django.db import models
from apps.tenants.tenancy import OrgOwned

TWO = Decimal("0.01")


def money(x):
    return Decimal(str(x)).quantize(TWO, rounding=ROUND_HALF_UP)


class Employee(OrgOwned):
    """Staff member + salary structure (payroll ke liye)."""

    class SalaryType(models.TextChoices):
        MONTHLY = "MONTHLY", "Monthly"
        DAILY = "DAILY", "Daily wage"

    code = models.CharField(max_length=20, blank=True)
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    designation = models.CharField(max_length=80, blank=True)
    department = models.CharField(max_length=80, blank=True)
    joining_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    # Optional app-login link
    user = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
                             related_name="employee_profile")

    # Salary structure
    salary_type = models.CharField(max_length=10, choices=SalaryType.choices, default=SalaryType.MONTHLY)
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    hra = models.DecimalField("HRA", max_digits=12, decimal_places=2, default=0)
    allowances = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                     help_text="Fixed monthly deductions (PF/ESI/PT etc.)")
    working_days = models.PositiveSmallIntegerField(default=30, help_text="Mahine ke standard working days (salary base)")
    paid_leaves_per_month = models.DecimalField(max_digits=4, decimal_places=1, default=0)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def gross_salary(self):
        return self.basic_salary + self.hra + self.allowances

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.code:
            self.code = f"EMP{self.id:04d}"
            super().save(update_fields=["code"])


class Attendance(OrgOwned):
    """Daily attendance — check-in/out + status."""

    class Status(models.TextChoices):
        PRESENT = "PRESENT", "Present"
        ABSENT = "ABSENT", "Absent"
        HALF_DAY = "HALF_DAY", "Half Day"
        LEAVE = "LEAVE", "Leave (paid)"
        HOLIDAY = "HOLIDAY", "Holiday"

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="attendances")
    date = models.DateField()
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PRESENT)
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = ("employee", "date")
        ordering = ["-date"]

    def __str__(self):
        return f"{self.employee.name} {self.date} {self.status}"

    @property
    def day_value(self):
        """Salary calc ke liye din ki value: present/leave=1, half=0.5, baaki 0."""
        if self.status in ("PRESENT", "LEAVE", "HOLIDAY"):
            return Decimal("1")
        if self.status == "HALF_DAY":
            return Decimal("0.5")
        return Decimal("0")


class LeaveRequest(OrgOwned):
    class LeaveType(models.TextChoices):
        CASUAL = "CASUAL", "Casual"
        SICK = "SICK", "Sick"
        PAID = "PAID", "Paid"
        UNPAID = "UNPAID", "Unpaid (LOP)"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="leaves")
    leave_type = models.CharField(max_length=10, choices=LeaveType.choices, default=LeaveType.CASUAL)
    from_date = models.DateField()
    to_date = models.DateField()
    reason = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)

    class Meta:
        ordering = ["-from_date"]

    def __str__(self):
        return f"{self.employee.name} {self.leave_type} {self.from_date}..{self.to_date}"

    @property
    def days(self):
        return (self.to_date - self.from_date).days + 1


class SalarySlip(OrgOwned):
    """Mahine ki payslip — attendance se compute hoti hai."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        FINALIZED = "FINALIZED", "Finalized"
        PAID = "PAID", "Paid"

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="payslips")
    year = models.PositiveIntegerField()
    month = models.PositiveSmallIntegerField()

    working_days = models.PositiveSmallIntegerField(default=30)
    present_days = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    paid_days = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    lop_days = models.DecimalField(max_digits=5, decimal_places=1, default=0)

    earned_basic = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    earned_hra = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    earned_allowances = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gross = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_payable = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    paid_on = models.DateField(null=True, blank=True)
    pay_mode = models.CharField(max_length=10, blank=True)

    class Meta:
        unique_together = ("employee", "year", "month")
        ordering = ["-year", "-month"]

    def __str__(self):
        return f"{self.employee.name} {self.month}/{self.year} — {self.net_payable}"

    @property
    def month_name(self):
        return calendar.month_name[self.month] if 1 <= self.month <= 12 else str(self.month)

    def compute(self, save=True):
        """Attendance + approved paid leaves se salary nikalti hai."""
        emp = self.employee
        wd = self.working_days or emp.working_days or 30
        # Present/paid days attendance se
        atts = Attendance.objects.filter(employee=emp, date__year=self.year, date__month=self.month)
        present = sum((a.day_value for a in atts), Decimal("0"))
        # Approved PAID leaves jo is mahine me aate hain
        paid_leave_days = Decimal("0")
        for lv in LeaveRequest.objects.filter(employee=emp, status="APPROVED", leave_type="PAID"):
            for n in range(lv.days):
                d = lv.from_date.fromordinal(lv.from_date.toordinal() + n)
                if d.year == self.year and d.month == self.month:
                    paid_leave_days += Decimal("1")
        paid_days = min(Decimal(str(wd)), present + paid_leave_days)
        # Agar koi attendance record nahi to full month maan lo (manual override possible)
        if not atts.exists() and paid_leave_days == 0:
            paid_days = Decimal(str(wd))

        ratio = (paid_days / Decimal(str(wd))) if wd else Decimal("0")
        self.present_days = present
        self.paid_days = paid_days
        self.lop_days = max(Decimal("0"), Decimal(str(wd)) - paid_days)
        self.earned_basic = money(emp.basic_salary * ratio)
        self.earned_hra = money(emp.hra * ratio)
        self.earned_allowances = money(emp.allowances * ratio)
        self.gross = money(self.earned_basic + self.earned_hra + self.earned_allowances)
        self.deductions = money(emp.deductions)
        self.net_payable = money(self.gross - self.deductions)
        if save:
            self.save()
