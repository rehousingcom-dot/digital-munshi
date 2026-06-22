from rest_framework import serializers
from .models import (Category, Item, ItemVariant, ItemUnitPrice, Batch, Stock,
                     PriceList, PriceListItem, ItemComponent, SerialNumber)


class ItemComponentSerializer(serializers.ModelSerializer):
    component_label = serializers.CharField(source="component.__str__", read_only=True)

    class Meta:
        model = ItemComponent
        fields = "__all__"


class SerialNumberSerializer(serializers.ModelSerializer):
    variant_label = serializers.CharField(source="variant.__str__", read_only=True)

    class Meta:
        model = SerialNumber
        fields = "__all__"


class PriceListItemSerializer(serializers.ModelSerializer):
    variant_label = serializers.CharField(source="variant.__str__", read_only=True)

    class Meta:
        model = PriceListItem
        fields = "__all__"


class PriceListSerializer(serializers.ModelSerializer):
    items = PriceListItemSerializer(many=True, read_only=True)

    class Meta:
        model = PriceList
        fields = "__all__"


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"


class ItemUnitPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemUnitPrice
        fields = "__all__"


class BatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Batch
        fields = "__all__"


class ItemVariantSerializer(serializers.ModelSerializer):
    unit_prices = ItemUnitPriceSerializer(many=True, read_only=True)
    batches = BatchSerializer(many=True, read_only=True)
    item_code = serializers.CharField(read_only=True)
    barcode = serializers.CharField(read_only=True)

    class Meta:
        model = ItemVariant
        fields = "__all__"


class ItemSerializer(serializers.ModelSerializer):
    variants = ItemVariantSerializer(many=True, read_only=True)

    class Meta:
        model = Item
        fields = "__all__"


class StockSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        fields = "__all__"
