import csv
from io import TextIOWrapper
from django.db.models import Sum
from django.http import HttpResponse
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from apps.tenants.tenancy import OrgScopedQuerysetMixin
from apps.core.models import Unit, TaxRate
from .models import (Category, Item, ItemVariant, ItemUnitPrice, Batch, Stock,
                     PriceList, PriceListItem, ItemComponent, SerialNumber)
from .serializers import (
    CategorySerializer, ItemSerializer, ItemVariantSerializer,
    ItemUnitPriceSerializer, BatchSerializer, StockSerializer,
    PriceListSerializer, PriceListItemSerializer,
    ItemComponentSerializer, SerialNumberSerializer,
)


class ItemComponentViewSet(OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = ItemComponent.objects.all().select_related("component")
    serializer_class = ItemComponentSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        pid = self.request.query_params.get("parent")
        return qs.filter(parent_id=pid) if pid else qs


class SerialNumberViewSet(OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = SerialNumber.objects.all().select_related("variant")
    serializer_class = SerialNumberSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        st = self.request.query_params.get("status")
        return qs.filter(status=st.upper()) if st else qs


class PriceListViewSet(OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = PriceList.objects.all().prefetch_related("items")
    serializer_class = PriceListSerializer


class PriceListItemViewSet(OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = PriceListItem.objects.all()
    serializer_class = PriceListItemSerializer


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def scan(request):
    """Barcode/item-code se item dhoondho — billing screen pe scan ke liye.
    GET /api/scan/?code=8900000000001
    """
    code = (request.query_params.get("code") or "").strip()
    if not code:
        return Response({"detail": "code chahiye"}, status=400)
    v = (ItemVariant.objects.filter(barcode=code).first()
         or ItemVariant.objects.filter(item_code=code).first())
    if not v:
        return Response({"found": False}, status=404)
    price = ItemUnitPrice.objects.filter(variant=v, unit=v.item.primary_unit).first()
    return Response({
        "found": True, "variant_id": v.id, "item": v.item.name,
        "item_code": v.item_code, "barcode": v.barcode,
        "unit": v.item.primary_unit_id, "unit_code": v.item.primary_unit.short_code,
        "sale_price": float(price.sale_price) if price else float(v.item.mrp),
        "mrp": float(v.item.mrp),
        "tax_percent": float(v.item.tax_rate.percent) if v.item.tax_rate else 0,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def items_export(request):
    """Items CSV export."""
    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = 'attachment; filename="items.csv"'
    w = csv.writer(resp)
    w.writerow(["name", "item_type", "hsn_code", "mrp", "reorder_level", "unit", "tax_percent"])
    for it in Item.objects.select_related("primary_unit", "tax_rate").all():
        w.writerow([it.name, it.item_type, it.hsn_code, it.mrp, it.reorder_level,
                    it.primary_unit.short_code if it.primary_unit else "",
                    it.tax_rate.percent if it.tax_rate else ""])
    return resp


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def items_import(request):
    """CSV se items bulk add. Columns: name, mrp, hsn_code, unit(short_code), tax_percent.
    multipart 'file' field."""
    f = request.FILES.get("file")
    if not f:
        return Response({"detail": "CSV file 'file' field me bhejein"}, status=400)
    reader = csv.DictReader(TextIOWrapper(f.file, encoding="utf-8"))
    created = 0
    default_unit = Unit.objects.first()
    for row in reader:
        name = (row.get("name") or "").strip()
        if not name:
            continue
        unit = Unit.objects.filter(short_code=(row.get("unit") or "").strip().upper()).first() or default_unit
        if not unit:
            continue
        tax = None
        tp = (row.get("tax_percent") or "").strip()
        if tp:
            tax = TaxRate.objects.filter(percent=tp).first()
        Item.objects.create(
            name=name, primary_unit=unit, tax_rate=tax,
            hsn_code=(row.get("hsn_code") or "").strip(),
            mrp=row.get("mrp") or 0, reorder_level=row.get("reorder_level") or 0,
        )
        created += 1
    return Response({"created": created})


class CategoryViewSet(OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class ItemViewSet(OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Item.objects.all().prefetch_related("variants")
    serializer_class = ItemSerializer

    @action(detail=True, methods=["post"], parser_classes=[MultiPartParser, FormParser])
    def upload_image(self, request, pk=None):
        """Item photo upload (multipart 'image' field)."""
        item = self.get_object()
        f = request.FILES.get("image")
        if not f:
            return Response({"detail": "image file required"}, status=400)
        item.image = f
        item.save(update_fields=["image"])
        return Response({"image": item.image.url if item.image else None})


class ItemVariantViewSet(OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = ItemVariant.objects.all()
    serializer_class = ItemVariantSerializer


class ItemUnitPriceViewSet(OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = ItemUnitPrice.objects.all()
    serializer_class = ItemUnitPriceSerializer


class BatchViewSet(OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Batch.objects.all()
    serializer_class = BatchSerializer


class StockViewSet(OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Stock.objects.select_related("variant", "godown", "batch").all()
    serializer_class = StockSerializer
