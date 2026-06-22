from rest_framework import serializers
from .models import Payment, PaymentAllocation


class PaymentAllocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentAllocation
        fields = ("id", "voucher", "amount")


class PaymentSerializer(serializers.ModelSerializer):
    allocations = PaymentAllocationSerializer(many=True, required=False)

    class Meta:
        model = Payment
        fields = "__all__"
        read_only_fields = ("number",)

    def create(self, validated_data):
        allocs = validated_data.pop("allocations", [])
        payment = Payment.objects.create(**validated_data)
        for a in allocs:
            PaymentAllocation.objects.create(payment=payment, **a)
        return payment
