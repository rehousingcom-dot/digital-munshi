from decimal import Decimal
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.tenants.tenancy import OrgScopedQuerysetMixin, get_current_org
from .models import Table, RestOrder, RestOrderItem, money
from .serializers import TableSerializer, RestOrderSerializer


class TableViewSet(OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Table.objects.prefetch_related("orders").all()
    serializer_class = TableSerializer


class RestOrderViewSet(OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = RestOrder.objects.prefetch_related("items").all()
    serializer_class = RestOrderSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        st = self.request.query_params.get("status")
        table = self.request.query_params.get("table")
        if st:
            qs = qs.filter(status=st)
        if table:
            qs = qs.filter(table_id=table)
        return qs

    @action(detail=False, methods=["post"])
    def open_table(self, request):
        """Table pe naya running order (ya existing running lauta do)."""
        table_id = request.data.get("table")
        o = RestOrder.objects.filter(table_id=table_id, status="RUNNING").first()
        if not o:
            o = RestOrder.objects.create(table_id=table_id, guests=request.data.get("guests") or 1)
        return Response(RestOrderSerializer(o).data)

    @action(detail=True, methods=["post"])
    def add_item(self, request, pk=None):
        o = self.get_object()
        RestOrderItem.objects.create(
            order=o, variant_id=request.data.get("variant") or None,
            name=(request.data.get("name") or "Item")[:200],
            price=money(request.data.get("price") or 0),
            qty=Decimal(str(request.data.get("qty") or 1)),
            note=(request.data.get("note") or "")[:120])
        return Response(RestOrderSerializer(o).data)

    @action(detail=True, methods=["post"])
    def remove_item(self, request, pk=None):
        o = self.get_object()
        RestOrderItem.objects.filter(order=o, id=request.data.get("item")).delete()
        return Response(RestOrderSerializer(o).data)

    @action(detail=True, methods=["post"])
    def kot(self, request, pk=None):
        """Naye items ka KOT — kitchen ke liye. Mark kot_sent."""
        o = self.get_object()
        new_items = [i for i in o.items.all() if not i.kot_sent]
        for i in new_items:
            i.kot_sent = True
            i.save(update_fields=["kot_sent"])
        return Response({"order_no": o.order_no, "table": o.table.name if o.table_id else "",
                         "items": [{"name": i.name, "qty": float(i.qty), "note": i.note} for i in new_items],
                         "time": timezone.localtime().strftime("%I:%M %p")})

    @action(detail=True, methods=["post"])
    def settle(self, request, pk=None):
        """Order settle → SALE invoice (draft) ban jaata hai, table free."""
        o = self.get_object()
        if o.voucher_id:
            return Response({"detail": "already billed"}, status=400)
        try:
            from apps.party.models import Party
            from apps.core.models import Godown
            from apps.billing.models import Voucher, VoucherLine
            party = Party.objects.filter(name="Walk-in").first() or Party.objects.create(
                name="Walk-in", party_type="CUSTOMER")
            godown = Godown.objects.first()
            if not godown:
                return Response({"detail": "Pehle ek store/godown banao."}, status=400)
            total = o.total
            v = Voucher.objects.create(
                voucher_type="SALE", date=timezone.localdate(), party=party, godown=godown,
                is_posted=False, notes=f"Restaurant {o.order_no} ({o.table.name if o.table_id else ''})",
                subtotal=total, taxable_value=total, grand_total=total)
            for it in o.items.all():
                unit_id = getattr(it.variant.item, "primary_unit_id", None) if it.variant_id else None
                VoucherLine.objects.create(
                    voucher=v, variant=it.variant, unit_id=unit_id, description=it.name,
                    qty=it.qty, rate=it.price, qty_primary=it.qty,
                    gross=money(it.amount), taxable_value=money(it.amount))
            o.voucher = v
            o.status = "BILLED"
            o.save(update_fields=["voucher", "status"])
            return Response({"ok": True, "voucher": v.id, "number": v.number, "total": str(total),
                             "detail": "Bill ban gaya — Sales & Transactions me hai. Table free."})
        except Exception as e:
            return Response({"detail": f"Settle nahi hua: {e}"}, status=400)
