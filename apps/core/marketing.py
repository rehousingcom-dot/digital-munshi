"""Marketing/SEO content — keyword landing pages + blog posts.
Content yahan dict me hai (DB ki zaroorat nahi). Naye page/blog add karna ho to
yahan entry add kar do."""

# ---- Keyword landing pages (/software/<slug>/) ----
KEYWORD_PAGES = {
    "gst-billing-software": {
        "title": "GST Billing Software for Indian Businesses | Digital Munshi",
        "desc": "Free GST billing & invoicing software. GST invoice, e-invoice, e-way bill, thermal & A4 print. Kirana, wholesale, pharmacy ke liye. Free trial.",
        "h1": "GST Billing Software — aasan, tez, GST-ready",
        "intro": "Digital Munshi se seconds me GST invoice banao — CGST/SGST/IGST auto, HSN, e-invoice aur e-way bill JSON ready. Thermal aur A4 print, WhatsApp pe share, UPI QR invoice par.",
        "points": ["GST invoice + Bill of Supply + Credit/Debit note", "e-Invoice & e-Way bill JSON", "Thermal (58mm) + A4 print, PDF", "GSTR-1 / GSTR-3B / HSN summary reports", "WhatsApp share + UPI QR on invoice"],
        "keyword": "GST billing software",
    },
    "kirana-billing-app": {
        "title": "Kirana Store Billing App | POS + Udhaar Khata — Digital Munshi",
        "desc": "Kirana dukaan ke liye billing app — fast POS billing, barcode scan, udhaar khata, stock alert. Hinglish me. Free trial.",
        "h1": "Kirana Billing App — dukaan ka poora hisaab",
        "intro": "Kirana store ke liye sabse aasan billing app. Barcode se fatafat billing, udhaar/khata, stock kam hone par alert, aur roz ki bikri ka hisaab — sab ek jagah.",
        "points": ["Fast POS billing + camera barcode scan", "Udhaar / khata + payment reminder", "Stock alert (kam maal par)", "Roz ki bikri ka summary", "Online catalog — WhatsApp par order"],
        "keyword": "kirana billing app",
    },
    "invoice-software": {
        "title": "Free Invoice Software India | Bill Banane Ka App — Digital Munshi",
        "desc": "Free invoice software — professional bill banao, GST ya bina GST, print/PDF/WhatsApp. Har business ke liye. Free trial.",
        "h1": "Invoice Software — professional bill 30 second me",
        "intro": "Apne business ka professional invoice banao — logo, bank details, UPI QR ke saath. GST ya bina-GST, print ya PDF, seedha WhatsApp par bhejo.",
        "points": ["Professional GST / non-GST invoice", "Logo + bank details + UPI QR", "Print, PDF, WhatsApp share", "Recurring/auto invoice", "Multi-currency (export)"],
        "keyword": "invoice software",
    },
    "inventory-management-software": {
        "title": "Inventory Management Software India | Stock App — Digital Munshi",
        "desc": "Inventory & stock management software — multi-godown, batch, barcode, low-stock alert, dead-stock report. Free trial.",
        "h1": "Inventory Management Software — stock par poora control",
        "intro": "Multi-godown stock, batch/expiry, variants, barcode aur low-stock alerts. Dead vs fast-moving items ka report — kya rukega, kya restock karna hai turant pata.",
        "points": ["Multi-godown stock tracking", "Batch, expiry, serial/IMEI", "Barcode + label designer", "Low-stock & reorder alerts", "Dead / fast-mover report"],
        "keyword": "inventory management software",
    },
    "vyapar-alternative": {
        "title": "Best Vyapar Alternative | Billing + Accounting — Digital Munshi",
        "desc": "Vyapar / Tally ka aasan alternative — billing, GST, inventory, accounting, HR, POS ek hi app me. Hinglish. Free trial.",
        "h1": "Vyapar / Tally ka aasan alternative",
        "intro": "Ek hi app me billing + GST + inventory + accounting + HR + POS + multi-firm. Hinglish me, aasan — Vyapar aur Tally ka modern, sasta alternative.",
        "points": ["Billing + GST + e-invoice", "Double-entry accounting + reports", "Inventory + POS + multi-firm", "HR / payroll", "Online catalog + loyalty points"],
        "keyword": "Vyapar alternative",
    },
}

