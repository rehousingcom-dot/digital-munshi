#!/bin/bash
# Digital Munshi ERP — Mac pe one-command local setup + run.
# Use: chmod +x run_local.sh && ./run_local.sh
set -e
cd "$(dirname "$0")"

echo "==> 1/6  Purane leftover files clean..."
rm -rf .venv db.sqlite3 db.sqlite3-journal 2>/dev/null || true

echo "==> 2/6  Virtual environment + dependencies..."
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo "==> 3/6  .env setup..."
if [ ! -f .env ]; then
  cp .env.example .env
  # random secret key
  KEY=$(python3 -c "import secrets;print(secrets.token_urlsafe(50))")
  python3 - <<PY
import re
s=open('.env').read()
s=re.sub(r'SECRET_KEY=.*', 'SECRET_KEY=$KEY', s)
open('.env','w').write(s)
PY
  echo "    .env banaya (SECRET_KEY auto-set)."
fi

echo "==> 4/6  Database migrate..."
python manage.py migrate

echo "==> 5/6  Plans + demo data seed..."
python manage.py seed_plans
python manage.py seed_demo

echo "==> 6/6  Server start..."
echo ""
echo "  ✓ App:        http://127.0.0.1:8000/"
echo "  ✓ Demo login: demo / demo12345"
echo "  ✓ Admin:      http://127.0.0.1:8000/admin/  (createsuperuser se banao)"
echo ""
python manage.py runserver
