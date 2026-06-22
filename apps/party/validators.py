import re
from django.core.exceptions import ValidationError

# GSTIN format: 2-digit state code + 10-char PAN + entity digit + 'Z' + checksum
GSTIN_REGEX = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$")

_GST_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def gstin_checksum_ok(gstin: str) -> bool:
    """GSTIN ka last digit checksum verify karta hai (official algorithm)."""
    if len(gstin) != 15:
        return False
    factor, total = 2, 0
    for ch in reversed(gstin[:14]):
        if ch not in _GST_CHARS:
            return False
        code = _GST_CHARS.index(ch)
        prod = code * factor
        total += prod // 36 + prod % 36
        factor = 1 if factor == 2 else 2
    check = (36 - (total % 36)) % 36
    return _GST_CHARS[check] == gstin[14]


# GST state code -> state name (intra/inter-state decide karne ke liye)
GST_STATE_CODES = {
    "01": "Jammu and Kashmir", "02": "Himachal Pradesh", "03": "Punjab", "04": "Chandigarh",
    "05": "Uttarakhand", "06": "Haryana", "07": "Delhi", "08": "Rajasthan", "09": "Uttar Pradesh",
    "10": "Bihar", "11": "Sikkim", "12": "Arunachal Pradesh", "13": "Nagaland", "14": "Manipur",
    "15": "Mizoram", "16": "Tripura", "17": "Meghalaya", "18": "Assam", "19": "West Bengal",
    "20": "Jharkhand", "21": "Odisha", "22": "Chhattisgarh", "23": "Madhya Pradesh", "24": "Gujarat",
    "26": "Dadra and Nagar Haveli and Daman and Diu", "27": "Maharashtra", "28": "Andhra Pradesh (Old)",
    "29": "Karnataka", "30": "Goa", "31": "Lakshadweep", "32": "Kerala", "33": "Tamil Nadu",
    "34": "Puducherry", "35": "Andaman and Nicobar Islands", "36": "Telangana", "37": "Andhra Pradesh",
    "38": "Ladakh", "97": "Other Territory", "99": "Centre Jurisdiction",
}


def gstin_info(gstin: str) -> dict:
    """Verified GSTIN se structured info nikaalta hai (state, PAN, entity type)."""
    g = (gstin or "").strip().upper()
    state = GST_STATE_CODES.get(g[:2], "") if len(g) >= 2 else ""
    pan = g[2:12] if len(g) >= 12 else ""
    return {"gstin": g, "state_code": g[:2] if len(g) >= 2 else "", "state": state, "pan": pan}


def validate_gstin(value: str):
    """Format + checksum validation. (Government API verification baad ke phase mein.)"""
    if not value:
        return
    value = value.strip().upper()
    if not GSTIN_REGEX.match(value):
        raise ValidationError("GSTIN format galat hai (15 characters: 22AAAAA0000A1Z5 jaisa).")
    if not gstin_checksum_ok(value):
        raise ValidationError("GSTIN ka checksum match nahi kar raha — number dobara check karein.")
