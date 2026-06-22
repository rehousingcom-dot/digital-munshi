"""Gunicorn config for Railway.

Railway's internal/private network is IPv6. The edge proxy reaches the
container over IPv6, so gunicorn MUST listen on IPv6 (``[::]``) or Railway
can't connect -> 502 "Application failed to respond". ``[::]`` is a
dual-stack socket: it accepts both IPv6 and IPv4. PORT is provided by
Railway in the environment; we read it in Python (no shell $PORT needed)."""
import os

_port = os.environ.get("PORT", "8080")
bind = f"[::]:{_port}"
workers = int(os.environ.get("WEB_CONCURRENCY", "2"))
timeout = 120
# Log to stdout/stderr so Railway captures it
accesslog = "-"
errorlog = "-"
loglevel = "info"
# Trust Railway's proxy headers
forwarded_allow_ips = "*"
