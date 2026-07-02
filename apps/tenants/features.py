"""Plan-based feature gating. Har plan ek tier hai; har feature (nav-tab) ka ek
minimum tier. User ko sirf uske plan ke features dikhte hain.
Trial ke dauraan sab features unlock (taaki customer poora try kar sake)."""

PLAN_TIER = {"starter": 1, "pro": 2, "business": 3}

# nav-tab key -> minimum plan tier chahiye
FEATURE_TIER = {
    # Starter (1) — basic dukaan
    "dash": 1, "pos": 1, "sale": 1, "vouchers": 1, "items": 1, "parties": 1,
    "cashbank": 1, "reports": 1, "utils": 1, "whatsapp": 1, "settings": 1, "plan": 1,
    # Pro (2)
    "accounting": 2, "committee": 2, "orders": 2, "staff": 2, "restaurant": 2,
    # Business (3)
    "hr": 3, "market": 3,
}

ALWAYS = {"dash", "settings", "plan"}  # ye hamesha dikhein


def plan_tier(sub):
    if not sub:
        return 1
    status = getattr(sub, "status", "")
    if status == "TRIAL":
        return 3  # trial me sab unlock
    plan = getattr(sub, "plan", None)
    code = getattr(plan, "code", "") if plan else ""
    return PLAN_TIER.get(code, 1)


def allowed_features(sub):
    tier = plan_tier(sub)
    feats = [k for k, v in FEATURE_TIER.items() if v <= tier]
    return tier, feats
