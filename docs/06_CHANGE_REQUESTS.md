# 06 — Change Requests (from "DIGITAL MUNSHI ERP 2.pptx")

Client feedback deck ki 8 slides = requested changes/bugs. Status legend:
✅ done · 🟠 missing (build) · 🟡 partial/UI tweak · 🐞 bug · 🟢 already live.

_Priority order: bugs first, then missing features in waves._

## 🐞 BUGS (P0 — pehle)
- [x] ✅ **Auto-logout on any transaction** — FIXED. Cause: JWT access token default 5-min +
      no refresh; any 401 forced logout. Fix: `SIMPLE_JWT` access=7d/refresh=30d + rotating,
      frontend ab refresh-token store karke 401 pe auto-renew karta hai (retry once, tabhi logout).
      _(commit: JWT session fix)_
- [ ] 🐞 **New Sale — GST auto-picks 18% (wrong)** — item ka actual GST rate pick hona chahiye.

## Slide 2 — Login / Signup
- [x] ✅ Auto-logout fix (upar).
- [ ] 🟠 Signup: **mobile no. mandatory + OTP verify** (abhi phone optional, no OTP).
      Needs: OTP send/verify (SMS gateway — e.g. MSG91/Twilio) + signup form change.

## Slide 3 — New Sale (billing window)
- [ ] 🟡 Party billing window se add (naya inline + manual) — select hai, inline-create add.
- [ ] 🟡 Wahi se naya item add (inline-create).
- [ ] 🐞 GST 18% wrong default → item se pick.
- [ ] 🟡 Unit dropdown → alag **column**.
- [x] 🟢 Price with/without tax + auto tax calc — backend `price_inclusive_tax` HAI; UI toggle clear karna.
- [ ] 🟡 Item add pe **row auto-open**.
- [ ] 🟠 **Description column** per line — missing.
- [ ] 🟠 **Image upload** (item/line) — missing.
- [ ] 🟡 **Document upload** — party-level hai, line/invoice-level add.

## Slide 4 — Transactions
- [ ] 🟠 Sale Order → invoice **once**; generate pe billing window; qty change → partial/close prompt.
- [ ] 🟡 Estimate → **2 options** (Order ya Invoice).
- [ ] 🟠 Delivery Challan → invoice me **returned qty** prompt → billing.
- [ ] 🟡 **Recurring → rename** "Auto / Repeated Invoice".

## Slide 5 — Batch details
- [x] 🟢 size/colour/model (ItemVariant) + expiry (Batch) — HAI.
- [ ] 🟠 **mfg date** field + **multiple batch ek saath add** wala alag window UI.

## Slide 6 — Reports
- [ ] 🟡 Report **header/branding** + **filters** improve (reference jaisa look).

## Slide 7 — Barcode
- [x] 🟢 Barcode designer — HAI.
- [ ] 🟠 printer choice, fix-print column, **batch-wise** barcode, **unique per unit**, custom size.

## Slide 8 — Cash & Bank
- [x] 🟢 Bank detail edit — HAI.
- [x] 🟢 Multiple bank accounts (name, A/C, IFSC, UPI id) — HAI.
- [ ] 🟠 **Bank details print on invoice**.
- [ ] 🟠 **UPI QR code on invoice** (payment ke liye).

---
### Suggested build order (waves)
1. **Bugs:** ✅ auto-logout · GST 18% fix.
2. **Billing UX:** description col, unit column, row auto-open, inline party/item add, tax toggle UI.
3. **Invoice output:** bank details + UPI QR on invoice, image upload.
4. **Transactions flow:** order→invoice (partial), estimate options, challan return qty, recurring rename.
5. **Batch + Barcode:** mfg date + multi-batch window, barcode enhancements.
6. **Reports:** header + filters.
7. **Signup OTP** (needs SMS gateway keys).
