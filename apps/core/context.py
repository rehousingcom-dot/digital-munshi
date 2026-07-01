from django.conf import settings


def seo(request):
    return {
        "GA_ID": getattr(settings, "GA_MEASUREMENT_ID", ""),
        "SUPPORT_WA": getattr(settings, "SUPPORT_WHATSAPP", ""),
    }
