from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.tenants.tenancy import OrgScopedQuerysetMixin
from .models import Payment, party_balance
from .serializers import PaymentSerializer
from apps.party.models import Party


class PaymentViewSet(OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Payment.objects.select_related("party").all()
    serializer_class = PaymentSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        ptype = self.request.query_params.get("type")
        party = self.request.query_params.get("party")
        if ptype:
            qs = qs.filter(payment_type=ptype.upper())
        if party:
            qs = qs.filter(party_id=party)
        return qs

    @action(detail=False, methods=["get"])
    def party_balance(self, request):
        """GET /api/payments/party_balance/?party=<id> -> outstanding."""
        pid = request.query_params.get("party")
        party = Party.objects.filter(pk=pid).first()
        if not party:
            return Response({"error": "party not found"}, status=404)
        bal = party_balance(party)
        return Response({
            "party": party.name,
            "balance": float(bal["abs"]),
            "type": bal["type"],
            "label": bal["label"],
        })
