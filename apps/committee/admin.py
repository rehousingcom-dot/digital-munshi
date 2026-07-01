from django.contrib import admin
from .models import Committee, CommitteeMember, CommitteeRound, CommitteePayment


@admin.register(Committee)
class CommitteeAdmin(admin.ModelAdmin):
    list_display = ("name", "total_value", "members_count", "status", "start_date")
    list_filter = ("status",)
    search_fields = ("name",)


@admin.register(CommitteeMember)
class CommitteeMemberAdmin(admin.ModelAdmin):
    list_display = ("name", "committee", "phone")
    search_fields = ("name", "phone")


@admin.register(CommitteeRound)
class CommitteeRoundAdmin(admin.ModelAdmin):
    list_display = ("committee", "month_no", "date", "winner", "bid_amount",
                    "net_payable", "per_head")
    list_filter = ("committee",)


@admin.register(CommitteePayment)
class CommitteePaymentAdmin(admin.ModelAdmin):
    list_display = ("round", "member", "amount_due", "amount_paid", "late_fee", "paid_on")
    list_filter = ("round__committee",)
