from decimal import Decimal
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.tenants.tenancy import OrgScopedQuerysetMixin
from .models import Committee, CommitteeMember, CommitteeRound, CommitteePayment, money
from .serializers import (
    CommitteeSerializer, CommitteeMemberSerializer,
    CommitteeRoundSerializer, CommitteePaymentSerializer,
)


def _sync_payments(rnd):
    """Round ke per_head ke hisaab se har member ka payment row bana/update kare
    (amount_paid ko chhede bina)."""
    for m in rnd.committee.members.all():
        CommitteePayment.objects.update_or_create(
            round=rnd, member=m, defaults={"amount_due": rnd.per_head})


class CommitteeViewSet(OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Committee.objects.all()
    serializer_class = CommitteeSerializer

    @action(detail=True, methods=["post"])
    def add_members(self, request, pk=None):
        """Bulk members add. body: {members:[{name,phone}]} ya {names:["a","b"]}."""
        c = self.get_object()
        rows = request.data.get("members")
        if not rows:
            rows = [{"name": n} for n in (request.data.get("names") or []) if n]
        created = []
        for r in rows:
            nm = (r.get("name") or "").strip()
            if not nm:
                continue
            m = CommitteeMember.objects.create(
                committee=c, name=nm, phone=(r.get("phone") or "").strip(),
                party_id=r.get("party") or None)
            created.append(m)
        return Response(CommitteeMemberSerializer(created, many=True).data)

    @action(detail=True, methods=["post"])
    def record_bid(self, request, pk=None):
        """Ek month ki boli record kare + sab members ke payment rows bana de.
        body: {month_no, date, winner, bid_amount}
        """
        c = self.get_object()
        month_no = int(request.data.get("month_no") or 0)
        if month_no < 1:
            return Response({"detail": "month_no required"}, status=400)
        rnd, _ = CommitteeRound.objects.get_or_create(committee=c, month_no=month_no)
        rnd.date = request.data.get("date") or rnd.date
        w = request.data.get("winner")
        rnd.winner_id = int(w) if w else None
        rnd.bid_amount = money(request.data.get("bid_amount") or 0)
        rnd.compute()
        _sync_payments(rnd)
        return Response(CommitteeRoundSerializer(rnd).data)

    @action(detail=True, methods=["get"])
    def ledger(self, request, pk=None):
        """Har member ka summary: total bharna, mila, gain/(cost), approx interest.
        Committee-level totals bhi."""
        c = self.get_object()
        n = c.members_count or 1
        rounds = list(c.rounds.all())
        total_per_head = sum((r.per_head for r in rounds), Decimal("0"))  # ek member ka poora contribution (recorded rounds tak)
        pays = list(CommitteePayment.objects.filter(round__committee=c).select_related("member", "round"))
        by_member = {}
        for p in pays:
            by_member.setdefault(p.member_id, []).append(p)

        wins = {r.winner_id: r for r in rounds if r.winner_id}
        out = []
        for m in c.members.all():
            mpays = by_member.get(m.id, [])
            paid = sum((p.amount_paid for p in mpays), Decimal("0"))
            late = sum((p.late_fee for p in mpays), Decimal("0"))
            win = wins.get(m.id)
            received = money(win.net_payable) if win else Decimal("0")
            won_month = win.month_no if win else None
            # gain = paisa mila - poora contribution dena hai (recorded rounds tak)
            gain = money(received - total_per_head)
            annual = None
            if win and total_per_head > 0:
                # simple annualised: gain ko total contribution pe, term (N month) ke hisaab se
                annual = round(float(gain / total_per_head) * (12.0 / n) * 100, 1)
            out.append({
                "member": m.id, "name": m.name, "phone": m.phone,
                "won_month": won_month, "received": str(received),
                "total_contribution": str(total_per_head),
                "paid_so_far": str(money(paid)), "late_fee": str(money(late)),
                "gain": str(gain), "annual_interest": annual,
            })
        collected = sum((p.amount_paid for p in pays), Decimal("0"))
        return Response({
            "committee": c.name, "total_value": str(money(c.total_value)),
            "members": n, "rounds_done": len([r for r in rounds if r.winner_id]),
            "one_member_contribution": str(money(total_per_head)),
            "total_collected": str(money(collected)),
            "members_ledger": out,
        })


class CommitteeMemberViewSet(OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = CommitteeMember.objects.select_related("committee", "party").all()
    serializer_class = CommitteeMemberSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        cid = self.request.query_params.get("committee")
        if cid:
            qs = qs.filter(committee_id=cid)
        return qs


class CommitteeRoundViewSet(OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = CommitteeRound.objects.select_related("committee", "winner").all()
    serializer_class = CommitteeRoundSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        cid = self.request.query_params.get("committee")
        if cid:
            qs = qs.filter(committee_id=cid)
        return qs

    def perform_create(self, serializer):
        obj = serializer.save()
        obj.compute()
        _sync_payments(obj)
        self._audit("CREATE", obj)

    def perform_update(self, serializer):
        obj = serializer.save()
        obj.compute()
        _sync_payments(obj)
        self._audit("UPDATE", obj)


class CommitteePaymentViewSet(OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = CommitteePayment.objects.select_related("member", "round", "round__committee").all()
    serializer_class = CommitteePaymentSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        cid = self.request.query_params.get("committee")
        rid = self.request.query_params.get("round")
        mid = self.request.query_params.get("member")
        if cid:
            qs = qs.filter(round__committee_id=cid)
        if rid:
            qs = qs.filter(round_id=rid)
        if mid:
            qs = qs.filter(member_id=mid)
        return qs

    @action(detail=True, methods=["post"])
    def mark_paid(self, request, pk=None):
        """body: {amount_paid(optional=full due), paid_on(optional=today)}"""
        p = self.get_object()
        p.paid_on = request.data.get("paid_on") or timezone.localdate()
        p.compute_late_fee(save=False)
        amt = request.data.get("amount_paid")
        p.amount_paid = money(amt) if amt not in (None, "") else p.total_due
        p.save()
        return Response(CommitteePaymentSerializer(p).data)
