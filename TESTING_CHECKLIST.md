# Digital Munshi ERP — Local Testing Checklist

Har feature ko ek-ek karke test karo. Login: **demo / demo12345** (ya naya signup).
Koi bhi screen pe error/galti dikhe to screenshot bhej dena — turant fix ho jayega.

> ⚠️ Pehle ek baar: `python manage.py migrate` chala lena (naya WhatsApp field ke liye).

---

## 1. Login / Signup
- [ ] `http://127.0.0.1:8000/` khulta hai, premium login screen dikhta hai
- [ ] demo / demo12345 se login hota hai
- [ ] Logout karke **naya business signup** (alag business type choose karke) — 7-din trial milta hai
- [ ] Naye business ka data demo se bilkul alag hai (isolation)

## 2. Dashboard
- [ ] KPI widgets dikhte hain (Total Sales, Profit, To Collect, To Pay, Tax)
- [ ] **+ Add Widget** se Purchases / Stock Value / Invoices add hote hain
- [ ] Widget pe hover karke **×** se hatta hai; refresh pe choice yaad rehti hai
- [ ] **Add Sale** / **Add Purchase** buttons sahi screen kholte hain
- [ ] Bar chart + Top Sellers + Recent Transactions dikhte hain
- [ ] Trend % (▲/▼) sahi dikhta hai

## 3. Items
- [ ] Items list dikhti hai (demo ke 5 items)
- [ ] Naya item add karo (admin/`/admin/` se ya API) — list mein aata hai
- [ ] Search kaam karta hai

## 4. Parties (Customer / Supplier)
- [ ] Parties list dikhti hai
- [ ] Naya customer add (GSTIN ke saath) — galat GSTIN reject hota hai
- [ ] Supplier add hota hai

## 5. Billing — New Sale
- [ ] Customer + item select karke bill banta hai (Save & Post)
- [ ] **Barcode** field mein item-code/barcode daal ke Enter → item add hota hai
- [ ] Discount + GST sahi calculate hota hai (total match karo)
- [ ] Bill banne ke baad **Print** aur **Share on WhatsApp** buttons aate hain
- [ ] Document type badal ke **Estimate** banao → phir Invoice mein convert
- [ ] **Add Purchase** se purchase entry → stock badhta hai

## 6. Invoice Print / PDF / WhatsApp
- [ ] Vouchers list mein **Print** → invoice HTML khulta hai (GST format, amount in words)
- [ ] PDF download hota hai
- [ ] **WhatsApp** button → WhatsApp Web/app khulta hai, message + link ready

## 7. Reports
- [ ] P&L cards (Revenue, Purchases, Gross Profit)
- [ ] Receivables Aging (4 buckets)
- [ ] Day Book table
- [ ] GSTR-1 (B2B / B2C / HSN)
- [ ] Low Stock, Purchase Register
- [ ] Party Statement (party choose karke running balance)

## 8. HR / Payroll
- [ ] **Employees** — naya employee add (salary structure ke saath)
- [ ] **Attendance** — date choose karke P/A/½/L/H mark
- [ ] **Leave** — leave add → Approve/Reject
- [ ] **Payroll** — month choose → Generate Payroll → net salary compute
- [ ] **Payslip** link → PDF khulta hai (earnings/deductions + amount in words)

## 9. WhatsApp Connect (naya screen)
- [ ] WhatsApp tab khulta hai — Quick Share ACTIVE dikhta hai
- [ ] Cloud API setup fields (token/phone-id) save hote hain
- [ ] Voucher ke saamne "Send on WhatsApp" → WhatsApp khulta hai

## 10. Settings
- [ ] Business type badalne par feature toggles reset hote hain
- [ ] GST Scheme **Composition** karo → naye sale pe tax 0 (Bill of Supply)
- [ ] Individual toggle save hota hai
- [ ] **Logo upload** → invoice pe logo aata hai
- [ ] **Export Items/Parties CSV** download; **Import** CSV se items aate hain

## 11. App Users (Staff) + Roles
- [ ] Staff add (username + password + role) — Operator/Viewer
- [ ] Viewer login → sirf dekh sakta hai (add/edit pe rok)

## 12. Subscription
- [ ] Banner pe trial/active status dikhta hai
- [ ] Subscription page pe plans dikhte hain; (dev-mode) Choose Plan → activate

## 13. Platform Admin (aapke liye)
- [ ] `owner` superuser se login → sidebar mein **Platform Admin** tab (MRR, tenants, revenue)
- [ ] `http://127.0.0.1:8000/admin/` → Django admin se saara data manage

## 14. Desktop App (Electron)
- [ ] `cd desktop && npm install && npm start` → native window khulta hai
- [ ] Poora app native window mein chalta hai
- [ ] Menu → WhatsApp → Open WhatsApp Web → QR scan window khulta hai

---

### Testing tips
- Har module mein **ek real entry** banao (item, party, bill, employee) taaki end-to-end flow verify ho
- Numbers cross-check karo (GST, discount, payroll) — kahin galat lage to batao
- Mobile/tablet pe bhi browser se kholo — responsive design check (sidebar hamburger)
- Koi error page (yellow Django error ya red text) dikhe → poora message bhej dena
