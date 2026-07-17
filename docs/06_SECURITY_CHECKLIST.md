# 06 — Security Checklist (ACTION REQUIRED)

> Yeh cheezein **aapko khud** karni hain (dashboards me login karke). Code se nahi ho
> saktीं. Priority order me hain — 🔴 = turant, 🟠 = jaldi, 🟢 = achha rahega.

---

## 🔴 1. Exposed secrets ROTATE karo (turant)

Purane chat/commits me kuch keys expose ho chuki thीं. Inhe **revoke + naya banao**,
phir naya value **sirf Railway env vars** me daalo (kabhi code/chat me nahi).

| Secret | Kahan rotate kare | Naya value kahan daale |
|---|---|---|
| **GitHub Personal Access Token** (`ghp_…`) | GitHub → Settings → Developer settings → Personal access tokens → **Revoke** purana, naya banao | Railway ko GitHub se deploy ke liye PAT ki zaroorat nahi (OAuth). Agar kahin use hai to wahin update. |
| **Gmail App Password** | Google Account → Security → 2-Step Verification → App passwords → purana **delete**, naya banao | Railway env: `EMAIL_HOST_PASSWORD` |
| **Resend API key** (`re_…`) | resend.com → API Keys → purana **delete**, naya banao | Railway env: `RESEND_API_KEY` (ya jo naam use ho raha hai) |
| **Cloudinary API secret** | cloudinary.com → Settings → Security → **Regenerate** API secret | Railway env: `CLOUDINARY_URL` / `CLOUDINARY_API_SECRET` |

**Rule:** koi bhi secret kabhi bhi chat, GitHub, ya screenshot me mat bhejo. Sirf Railway
→ service → **Variables** tab me.

---

## 🔴 2. Django SECRET_KEY (production)

- `config/settings.py` me fallback hai: `SECRET_KEY = env("SECRET_KEY", default="dev-insecure-key-change-me")`.
- **Confirm karo Railway me `SECRET_KEY` set hai** (ek lamba random string). Agar nahi, to
  session/token security kamzor hai.
- Naya banane ke liye (local terminal):
  ```
  python -c "import secrets; print(secrets.token_urlsafe(64))"
  ```
  → yeh value Railway env `SECRET_KEY` me daalo.

---

## 🔴 3. DEBUG = False on production

- `DEBUG` ki default `True` hai. Production me **`DEBUG=False`** hona chahiye
  (warna error pages me stack-trace + code leak hota hai).
- Railway env: `DEBUG=False` set karo.
- Saath me `ALLOWED_HOSTS` me apne domains daalo:
  `ALLOWED_HOSTS=erp.reloaddigital.in,web-production-9d149.up.railway.app`

---

## 🟠 4. Committee public link — boli privacy (optional, recommend)

- Common public link (`/c/<uuid>/`) par abhi koi bhi dropdown se **kisi bhi member** ke
  naam boli daal sakta hai (verification nahi).
- Sujhav: common page se member-dropdown hata do; boli sirf **personal secure link**
  (`/cm/<token>/`) se ho — jahan identity token se lock hai. (Bol do to main kar dunga.)

---

## 🟠 5. Superuser / admin password

- `/admin/` superuser (**Nkgrewal**) ka password strong hai confirm karo.
- Purane demo/test accounts (jaise `demo@reloaddigital.in`) production me zaroorat na ho
  to disable/delete.

---

## 🟢 6. Backups verify

- Nightly DB backup (Cloudinary) chal raha hai — ek baar **restore test** kar lo (backup
  file actually valid hai ya nahi).
- Railway Postgres ka apna backup/retention bhi enable rakho.

## 🟢 7. Rate-limit / throttle

- DRF throttle laga hai (Wave 1). Login/signup endpoints par brute-force protection
  confirm kar lo (throttle rates settings me).

## 🟢 8. HTTPS / security headers

- `DEBUG=False` hone par production security auto-on hoti hai (HSTS, secure cookies).
- Cloudflare par **SSL: Full (strict)** rakho.

---

### Quick "done" checklist

- [ ] GitHub PAT rotated
- [ ] Gmail app password rotated
- [ ] Resend key rotated
- [ ] Cloudinary secret rotated
- [ ] `SECRET_KEY` set in Railway (random)
- [ ] `DEBUG=False` in Railway
- [ ] `ALLOWED_HOSTS` set
- [ ] Admin password strong
- [ ] Backup restore tested
