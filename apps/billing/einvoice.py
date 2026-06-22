"""E-Invoice (IRN) aur E-Way Bill ke liye government-schema JSON banata hai.

NOTE: Yeh JSON **ready-to-upload** hota hai. Asli IRN/QR generate karne ke liye
GSP/NIC API (credentials) chahiye — woh integration baad mein plug hoga. Abhi yeh
JSON aap government portal / GSP pe upload kar sakte hain.
"""
from decimal import Decimal


def _gst_split(voucher):
    return {
        "CgstVal": float(voucher.cgst), "SgstVal": float(voucher.sgst),
        "IgstVal": float(voucher.igst),
    }


def einvoice_json(voucher, company):
    """NIC e-invoice schema (simplified v1.1)."""
    lines = []
    for i, l in enumerate(voucher.lines.select_related("variant__item").all(), 1):
        lines.append({
            "SlNo": str(i),
            "PrdDesc": l.variant.item.name,
            "IsServc": "Y" if l.variant.item.item_type == "SERVICE" else "N",
            "HsnCd": l.variant.item.hsn_code or "",
            "Qty": float(l.qty), "Unit": l.unit.short_code,
            "UnitPrice": float(l.rate), "TotAmt": float(l.gross),
            "Discount": float(l.discount_total), "AssAmt": float(l.taxable_value),
            "GstRt": float(l.tax_percent),
            "CgstAmt": float(l.cgst), "SgstAmt": float(l.sgst), "IgstAmt": float(l.igst),
            "TotItemVal": float(l.line_total),
        })
    return {
        "Version": "1.1",
        "TranDtls": {"TaxSch": "GST", "SupTyp": "B2B"},
        "DocDtls": {"Typ": "INV", "No": voucher.number, "Dt": voucher.date.strftime("%d/%m/%Y")},
        "SellerDtls": {
            "Gstin": company.gstin if company else "", "LglNm": company.name if company else "",
            "Addr1": company.address if company else "", "Loc": company.state if company else "",
            "Pin": 0, "Stcd": company.state_code if company else "",
        },
        "BuyerDtls": {
            "Gstin": voucher.party.gstin, "LglNm": voucher.party.legal_name or voucher.party.name,
            "Pos": voucher.party.state_code or "", "Addr1": voucher.party.address,
            "Loc": voucher.party.city, "Stcd": voucher.party.state_code or "",
        },
        "ItemList": lines,
        "ValDtls": {
            "AssVal": float(voucher.taxable_value), **_gst_split(voucher),
            "RndOffAmt": float(voucher.round_off), "TotInvVal": float(voucher.grand_total),
        },
    }


def eway_json(voucher, company, transport=None):
    """E-Way Bill schema (simplified). transport = {transporter_id, vehicle_no, distance}."""
    transport = transport or {}
    return {
        "supplyType": "O", "subSupplyType": "1", "docType": "INV",
        "docNo": voucher.number, "docDate": voucher.date.strftime("%d/%m/%Y"),
        "fromGstin": company.gstin if company else "",
        "fromTrdName": company.name if company else "",
        "fromStateCode": company.state_code if company else "",
        "toGstin": voucher.party.gstin, "toTrdName": voucher.party.name,
        "toStateCode": voucher.party.state_code or "",
        "totalValue": float(voucher.taxable_value),
        "cgstValue": float(voucher.cgst), "sgstValue": float(voucher.sgst),
        "igstValue": float(voucher.igst), "totInvValue": float(voucher.grand_total),
        "transporterId": transport.get("transporter_id", ""),
        "vehicleNo": transport.get("vehicle_no", ""),
        "transDistance": str(transport.get("distance", "")),
        "itemList": [{
            "productName": l.variant.item.name, "hsnCode": l.variant.item.hsn_code or "",
            "quantity": float(l.qty), "qtyUnit": l.unit.short_code,
            "taxableAmount": float(l.taxable_value), "cgstRate": 0, "sgstRate": 0,
        } for l in voucher.lines.select_related("variant__item").all()],
    }
