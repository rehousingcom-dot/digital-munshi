"""Har business ke owner ko aaj ki bikri ka summary email karta hai (Resend).

Chalane ka tareeka (shaam ko cron se):
    python manage.py daily_summary
    python manage.py daily_summary --date 2026-07-01   # kisi bhi din ka

Sirf un orgs ko bhejta hai jinke owner ka email hai aur jinki aaj koi activity thi."""
import datetime as _dt
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Sum, Count, F


class Command(BaseCommand):
    help = "Aaj ki bikri ka summary har org owner ko email karta hai."

    def add_arguments(self, parser):
        parser.add_argument("--date", default="", help="YYYY-MM-DD (default: aaj)")

    def handle(self, *args, **opts):
        from apps.tenants.models import Organization
        from apps.billing.models import Voucher, VoucherLine

        if opts["date"]:
            day = _dt.date.fromisoformat(opts["date"])
        else:
            day = _dt.date.today()

        key = getattr(settings, "RESEND_API_KEY", "")
        if not key:
            self.stderr.write("RESEND_API_KEY not set — emails skip.")
        sent = 0

        for org in Organization.objects.select_related("owner").all():
            owner = getattr(org, "owner", None)
            email = getattr(owner, "email", "") if owner else ""
            if not email:
                continue

            sales = Voucher.all_objects.filter(organization=org, voucher_type="SALE", date=day)
            agg = sales.aggregate(total=Sum("grand_total"), n=Count("id"))
            total = agg["total"] or 0
            n = agg["n"] or 0

            purch = Voucher.all_objects.filter(organization=org, voucher_type="PURCHASE", date=day)\
                .aggregate(total=Sum("grand_total"))["total"] or 0

            if n == 0 and not purch:
                continue  # aaj kuch nahi hua — email mat bhejo

            # Top item (aaj bikri me sabse zyada qty)
            top = (VoucherLine.all_objects
                   .filter(organization=org, voucher__voucher_type="SALE", voucher__date=day)
                   .values(name=F("variant__item__name"))
                   .annotate(qty=Sum("qty")).order_by("-qty").first())
            top_line = f"{top['name']} ({top['qty']})" if top and top.get("name") else "—"

            body = (
                f"Namaste {org.name},\n\n"
                f"{day.strftime('%d %b %Y')} ka summary:\n\n"
                f"  Bikri (Sales)   : Rs {total:,.2f}  ({n} invoice)\n"
                f"  Kharid (Purchase): Rs {purch:,.2f}\n"
                f"  Top item        : {top_line}\n\n"
                f"— Digital Munshi ERP\n{ _base_url() }"
            )
            if self._send(key, email, f"Aaj ki bikri — {org.name} ({day.strftime('%d %b')})", body):
                sent += 1

        self.stdout.write(self.style.SUCCESS(f"Daily summary sent to {sent} owners for {day}"))

    def _send(self, key, to, subject, text):
        if not key:
            return False
        try:
            import requests
            r = requests.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"from": getattr(settings, "RESEND_FROM", "onboarding@resend.dev"),
                      "to": [to], "subject": subject, "text": text}, timeout=10)
            return r.status_code in (200, 201)
        except Exception as e:
            self.stderr.write(f"(mail fail {to}: {e})")
            return False


def _base_url():
    hosts = getattr(settings, "ALLOWED_HOSTS", [])
    for h in hosts:
        if h and not h.startswith(".") and h not in ("127.0.0.1", "localhost", "*"):
            return f"https://{h}"
    return ""
