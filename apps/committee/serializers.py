from rest_framework import serializers
from .models import (Committee, CommitteeMember, CommitteeRound, CommitteePayment,
                     CommitteeBid, CommitteeJoinRequest)


class CommitteeSerializer(serializers.ModelSerializer):
    coupon_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    monthly_base = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    members_total = serializers.SerializerMethodField()
    rounds_done = serializers.SerializerMethodField()

    # Optional fields jinhe khali chhoda ja sakta hai -> model default lag jaayega
    _OPTIONAL_BLANK = ["coupon1", "coupon2", "late_fee_per_day", "bid_increment",
                       "members_count", "start_date", "end_date", "open_month",
                       "bid_day", "due_day"]

    class Meta:
        model = Committee
        fields = "__all__"

    def to_internal_value(self, data):
        try:
            data = data.copy()
            for k in self._OPTIONAL_BLANK:
                if k in data and data.get(k) in ("", None):
                    data.pop(k, None)
        except Exception:
            pass
        return super().to_internal_value(data)

    def get_members_total(self, obj):
        return obj.members.count()

    def get_rounds_done(self, obj):
        return obj.rounds.filter(winner__isnull=False).count()


class CommitteeMemberSerializer(serializers.ModelSerializer):
    party_name = serializers.CharField(source="party.name", read_only=True)
    token = serializers.CharField(read_only=True)

    class Meta:
        model = CommitteeMember
        fields = "__all__"


class CommitteeRoundSerializer(serializers.ModelSerializer):
    winner_name = serializers.CharField(source="winner.name", read_only=True)
    due_date = serializers.SerializerMethodField()

    class Meta:
        model = CommitteeRound
        fields = "__all__"
        read_only_fields = ("net_payable", "coupon_total", "collection", "per_head")

    def get_due_date(self, obj):
        d = obj.due_date()
        return d.isoformat() if d else None


class CommitteePaymentSerializer(serializers.ModelSerializer):
    member_name = serializers.CharField(source="member.name", read_only=True)
    month_no = serializers.IntegerField(source="round.month_no", read_only=True)
    status = serializers.CharField(read_only=True)
    total_due = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = CommitteePayment
        fields = "__all__"


class CommitteeBidSerializer(serializers.ModelSerializer):
    member_name = serializers.CharField(source="member.name", read_only=True)

    class Meta:
        model = CommitteeBid
        fields = "__all__"


class CommitteeJoinRequestSerializer(serializers.ModelSerializer):
    committee_name = serializers.CharField(source="committee.name", read_only=True)

    class Meta:
        model = CommitteeJoinRequest
        fields = "__all__"
