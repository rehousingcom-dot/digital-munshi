from rest_framework import serializers
from .models import Table, RestOrder, RestOrderItem


class RestOrderItemSerializer(serializers.ModelSerializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = RestOrderItem
        fields = ["id", "variant", "name", "price", "qty", "kot_sent", "note", "amount"]


class RestOrderSerializer(serializers.ModelSerializer):
    items = RestOrderItemSerializer(many=True, read_only=True)
    total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    table_name = serializers.CharField(source="table.name", read_only=True)

    class Meta:
        model = RestOrder
        fields = ["id", "order_no", "table", "table_name", "status", "guests", "note",
                  "voucher", "items", "total", "created_at"]


class TableSerializer(serializers.ModelSerializer):
    running_order_id = serializers.SerializerMethodField()
    running_total = serializers.SerializerMethodField()

    class Meta:
        model = Table
        fields = ["id", "name", "seats", "area", "is_active", "running_order_id", "running_total"]

    def get_running_order_id(self, obj):
        o = obj.running_order
        return o.id if o else None

    def get_running_total(self, obj):
        o = obj.running_order
        return float(o.total) if o else 0
