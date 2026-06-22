"""Tenant resolution + subscription enforcement.

1. Har request pe current organization set karta hai (JWT header, ?token=, ya session se).
2. Agar subscription expire ho gaya hai to business APIs block (402) — sirf
   auth/signup/plans/subscription endpoints allow taaki user pay kar sake.
"""
from django.http import JsonResponse
from .tenancy import set_current_org, clear_current_org

# Inhe subscription ke bina bhi access milta hai
EXEMPT_PREFIXES = (
    "/api/health", "/api/auth", "/api/signup", "/api/me",
    "/api/plans", "/api/subscription", "/api/admin", "/api/firms",
    "/api/schema", "/api/docs",
)


def _resolve_user(request):
    # Session user (admin / browser)
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        return user
    # JWT — header ya query param (?token= invoice links ke liye)
    try:
        from rest_framework_simplejwt.authentication import JWTAuthentication
        from rest_framework_simplejwt.tokens import AccessToken
        auth = JWTAuthentication()
        header = auth.authenticate(request)
        if header is not None:
            return header[0]
        raw = request.GET.get("token")
        if raw:
            validated = AccessToken(raw)
            return auth.get_user(validated)
    except Exception:
        return None
    return None


class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        org = None
        sub = None
        user = _resolve_user(request)
        if user is not None and getattr(user, "is_authenticated", False):
            org = getattr(user, "organization", None)
            if org is not None:
                sub = getattr(org, "subscription", None)
        set_current_org(org)
        try:
            # Subscription enforcement (sirf protected /api/ paths)
            path = request.path
            if path.startswith("/api/") and not path.startswith(EXEMPT_PREFIXES):
                if org is not None:
                    if sub is None or not _allowed(sub):
                        return JsonResponse(
                            {"detail": "Subscription expired ya inactive. Kripya plan le lein.",
                             "code": "subscription_required"},
                            status=402,
                        )
            return self.get_response(request)
        finally:
            clear_current_org()


def _allowed(sub):
    try:
        return sub.is_access_allowed()
    except Exception:
        return False
