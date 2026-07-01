"""Provider-agnostic SMS sender.

Koi bhi Indian SMS gateway (STPL/Teledgers, MSG91, Fast2SMS, etc.) chal jaata hai —
bas env vars me URL template daalo. DLT-registered Sender ID + Template ID zaroori.

Env vars (Railway):
  SMS_API_URL   -> gateway ka URL, placeholders ke saath. Example (GET-based):
      https://gateway.com/api?key=XXXX&sender=RELOAD&to={to}&message={text}&tempid={tid}
      (jo params gateway maange — {to}, {text}, {tid} placeholders replace ho jayenge)
  SMS_METHOD    -> "GET" (default) ya "POST"
  SMS_OTP_TEXT  -> DLT template ka exact text, {otp} placeholder ke saath. Example:
      "Your Digital Munshi OTP is {otp}. Valid 10 min. Do not share. -RELOAD"
  SMS_OTP_TID   -> OTP template ka DLT Template ID (jo gateway maange)

Bina SMS_API_URL ke: SMS disabled (koi error nahi — sirf skip)."""
from urllib.parse import quote
from django.conf import settings


def is_enabled():
    return bool(getattr(settings, "SMS_API_URL", ""))


def _norm(to):
    d = "".join(c for c in str(to or "") if c.isdigit())
    if len(d) == 10:
        d = "91" + d
    return d


def send_sms(to, text, template_id=""):
    """Ek SMS bhejo. Returns (ok, info)."""
    url_tmpl = getattr(settings, "SMS_API_URL", "")
    if not url_tmpl:
        return False, "SMS not configured (SMS_API_URL missing)"
    to = _norm(to)
    if len(to) < 11:
        return False, f"bad number: {to}"
    try:
        import requests
        url = (url_tmpl
               .replace("{to}", to)
               .replace("{text}", quote(text))
               .replace("{tid}", quote(str(template_id or ""))))
        method = (getattr(settings, "SMS_METHOD", "GET") or "GET").upper()
        if method == "POST":
            r = requests.post(url, timeout=12)
        else:
            r = requests.get(url, timeout=12)
        ok = r.status_code in (200, 201, 202)
        return ok, f"{r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def send_otp_sms(to, otp):
    """OTP SMS — DLT template text me {otp} replace karke bhejta hai."""
    text = getattr(settings, "SMS_OTP_TEXT", "") or f"Your OTP is {otp}. Do not share."
    text = text.replace("{otp}", str(otp)).replace("{#var#}", str(otp))
    tid = getattr(settings, "SMS_OTP_TID", "")
    return send_sms(to, text, template_id=tid)
