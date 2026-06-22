# Digital Munshi — Desktop App

Humari web app ko ek **native desktop app** (Mac / Windows / Linux) mein chalata hai (Electron).
Sab UI/feature reuse hote hain + ek bonus: **WhatsApp Web** alag window mein (QR scan karke documents bhejein).

## Pehle: Node.js chahiye
Desktop app banane ke liye Node.js zaroori hai. Check: `node --version`
Agar nahi hai → https://nodejs.org se LTS install karein (ya `brew install node`).

## Chalana (development)
```bash
# 1. Pehle Django server chalu rakhein (dusre terminal mein):
cd ~/"ERP Munshi" && source .venv/bin/activate && python manage.py runserver

# 2. Desktop app:
cd ~/"ERP Munshi/desktop"
npm install        # pehli baar (Electron download ~ thoda time lagega)
npm start
```
Ek native window khulega jisme poora Digital Munshi chalega. Menu mein **WhatsApp → Open WhatsApp Web**
se WhatsApp Web alag window mein khol ke QR scan kar sakte hain.

## Installable app banana (.dmg / .exe)
```bash
npm run build:mac     # Mac .dmg + .zip   (dist/ folder mein)
npm run build:win     # Windows installer
npm run build:linux   # Linux AppImage
```
> Mac/Windows pe distribution ke liye code-signing chahiye hota hai (Apple Developer / Windows cert),
> par apne use ke liye `npm start` ya unsigned build kaafi hai.

## Cloud server se connect (production)
Backend cloud pe deploy karne ke baad:
```bash
DM_SERVER_URL="https://app.aapkadomain.com/" npm start
```
Phir desktop app local server ke bajaye cloud se connect hoga — har computer pe bas app install,
server kahin nahi chalana.

## Aage (roadmap)
- App icon + splash screen
- Auto-update (electron-updater)
- Native thermal printer + barcode scanner integration (preload.js se)
- Offline cache
