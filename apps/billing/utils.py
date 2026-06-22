from decimal import Decimal

_ONES = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
         "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
         "Seventeen", "Eighteen", "Nineteen"]
_TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]


def _two(n):
    if n < 20:
        return _ONES[n]
    return (_TENS[n // 10] + (" " + _ONES[n % 10] if n % 10 else "")).strip()


def _three(n):
    h = n // 100
    rest = n % 100
    out = ""
    if h:
        out = _ONES[h] + " Hundred"
        if rest:
            out += " "
    if rest:
        out += _two(rest)
    return out


def amount_in_words(amount) -> str:
    """Indian system (Lakh/Crore) — invoice ke liye rupees + paise."""
    amount = Decimal(str(amount or 0))
    rupees = int(amount)
    paise = int((amount - rupees) * 100 + Decimal("0.5"))

    if rupees == 0:
        words = "Zero"
    else:
        crore = rupees // 10000000
        rupees %= 10000000
        lakh = rupees // 100000
        rupees %= 100000
        thousand = rupees // 1000
        rupees %= 1000
        hundred = rupees
        parts = []
        if crore:
            parts.append(_two(crore) + " Crore")
        if lakh:
            parts.append(_two(lakh) + " Lakh")
        if thousand:
            parts.append(_two(thousand) + " Thousand")
        if hundred:
            parts.append(_three(hundred))
        words = " ".join(parts)

    result = f"{words} Rupees"
    if paise:
        result += f" and {_two(paise)} Paise"
    return result + " Only"
