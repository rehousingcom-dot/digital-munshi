from rest_framework import serializers
from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "variant", "name", "price", "qty", "amount"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ["id", "order_no", "token", "customer_name", "customer_phone",
                  "customer_address", "note", "status", "total", "party", "voucher",
                  "items", "item_count", "created_at"]

    def get_item_count(self, obj):
        return obj.items.count()
