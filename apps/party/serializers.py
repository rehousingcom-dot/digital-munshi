from rest_framework import serializers
from .models import Party, PartyDocument


class PartyDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PartyDocument
        fields = "__all__"


class PartySerializer(serializers.ModelSerializer):
    documents = PartyDocumentSerializer(many=True, read_only=True)
    state_code = serializers.CharField(read_only=True)
    loyalty_points = serializers.IntegerField(read_only=True)

    class Meta:
        model = Party
        fields = "__all__"
