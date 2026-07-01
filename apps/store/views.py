from decimal import Decimal
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.tenants.tenancy import OrgScopedQuerysetMixin, get_current_org
from .models import Order, money
from .serializers import OrderSerializer


class OrderViewSet(OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Order.objects.prefetch_related("items").all()
    serializer_class = OrderSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        st = self.request.query_params.get("status")
        if st:
            qs = qs.filter(status=st)
        return qs

    @action(detail=True, methods=["post"])
    def set_status(self, request, pk=None):
        o = self.get_object()
        o.status = (request.data.get("status") or "CONFIRMED").upper()
        o.save(update_fields=["status"])
        return Response(OrderSerializer(o).data)

    @action(detail=True, methods=["post"])
    def convert_to_invoice(self, request, pk=None):
        """Order se ek DRAFT sale invoice bana deta hai (dukaandar review/post kare)."""
        o = self.get_object()
        if o.voucher_id:
            return Response({"detail": "already converted", "voucher": o.voucher_id}, status=400)
        org = get_current_org()
        try:
            from apps.party.models import Party
            from apps.core.models import Godown
            from apps.billing.models import Voucher, VoucherLine
            # Party — phone se dhundo ya bana do
            party = None
            if o.customer_phone:
                party = Party.objects.filter(phone=o.customer_phone).first()
            if not party:
                party = Party.objects.create(
                    name=o.customer_name or "Online customer",
                    phone=o.customer_phone or "", address=o.customer_address or "",
                    party_type="CUSTOMER")
            godown = Godown.objects.first()
            if not godown:
                return Response({"detail": "Pehle ek godown/store banao (Settings)."}, status=400)
            v = Voucher.objects.create(
                voucher_type="SALE", date=timezone.localdate(), party=party, godown=godown,
                is_posted=False, notes=f"Online order {o.order_no}",
                subtotal=money(o.total), taxable_value=money(o.total), grand_total=money(o.total))
            for it in o.items.all():
                if not it.variant_id:
                    continue
                unit_id = getattr(it.variant.item, "primary_unit_id", None)
                VoucherLine.objects.create(
                    voucher=v, variant=it.variant, unit_id=unit_id,
                    description=it.name, qty=it.qty, rate=it.price,
                    qty_primary=it.qty, gross=money(it.amount),
                    taxable_value=money(it.amount))
            o.voucher = v
            o.party = party
            if o.status == "NEW":
                o.status = "CONFIRMED"
            o.save(update_fields=["voucher", "party", "status"])
            return Response({"ok": True, "voucher": v.id, "number": v.number,
                             "detail": "Draft invoice ban gaya — Sales & Transactions me review/post karo."})
        except Exception as e:
            return Response({"detail": f"Convert nahi hua: {e}"}, status=400)