# ---- Blog posts (/blog/<slug>/) ----
BLOG_POSTS = {
    "gst-invoice-kaise-banaye": {
        "title": "GST Invoice Kaise Banaye — Step by Step (2026) | Digital Munshi",
        "desc": "GST invoice banane ka aasan tarika — kaunsi details chahiye, CGST/SGST/IGST kab lagta hai, aur software se 30 second me invoice.",
        "h1": "GST Invoice Kaise Banaye — Poori Guide",
        "html": """
<p>GST invoice har registered business ke liye zaroori hai. Isme kuch mandatory details honi chahiye. Aaiye simple bhasha me samajhte hain.</p>
<h2>GST Invoice me kya-kya hona chahiye</h2>
<ul>
<li>Seller ka naam, address aur GSTIN</li>
<li>Invoice number aur date</li>
<li>Buyer ka naam, address, GSTIN (agar registered)</li>
<li>Item ka naam, HSN/SAC code, quantity, rate</li>
<li>Taxable value, CGST/SGST ya IGST, total</li>
</ul>
<h2>CGST/SGST vs IGST — kab kaunsa?</h2>
<p>Agar buyer aur seller <b>same state</b> me hain to <b>CGST + SGST</b> lagta hai. Agar <b>alag state</b> me hain to <b>IGST</b>. Digital Munshi ye automatically decide kar leta hai party ke state ke hisaab se.</p>
<h2>Software se invoice — 30 second</h2>
<p>Manually ye sab likhna time leta hai aur galti hoti hai. Digital Munshi me party aur item choose karo — GST, HSN, total sab auto. Print, PDF ya seedha WhatsApp par bhejo, UPI QR ke saath.</p>
""",
    },
    "dukaan-ka-hisaab-kaise-rakhe": {
        "title": "Dukaan Ka Hisaab App Se Kaise Rakhe | Digital Munshi",
        "desc": "Dukaan ka roz ka hisaab, udhaar/khata, stock aur bikri — mobile app se aasan tarika. Kirana, wholesale sabke liye.",
        "h1": "Dukaan Ka Hisaab App Se Kaise Rakhe",
        "html": """
<p>Register/copy me hisaab rakhna purana tarika hai — udhaar bhool jaate hain, stock ka pata nahi chalta. App se ye sab automatic ho jata hai.</p>
<h2>1. Har bikri turant record</h2>
<p>Barcode scan ya item choose karke bill banao. Har sale apne aap hisaab me chadh jaati hai.</p>
<h2>2. Udhaar / Khata</h2>
<p>Kisne kitna udhaar liya, kab dena hai — sab track. Payment reminder WhatsApp par bhej sakte ho.</p>
<h2>3. Stock aur alert</h2>
<p>Maal kam hone par app alert deta hai. Dead stock (jo nahi bik raha) bhi pata chalta hai.</p>
<h2>4. Roz ka summary</h2>
<p>Har shaam aaj ki bikri, cash, top item ka summary — email par automatic. Digital Munshi se ye sab ek app me.</p>
""",
    },
    "eway-bill-kya-hai": {
        "title": "E-Way Bill Kya Hai — Kab Zaroori Hai? | Digital Munshi",
        "desc": "E-way bill kya hota hai, kab banana zaroori hai (Rs 50,000+), aur software se JSON kaise ready karein.",
        "h1": "E-Way Bill Kya Hai aur Kab Zaroori Hai",
        "html": """
<p>E-way bill ek electronic document hai jo goods ki movement ke liye chahiye jab value ek limit se zyada ho.</p>
<h2>Kab zaroori hai?</h2>
<p>Jab ek consignment ki value <b>Rs 50,000 se zyada</b> ho aur goods ek jagah se doosri jagah ja rahe ho — tab e-way bill banana zaroori hai.</p>
<h2>Kya chahiye?</h2>
<ul>
<li>Invoice / bill of supply</li>
<li>Transporter ID ya vehicle number</li>
<li>HSN code, value, GSTIN details</li>
</ul>
<h2>Software se aasan</h2>
<p>Digital Munshi invoice se seedha <b>e-way bill JSON</b> generate kar deta hai jo portal par upload-ready hota hai — manually type karne ki zaroorat nahi.</p>
""",
    },
}
