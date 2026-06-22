from django.contrib import admin
from .models import Party, PartyDocument


class PartyDocumentInline(admin.TabularInline):
    model = PartyDocument
    extra = 1


@admin.register(Party)
class PartyAdmin(admin.ModelAdmin):
    list_display = ("name", "party_type", "gstin", "phone", "city", "state",
                    "opening_balance", "opening_balance_type", "is_active")
    list_filter = ("party_type", "is_active", "state")
    search_fields = ("name", "legal_name", "gstin", "phone")
    inlines = [PartyDocumentInline]


@admin.register(PartyDocument)
class PartyDocumentAdmin(admin.ModelAdmin):
    list_display = ("party", "title", "created_at")
    search_fields = ("party__name", "title")
