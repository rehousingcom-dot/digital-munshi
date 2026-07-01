from rest_framework import serializers
from .models import Voucher, VoucherLine, RecurringInvoice


class RecurringInvoiceSerializer(serializers.ModelSerializer):
    party_name = serializers.CharField(source="source_voucher.party.name", read_only=True, default="")
    source_number = serializers.CharField(source="source_voucher.number", read_only=True, default="")
    amount = serializers.DecimalField(source="source_voucher.grand_total", max_digits=14,
                                      decimal_places=2, read_only=True, default=0)

    class Meta:
        model = RecurringInvoice
        fields = "__all__"
        read_only_fields = ("generated_count", "last_generated")


class VoucherLineSerializer(serializers.ModelSerializer):
    variant_name = serializers.SerializerMethodField()

    def get_variant_name(self, obj):
        try:
            v = obj.variant
            it = v.item
            extra = " ".join(x for x in [getattr(v, "size", ""), getattr(v, "colour", ""),
                                         getattr(v, "model", "")] if x)
            return it.name + (f" ({extra})" if extra else "")
        except Exception:
            return ""

    class Meta:
        model = VoucherLine
        fields = "__all__"
        read_only_fields = ("gross", "discount_total", "taxable_value", "cgst",
                            "sgst", "igst", "cess", "tax_amount", "line_total", "voucher")


class VoucherSerializer(serializers.ModelSerializer):
    lines = VoucherLineSerializer(many=True)

    class Meta:
        model = Voucher
        fields = "__all__"
        read_only_fields = ("number", "subtotal", "total_discount", "taxable_value",
                            "cgst", "sgst", "igst", "cess", "total_tax", "round_off",
                            "grand_total", "is_posted")

    def create(self, validated_data):
        lines = validated_data.pop("lines", [])
        voucher = Voucher.objects.create(**validated_data)
        for ln in lines:
            VoucherLine.objects.create(voucher=voucher, **ln)
        voucher.recalculate()
        return voucher

    def update(self, instance, validated_data):
        lines = validated_data.pop("lines", None)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()
        if lines is not None:
            instance.lines.all().delete()
            for ln in lines:
                VoucherLine.objects.create(voucher=instance, **ln)
        instance.recalculate()
        return instance
