from rest_framework import serializers
from .models import Company, Setting, Unit, TaxRate, Godown


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = "__all__"


class SettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Setting
        fields = "__all__"


class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unit
        fields = "__all__"


class TaxRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxRate
        fields = "__all__"


class GodownSerializer(serializers.ModelSerializer):
    class Meta:
        model = Godown
        fields = "__all__"
