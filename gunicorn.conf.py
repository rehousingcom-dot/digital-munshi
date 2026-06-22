"""Gunicorn config for Railway.

Railway's internal network is IPv6 — gunicorn MUST listen on ``[::]`` (a
dual-stack socket that accepts both IPv6 and IPv4) or Railway's edge proxy
can't connect -> 502 "Application failed to respond".

We bind a FIXED port 8080 (matching Dockerfile EXPOSE and Railway's target
port) so there is zero ambiguity about which port Railway should route to.
PORT env (if Railway sets it) overrides, but defaults to 8080."""
import os

# Fixed 8080 — matches Dockerfile EXPOSE and Railway's target port. We do NOT
# read $PORT so there is exactly one port everyone agrees on.
bind = "[::]:8080"
workers = int(os.environ.get("WEB_CONCURRENCY", "1"))
timeout = 120
accesslog = "-"
errorlog = "-"
loglevel = "info"
forwarded_allow_ips = "*"
