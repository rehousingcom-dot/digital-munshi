"""Razorpay payment gateway wrapper.

- Agar RAZORPAY_KEY_ID + RAZORPAY_KEY_SECRET .env mein set hain -> real Razorpay.
- Warna DEV MODE: ek dummy order banata hai aur verify hamesha pass (taaki bina
  keys ke local pe poora flow test ho sake).

Razorpay flow (confirmed from docs):
  client.order.create(amount_in_paise, currency, receipt)
  client.utility.verify_payment_signature({order_id, payment_id, signature})
"""
import hashlib
import hmac
import time
from django.conf import settings


def is_configured():
    return bool(getattr(settings, "RAZORPAY_KEY_ID", "") and
                getattr(settings, "RAZORPAY_KEY_SECRET", ""))


def _client():
    import razorpay
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def create_order(amount, receipt):
    """amount rupees mein -> paise mein convert karke order banata hai."""
    paise = int(round(float(amount) * 100))
    if is_configured():
        order = _client().order.create({
            "amount": paise, "currency": "INR", "receipt": receipt,
            "payment_capture": 1,
        })
        return {"order_id": order["id"], "amount": paise, "currency": "INR",
                "key_id": settings.RAZORPAY_KEY_ID, "dev_mode": False}
    # DEV MODE
    fake = f"order_dev_{int(time.time())}"
    return {"order_id": fake, "amount": paise, "currency": "INR",
            "key_id": "dev_mode", "dev_mode": True}


def verify_signature(order_id, payment_id, signature):
    """Payment signature verify. DEV mode mein hamesha True."""
    if not is_configured():
        return True  # dev mode
    secret = settings.RAZORPAY_KEY_SECRET.encode()
    msg = f"{order_id}|{payment_id}".encode()
    expected = hmac.new(secret, msg, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")


# ---- Auto-recurring (Razorpay Subscriptions API) — groundwork ----

def create_subscription(plan, cycle):
    """Razorpay Subscription banata hai (auto-recurring, eMandate ke saath).
    Configured ho to real; warna dev-mode fake subscription id.
    Note: Razorpay dashboard pe pehle Plan banana padta hai; uska plan_id yahan
    use hota hai. Production me plan_id mapping store karenge.
    """
    interval = 12 if cycle == "YEARLY" else 1
    if is_configured():
        client = _client()
        # Plan create (ya pre-created plan_id use karein)
        rp_plan = client.plan.create({
            "period": "monthly", "interval": interval,
            "item": {"name": f"{plan.name} ({cycle})",
                     "amount": int(float(plan.price_for(cycle)) * 100), "currency": "INR"},
        })
        sub = client.subscription.create({
            "plan_id": rp_plan["id"], "total_count": 120, "customer_notify": 1,
        })
        return {"subscription_id": sub["id"], "short_url": sub.get("short_url", ""),
                "key_id": settings.RAZORPAY_KEY_ID, "dev_mode": False}
    return {"subscription_id": f"sub_dev_{plan.code}_{cycle}", "short_url": "",
            "key_id": "dev_mode", "dev_mode": True}


def verify_webhook(body, signature):
    """Razorpay webhook signature verify (subscription.charged events ke liye)."""
    secret = getattr(settings, "RAZORPAY_WEBHOOK_SECRET", "") or settings.RAZORPAY_KEY_SECRET
    if not secret:
        return True  # dev
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")
