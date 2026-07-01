# 06 — Change Requests (from "DIGITAL MUNSHI ERP 2.pptx")

Client feedback deck ki 8 slides = requested changes/bugs. Status legend:
✅ done · 🟠 missing (build) · 🟡 partial/UI tweak · 🐞 bug · 🟢 already live.

_Priority order: bugs first, then missing features in waves._

## 🐞 BUGS (P0 — pehle)
- [x] ✅ **Auto-logout on any transaction** — FIXED. Cause: JWT access token default 5-min +
      no refresh; any 401 forced logout. Fix: `SIMPLE_JWT` access=7d/refresh=30d + rotating,
      frontend ab refresh-token store karke 401 pe auto-renew karta hai (retry once, tabhi logout).
      _(commit: JWT session fix)_
- [x] ✅ **New Sale — GST auto-picks 18% (wrong)** — FIXED. Cause: frontend `taxFor()` stub
      hamesha 18 return karta tha; item ka tax_rate percent expose hi nahi tha. Fix: ItemSerializer
      me `tax_percent` add (tax_rate.percent se), New Sale + POS ab item ka **real GST** pick karte
      hain (item me rate set na ho to 0 — user item form me GST% set kare). _(commit 1d258eb)_

## Slide 2 — Login / Signup
- [x] ✅ Auto-logout fix (upar).
- [x] ✅ Signup: **mobile mandatory + OTP verify** — `/api/send-otp/` + signup me OTP check.
      SMS gateway abhi nahi, isliye **dev-mode me OTP screen par** dikhta hai (testing ke liye).
      _Real SMS ke liye MSG91/Twilio keys chahiye — send_otp view me `sms_configured` wire karna._ _(4de69b6)_

## Slide 3 — New Sale (billing window)
- [x] ✅ Party billing window se add — **inline "+ New"** quick-add (naam+phone → Save & Select). _(233604d)_
- [x] ✅ Wahi se naya item add — **"+ New Item"** quick-add (naam+price+GST → Save & Add to bill). _(233604d)_
- [x] ✅ GST 18% wrong default → item se real GST pick. _(1d258eb)_
- [x] ✅ Unit alag **column** me — already tha (Item ke baad Unit column).
- [x] ✅ Price with/without tax + auto tax calc — `price_inclusive_tax` + row me **+T/−T toggle**.
- [x] ✅ Item add pe **row auto-open** — item select karte hi nayi khaali row auto-add. _(0845bfa)_
- [x] ✅ **Description column** per line (+ invoice par print). _(0845bfa)_
- [x] ✅ **Image upload** — Item photo upload (ItemForm → `/items/<id>/upload_image/`), preview + shows in form. _(7d0c0ae)_
- [~] 🟡 **Document upload** — party-level document upload HAI. Invoice/line-level attachment abhi nahi (v2 me).

## Slide 4 — Transactions
- [x] ✅ Sale Order/Estimate/Challan → invoice **sirf ek baar** (converted-once guard; "✓ Invoiced" badge). _(75add7b)_
- [x] ✅ Estimate → **2 options**: "→ Invoice" aur "→ Order" buttons. _(75add7b)_
- [x] ✅ Delivery Challan → invoice **returned qty** prompt — per-line "Returned" qty modal; sirf net
      delivered qty invoice hoti hai (backend convert_to returns=). _(5b1db8e)_
- [x] ✅ **Recurring → "Auto Invoice"** rename (tab, buttons, modal). _(75add7b)_

## Slide 5 — Batch details
- [x] 🟢 size/colour/model (ItemVariant) + expiry (Batch) — HAI.
- [x] ✅ **Batch me mfg_date + size + colour + model** fields add (model + ItemForm inputs). _(7d0c0ae)_
- [x] ✅ **Multiple batch ek saath add** — Item form → Stock tab me "More Batches" grid (batch_no+MRP+expiry, add many). _(144b661)_

## Slide 6 — Reports
- [x] ✅ Report **branded header** (business name, report title, date-range, Generated timestamp, **Print/PDF**)
      + **working date-range filter** (start/end → backend `_range`). _(0c3c610)_

## Slide 7 — Barcode
- [x] 🟢 Barcode designer — HAI (symbology, custom W×H mm, copies).
- [x] ✅ **Columns/row (fix print)**, **unique barcode per unit** (…-0001), name/price design toggles,
      printer choice (browser print dialog). Custom size pehle se tha. _(7ab92ec)_
- [x] ✅ **Batch-wise barcode** — Barcode Designer me batch selector; value = code-<batch_no>, MRP batch se. _(144b661)_

## Slide 8 — Cash & Bank
- [x] 🟢 Bank detail edit — HAI.
- [x] 🟢 Multiple bank accounts (name, A/C, IFSC, UPI id) — HAI.
- [x] ✅ **Bank details print on invoice** — org ka active bank (name/A-C/IFSC/UPI). _(6617b19)_
- [x] ✅ **UPI QR code on invoice** — "Scan & Pay" QR (upi://pay, amount ke saath). _(6617b19)_

---
### Suggested build order (waves)
1. **Bugs:** ✅ auto-logout · GST 18% fix.
2. **Billing UX:** description col, unit column, row auto-open, inline party/item add, tax toggle UI.
3. **Invoice output:** bank details + UPI QR on invoice, image upload.
4. **Transactions flow:** order→invoice (partial), estimate options, challan return qty, recurring rename.
5. **Batch + Barcode:** mfg date + multi-batch window, barcode enhancements.
6. **Reports:** header + filters.
7. **Signup OTP** (needs SMS gateway keys).

## Post-deck follow-ups (July 2026)
- [x] ✅ **Email OTP via Resend** (Railway SMTP blocked) — domain reloaddigital.in verified. _(1497bf5)_
- [x] ✅ **Data backup / export** — Utilities → Transactions CSV (all + Sales/Purchase filters). _(6fe477a)_
- [x] ✅ **Hindi/English toggle** expanded — New Sale, Party, Items, Reports/Cash&Bank/Utilities/Accounting/HR
      titles + tab bars + core form fields wrapped in `t()`. _(bc70ec0, aa97ab5, 4864299, 3e03187)_
- [x] ✅ **Challan→invoice returned-qty**, **multi-batch grid**, **batch-wise barcode**. _(5b1db8e, 144b661)_
