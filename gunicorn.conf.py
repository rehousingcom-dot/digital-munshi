"""Gunicorn config — reads PORT from environment in Python so we never depend
on shell variable expansion (Railway/Heroku-style $PORT). Bulletproof."""
import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
workers = int(os.environ.get("WEB_CONCURRENCY", "3"))
timeout = 120
