"""Business-type presets — deck slide 2: 'All changes for any type will be from
setting option.' Har business type app ko apne hisaab se configure karta hai.

Yeh flags frontend ko batate hain ki kaunse features dikhane hain, aur billing
ke defaults kya hon. User inhe Settings se kabhi bhi badal sakta hai.
"""

BUSINESS_TYPES = [
    ("RETAIL", "Retail Shop / Kirana"),
    ("WHOLESALE", "Wholesale / Distributor"),
    ("RESTAURANT", "Restaurant / Cafe"),
    ("PHARMACY", "Pharmacy / Medical"),
    ("SERVICES", "Services / Professional"),
    ("MANUFACTURER", "Manufacturer"),
    ("GENERAL", "General / Other"),
]

# Har type ke default settings. enable_* flags UI ko control karte hain.
PRESETS = {
    "RETAIL": dict(
        enable_batch=False, enable_godown=False, enable_barcode=True, enable_serial=False,
        default_price_inclusive=True, negative_stock_allowed=True, default_item_type="GOODS",
        sell_type="PRODUCT", enable_stock_maintenance=True, enable_mrp=True,
        calculate_tax_on_mrp=True, enable_wholesale_price=False, enable_manufacturing=False,
    ),
    "WHOLESALE": dict(
        enable_batch=True, enable_godown=True, enable_barcode=True, enable_serial=False,
        default_price_inclusive=False, negative_stock_allowed=False, default_item_type="GOODS",
        sell_type="PRODUCT", enable_stock_maintenance=True, enable_wholesale_price=True,
        party_wise_rate=True, enable_mrp=True,
    ),
    "RESTAURANT": dict(
        enable_batch=False, enable_godown=False, enable_barcode=False, enable_serial=False,
        default_price_inclusive=True, negative_stock_allowed=True, default_item_type="GOODS",
        sell_type="BOTH", enable_stock_maintenance=False, enable_mrp=False,
        item_wise_discount=True,
    ),
    "PHARMACY": dict(
        enable_batch=True, enable_godown=True, enable_barcode=True, enable_serial=False,
        default_price_inclusive=True, negative_stock_allowed=False, default_item_type="GOODS",
        sell_type="PRODUCT", enable_stock_maintenance=True, enable_mrp=True,
        enable_exp_date=True, enable_mfg_date=True,
    ),
    "SERVICES": dict(
        enable_batch=False, enable_godown=False, enable_barcode=False, enable_serial=False,
        default_price_inclusive=False, negative_stock_allowed=True, default_item_type="SERVICE",
        sell_type="SERVICE", enable_stock_maintenance=False, enable_mrp=False,
        enable_description=True,
    ),
    "MANUFACTURER": dict(
        enable_batch=True, enable_godown=True, enable_barcode=True, enable_serial=True,
        default_price_inclusive=False, negative_stock_allowed=False, default_item_type="GOODS",
        sell_type="PRODUCT", enable_stock_maintenance=True, enable_manufacturing=True,
        enable_model_no=True, enable_size=True,
    ),
    "GENERAL": dict(
        enable_batch=True, enable_godown=True, enable_barcode=True, enable_serial=False,
        default_price_inclusive=False, negative_stock_allowed=True, default_item_type="GOODS",
        sell_type="BOTH", enable_stock_maintenance=True, enable_mrp=True,
    ),
}


def preset_for(business_type):
    return PRESETS.get(business_type, PRESETS["GENERAL"])
