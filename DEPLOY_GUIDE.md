# Digital Munshi ERP — Cloud Deploy Guide (Render / Railway)

Yeh guide app ko **internet pe live** karne ke liye hai. Ek baar deploy → har client browser/desktop se login karke use karega. Update/backup/subscription sab automatic.

> Pehle ek **GitHub account** chahiye + code GitHub pe push hona chahiye (private repo theek hai).

---

## Option A — Render.com (Recommended, sabse aasaan)

Render free PostgreSQL + auto-deploy deta hai. `render.yaml` already bana hai (one-click blueprint).

### Steps
1. **GitHub pe code daalo:**
   ```bash
   cd ~/"ERP Munshi"
   git init && git add -A && git commit -m "Digital Munshi ERP"
   # GitHub pe naya private repo banao, phir:
   git remote add origin https://github.com/<aapka-user>/digital-munshi.git
   git push -u origin main
   ```
   > `.gitignore` mein `.env`, `db.sqlite3`, `media/`, `staticfiles/`, `.venv/` zaroor ho (taaki secrets/local data push na ho).

2. **Render pe jao** → [render.com](https://render.com) → sign up (GitHub se) → **New → Blueprint** → apna repo choose karo.
3. Render `render.yaml` padh ke **web service + PostgreSQL** dono bana dega. **Apply** dabao.
4. Deploy ke baad **ALLOWED_HOSTS** update karo — service ka URL (jaise `digital-munshi.onrender.com`) Render dashboard → Environment mein daalo → redeploy.
5. **Pehla admin banao** — Render dashboard → service → **Shell** → ye chalao:
   ```bash
   python manage.py createsuperuser
   python manage.py seed_plans        # subscription plans (agar command hai)
   ```
6. Done! `https://digital-munshi.onrender.com` pe app live. Signup se naye business ban sakte hain.

**Cost:** Web starter ~$7/mo + DB basic ~$1-7/mo. (Free plan bhi hai par 15 min baad "sleep" ho jata hai — testing ke liye theek.)

---

## Option B — Railway.app

1. Code GitHub pe (upar jaisa).
2. [railway.app](https://railway.app) → **New Project → Deploy from GitHub repo**.
3. **+ New → Database → PostgreSQL** add karo. Railway khud `DATABASE_URL` inject karta hai.
4. Service → **Variables** mein set karo:
   - `SECRET_KEY` = (lambi random string)
   - `DEBUG` = `False`
   - `ALLOWED_HOSTS` = `<your-app>.up.railway.app`
5. Railway `Procfile` se khud `migrate + collectstatic + gunicorn` chala lega.
6. Deploy ke baad Shell se `createsuperuser`.

**Cost:** ~$5 usage-based se shuru.

---

## Deploy ke baad checklist

- [ ] `https://<domain>/` → login screen khulta hai
- [ ] `https://<domain>/admin/` → Django admin (superuser se)
- [ ] Naya signup → trial milta hai, billing chalti hai
- [ ] Invoice print, WhatsApp share kaam karta hai
- [ ] **Custom domain** add karo (Render/Railway → Settings → Custom Domain → `app.aapkadomain.in`) + DNS CNAME
- [ ] **HTTPS** automatic milta hai (Render/Railway free SSL dete hain)

## Production mein real keys (jab chahiye)

Environment variables mein daalo (code mein nahi):
- `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET` — asli payment
- `GSTIN_API_KEY` — GSTIN auto-fill (Appyflow/MasterGST)
- `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` — invoice email
- WhatsApp Cloud API token — Settings se ya env se

## Backups (zaroori)
- Render/Railway managed PostgreSQL **automatic daily backup** deta hai (plan ke hisaab se).
- Extra safety: hafte mein ek baar DB export download kar lo.

## Updates (kitna aasaan)
- Code change → GitHub pe `git push` → Render/Railway **automatically naya version deploy** kar deta hai. Saare clients ko turant mil jata hai. **Koi client ko kuch nahi karna padta** (cloud ka sabse bada fayda).

---
*Sawaal ho to poochho — main har step pe help karunga.*
