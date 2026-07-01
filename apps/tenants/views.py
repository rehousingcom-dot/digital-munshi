from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Organization, Plan, Subscription, SubscriptionPayment
from .serializers import PlanSerializer, SubscriptionSerializer
from .services import signup_organization, provision_default_masters
from . import razorpay_gateway as gw


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def firms(request):
    """Multi-firm: GET = user ke saare firms; POST = naya firm banao.
    Har firm ek alag Organization hai (poora alag data/books).
    """
    user = request.user
    if request.method == "GET":
        orgs = Organization.objects.filter(owner=user).order_by("created_at")
        active_id = getattr(getattr(user, "organization", None), "id", None)
        return Response([{
            "id": o.id, "name": o.name, "active": o.id == active_id,
            "status": getattr(getattr(o, "subscription", None), "status", "-"),
        } for o in orgs])
    name = (request.data.get("name") or "").strip()
    btype = request.data.get("business_type", "GENERAL")
    if not name:
        return Response({"detail": "Firm ka naam chahiye"}, status=400)
    org = Organization.objects.create(name=name, owner=user)
    cur = getattr(getattr(user, "organization", None), "subscription", None)
    if cur and cur.status == Subscription.Status.ACTIVE:
        Subscription.objects.create(
            organization=org, plan=cur.plan, status=Subscription.Status.ACTIVE,
            billing_cycle=cur.billing_cycle, current_period_end=cur.current_period_end)
    else:
        default_plan = Plan.objects.filter(is_active=True).order_by("sort_order").first()
        Subscription.start_trial(org, plan=default_plan)
    provision_default_masters(org, business_type=btype)
    return Response({"id": org.id, "name": org.name, "active": False}, status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def firm_switch(request):
    """Active firm badlo — sirf apne firms ke beech."""
    user = request.user
    org_id = request.data.get("org_id")
    org = Organization.objects.filter(id=org_id, owner=user).first()
    if not org:
        return Response({"detail": "Firm nahi mila ya access nahi"}, status=404)
    user.organization = org
    user.save(update_fields=["organization"])
    return Response({"ok": True, "organization": org.name, "org_id": org.id})


@api_view(["GET"])
@permission_classes([IsAdminUser])
def admin_metrics(request):
    """Platform owner (aap) ke liye SaaS metrics — sab tenants ka overview.
    Sirf staff/superuser access kar sakta hai.
    """
    now = timezone.now()
    soon = now + timedelta(days=7)
    subs = Subscription.objects.select_related("plan", "organization")

    trials = [s for s in subs if s.status == "TRIAL" and s.is_access_allowed()]
    active = [s for s in subs if s.status == "ACTIVE" and s.is_access_allowed()]
    expiring = [s for s in trials if s.trial_ends_at and s.trial_ends_at <= soon]

    # MRR (monthly recurring revenue) — yearly ko /12
    mrr = Decimal("0")
    for s in active:
        if not s.plan:
            continue
        mrr += (s.plan.price_yearly / 12) if s.billing_cycle == "YEARLY" else s.plan.price_monthly

    revenue = SubscriptionPayment.objects.filter(status="PAID").aggregate(
        t=Sum("amount"))["t"] or Decimal("0")
    recent = Organization.objects.filter(created_at__gte=now - timedelta(days=30)).count()

    return Response({
        "total_businesses": Organization.objects.count(),
        "active_trials": len(trials),
        "trials_expiring_7d": len(expiring),
        "active_subscriptions": len(active),
        "expired": subs.filter(status="EXPIRED").count(),
        "mrr": float(round(mrr, 2)),
        "total_revenue": float(revenue),
        "signups_last_30d": recent,
        "recent_businesses": [
            {"name": o.name, "joined": str(o.created_at.date()),
             "status": getattr(getattr(o, "subscription", None), "status", "—")}
            for o in Organization.objects.order_by("-created_at")[:10]
        ],
    })


def _tokens(user):
    r = RefreshToken.for_user(user)
    return {"access": str(r.access_token), "refresh": str(r)}


def _send_email_otp(email):
    """Generate + cache an OTP for the email and try to send it. Returns (otp, sent)."""
    import random
    from django.core.cache import cache
    from django.core.mail import send_mail
    from django.conf import settings
    otp = f"{random.randint(0, 999999):06d}"
    cache.set(f"otp:{email}", otp, 600)  # 10 min
    sent = False
    host = getattr(settings, "EMAIL_HOST", "") or ""
    if getattr(settings, "EMAIL_HOST_USER", "") or host not in ("", "localhost"):
        try:
            send_mail(
                "Your Digital Munshi OTP",
                f"Your OTP is {otp}. It is valid for 10 minutes.\n\n— Digital Munshi ERP",
                getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@digitalmunshi.in"),
                [email], fail_silently=False,
            )
            sent = True
        except Exception:
            sent = False
    return otp, sent


@api_view(["POST"])
@permission_classes([AllowAny])
def send_otp(request):
    """Signup email OTP. If email (SMTP) is configured it is sent to the inbox,
    otherwise dev-mode returns the OTP so testing still works."""
    email = str(request.data.get("email") or "").strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        return Response({"detail": "Enter a valid email address"}, status=400)
    otp, sent = _send_email_otp(email)
    resp = {"sent": sent}
    if not sent:
        resp["dev_otp"] = otp
        resp["message"] = "Email not configured yet — OTP shown on screen (dev mode)."
    return Response(resp)


@api_view(["POST"])
@permission_classes([AllowAny])
def signup(request):
    """Register a new business + 7-day trial. Email + OTP required. Returns JWT."""
    from django.core.cache import cache
    d = request.data
    required = ["username", "password", "org_name", "email"]
    missing = [f for f in required if not d.get(f)]
    if missing:
        return Response({"detail": f"Required: {', '.join(missing)}"}, status=400)
    email = str(d.get("email", "")).strip().lower()
    if "@" not in email:
        return Response({"detail": "Enter a valid email address"}, status=400)
    cached = cache.get(f"otp:{email}")
    if not cached or str(d.get("otp", "")).strip() != cached:
        return Response({"detail": "OTP is wrong or expired — please resend"}, status=400)
    try:
        user, org, sub = signup_organization(
            username=d["username"], password=d["password"],
            email=email, org_name=d["org_name"], phone=d.get("phone", ""),
            business_type=d.get("business_type", "GENERAL"),
        )
    except ValueError as e:
        return Response({"detail": str(e)}, status=400)
    cache.delete(f"otp:{email}")
    return Response({
        "tokens": _tokens(user),
        "organization": org.name,
        "trial_ends_at": sub.trial_ends_at,
        "days_left": sub.days_left,
    }, status=201)


@api_view(["GET"])
@permission_classes([AllowAny])
def plans(request):
    return Response(PlanSerializer(Plan.objects.filter(is_active=True), many=True).data)


def _sub(request):
    org = getattr(request.user, "organization", None)
    return getattr(org, "subscription", None) if org else None


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    u = request.user
    org = getattr(u, "organization", None)
    logo = None
    if org:
        from apps.core.models import Company
        company = Company.objects.filter(is_active=True).first()
        if company and company.logo:
            try:
                logo = request.build_absolute_uri(company.logo.url)
            except Exception:
                logo = None
    return Response({
        "username": u.username, "role": getattr(u, "role", ""),
        "is_platform_admin": bool(u.is_staff or u.is_superuser),
        "organization": org.name if org else None,
        "logo": logo,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def subscription_status(request):
    sub = _sub(request)
    if not sub:
        return Response({"detail": "No subscription"}, status=404)
    sub.refresh_status()
    return Response(SubscriptionSerializer(sub).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_order(request):
    """Plan + cycle -> Razorpay order banata hai (ya dev-mode order)."""
    sub = _sub(request)
    if not sub:
        return Response({"detail": "No subscription"}, status=404)
    code = request.data.get("plan_code")
    cycle = (request.data.get("cycle") or "MONTHLY").upper()
    plan = Plan.objects.filter(code=code, is_active=True).first()
    if not plan:
        return Response({"detail": "Invalid plan"}, status=400)
    amount = plan.price_for(cycle)
    order = gw.create_order(amount, receipt=f"sub_{sub.id}_{plan.code}")
    pay = SubscriptionPayment.objects.create(
        subscription=sub, plan=plan, cycle=cycle, amount=amount,
        gateway_order_id=order["order_id"], status=SubscriptionPayment.Status.CREATED,
    )
    return Response({
        "payment_id": pay.id,
        "order_id": order["order_id"],
        "amount": order["amount"], "currency": order["currency"],
        "key_id": order["key_id"], "dev_mode": order["dev_mode"],
        "plan": plan.name, "cycle": cycle,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_recurring(request):
    """Auto-recurring subscription (Razorpay Subscriptions API). Dev-mode me turant activate.
    Groundwork — production me eMandate checkout + webhook se renew hoga.
    """
    sub = _sub(request)
    if not sub:
        return Response({"detail": "No subscription"}, status=404)
    code = request.data.get("plan_code")
    cycle = (request.data.get("cycle") or "MONTHLY").upper()
    plan = Plan.objects.filter(code=code, is_active=True).first()
    if not plan:
        return Response({"detail": "Invalid plan"}, status=400)
    rs = gw.create_subscription(plan, cycle)
    if rs["dev_mode"]:
        sub.activate(plan, cycle)  # dev: turant active
        return Response({"dev_mode": True, "activated": True,
                         "subscription": SubscriptionSerializer(sub).data})
    return Response({"dev_mode": False, "subscription_id": rs["subscription_id"],
                     "short_url": rs["short_url"], "key_id": rs["key_id"]})


@api_view(["POST"])
@permission_classes([AllowAny])
def razorpay_webhook(request):
    """Razorpay webhook — subscription.charged pe period extend (groundwork)."""
    sig = request.META.get("HTTP_X_RAZORPAY_SIGNATURE", "")
    if not gw.verify_webhook(request.body, sig):
        return Response({"detail": "bad signature"}, status=400)
    event = request.data.get("event", "")
    # production: event payload se org/subscription nikaal kar activate karein
    return Response({"received": True, "event": event})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def verify_payment(request):
    """Razorpay se aaya signature verify -> subscription activate."""
    sub = _sub(request)
    if not sub:
        return Response({"detail": "No subscription"}, status=404)
    order_id = request.data.get("razorpay_order_id")
    payment_id = request.data.get("razorpay_payment_id", "dev_payment")
    signature = request.data.get("razorpay_signature", "")

    pay = SubscriptionPayment.objects.filter(
        subscription=sub, gateway_order_id=order_id).order_by("-id").first()
    if not pay:
        return Response({"detail": "Order not found"}, status=404)

    if not gw.verify_signature(order_id, payment_id, signature):
        pay.status = SubscriptionPayment.Status.FAILED
        pay.save(update_fields=["status"])
        return Response({"detail": "Signature verification failed"}, status=400)

    pay.status = SubscriptionPayment.Status.PAID
    pay.gateway_payment_id = payment_id
    pay.gateway_signature = signature
    pay.paid_at = timezone.now()
    pay.save()
    sub.activate(pay.plan, pay.cycle)
    return Response({
        "status": "activated",
        "subscription": SubscriptionSerializer(sub).data,
    })
