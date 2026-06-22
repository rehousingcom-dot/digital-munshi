"""WhatsApp document bhejne ke 2 tareeke:
1. Official WhatsApp Business Cloud API (auto-send) — agar company.whatsapp_api_token set ho.
2. wa.me click-to-chat (fallback) — har user ke liye, zero-setup (reliable).

Note: Cloud API ke liye Meta verified WhatsApp Business account + token chahiye.
"""
import json
import urllib.request


def send_via_cloud_api(token, phone_number_id, to_number, message):
    """Official Cloud API se text message bhejta hai. Token configured ho to hi."""
    url = f"https://graph.facebook.com/v19.0/{phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp", "to": to_number,
        "type": "text", "text": {"body": message},
    }
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())


def send_document(company, to_number, message):
    """Configured ho to Cloud API se bheje, warna wa.me link return kare."""
    token = getattr(company, "whatsapp_api_token", "") if company else ""
    phone_id = getattr(company, "whatsapp_phone_id", "") if company else ""
    if token and phone_id and to_number:
        try:
            resp = send_via_cloud_api(token, phone_id, to_number, message)
            return {"mode": "cloud_api", "sent": True, "response": resp}
        except Exception as e:
            return {"mode": "cloud_api", "sent": False, "error": str(e)}
    return {"mode": "wa_link", "sent": False,
            "note": "Cloud API token nahi — wa.me link use karein (share_link endpoint)."}
