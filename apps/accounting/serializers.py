from rest_framework import serializers
from django.db import transaction
from .models import Account, JournalEntry, JournalLine


class AccountSerializer(serializers.ModelSerializer):
    balance = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = Account
        fields = "__all__"


class JournalLineSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source="account.name", read_only=True, default="")
    account_code = serializers.CharField(source="account.code", read_only=True, default="")

    class Meta:
        model = JournalLine
        fields = ("id", "account", "account_name", "account_code", "debit", "credit", "notes")


class JournalEntrySerializer(serializers.ModelSerializer):
    lines = JournalLineSerializer(many=True)
    total_debit = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    total_credit = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    is_balanced = serializers.BooleanField(read_only=True)

    class Meta:
        model = JournalEntry
        fields = ("id", "date", "narration", "reference", "tags", "lines",
                  "total_debit", "total_credit", "is_balanced")

    def validate(self, data):
        lines = data.get("lines", [])
        from decimal import Decimal
        dr = sum((Decimal(str(l.get("debit", 0) or 0)) for l in lines), Decimal("0"))
        cr = sum((Decimal(str(l.get("credit", 0) or 0)) for l in lines), Decimal("0"))
        if len(lines) < 2:
            raise serializers.ValidationError("Journal mein kam se kam 2 lines chahiye.")
        if dr != cr:
            raise serializers.ValidationError(f"Debit ({dr}) aur Credit ({cr}) barabar hone chahiye.")
        if dr == 0:
            raise serializers.ValidationError("Amount 0 nahi ho sakta.")
        return data

    @transaction.atomic
    def create(self, validated_data):
        lines = validated_data.pop("lines", [])
        je = JournalEntry.objects.create(**validated_data)
        for ln in lines:
            JournalLine.objects.create(journal=je, **ln)
        return je
