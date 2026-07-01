"""Nightly data backup: poore database ko JSON (dumpdata) me nikaal ke Cloudinary
pe raw file ke roop me upload karta hai. pg_dump ki zaroorat nahi (DB-agnostic).

Chalane ka tareeka (Railway Console ya cron):
    python manage.py backup_db

Cloudinary env vars set hone chahiye (CLOUDINARY_CLOUD_NAME/API_KEY/API_SECRET).
Backup na ho paye to error print karta hai (non-zero exit)."""
import io
import datetime as _dt

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


# Ye apps/tables backup se skip (bade + regenerable/session data)
_EXCLUDE = [
    "contenttypes", "auth.permission", "admin.logentry", "sessions.session",
]


class Command(BaseCommand):
    help = "Database ka JSON backup Cloudinary pe upload karta hai."

    def add_arguments(self, parser):
        parser.add_argument("--email", default="", help="Backup link is email pe bhejo")

    def handle(self, *args, **opts):
        ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        buf = io.StringIO()
        call_command("dumpdata", *[f"--exclude={e}" for e in _EXCLUDE],
                     "--natural-foreign", "--natural-primary", indent=1, stdout=buf)
        data = buf.getvalue().encode("utf-8")
        size_kb = round(len(data) / 1024, 1)

        cloud = getattr(settings, "CLOUDINARY_CLOUD_NAME", "")
        if not cloud:
            self.stderr.write("Cloudinary not configured — backup upload skip. "
                              "(CLOUDINARY_* env vars set karo.)")
            return

        try:
            import cloudinary
            import cloudinary.uploader
            cloudinary.config(
                cloud_name=settings.CLOUDINARY_CLOUD_NAME,
                api_key=settings.CLOUDINARY_API_KEY,
                api_secret=settings.CLOUDINARY_API_SECRET,
                secure=True,
            )
            public_id = f"backups/dm_backup_{ts}"
            res = cloudinary.uploader.upload(
                io.BytesIO(data), resource_type="raw",
                public_id=public_id, overwrite=True, invalidate=True,
            )
            url = res.get("secure_url", "")
        except Exception as e:
            self.stderr.write(f"Backup upload FAIL: {type(e).__name__}: {e}")
            raise SystemExit(1)

        self.stdout.write(self.style.SUCCESS(f"Backup OK ({size_kb} KB) -> {url}"))

        to = opts.get("email") or getattr(settings, "BACKUP_EMAIL", "") \
            or getattr(settings, "DEFAULT_FROM_EMAIL", "")
        if to and url:
            try:
                from apps.tenants.views import _send_via_resend  # reuse Resend helper
                # simple mail via Resend
                key = getattr(settings, "RESEND_API_KEY", "")
                if key:
                    import requests
                    requests.post(
                        "https://api.resend.com/emails",
                        headers={"Authorization": f"Bearer {key}",
                                 "Content-Type": "application/json"},
                        json={"from": getattr(settings, "RESEND_FROM", "onboarding@resend.dev"),
                              "to": [to], "subject": f"Digital Munshi backup {ts}",
                              "text": f"Aaj ka data backup ready:\n{url}\n\nSize: {size_kb} KB"},
                        timeout=10)
                    self.stdout.write(f"Backup link emailed to {to}")
            except Exception as e:
                self.stderr.write(f"(email skip: {e})")
