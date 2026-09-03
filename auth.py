"""
Minimal admin auth: require an X-Admin-Key header matching Config.ADMIN_API_KEY.

This is intentionally simple (no sessions/JWT) since the admin surface here is
a single internal dashboard. If you need per-user admin accounts or audit
trails, swap this for Flask-Login / JWT — but ship *something* before this
goes anywhere reachable from the internet.
"""
from functools import wraps

from flask import request, jsonify

from config import Config


import logging

logger = logging.getLogger("admin_audit")


def require_admin(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        supplied = request.headers.get("X-Admin-Key") or request.args.get("admin_key")
        client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
        if not supplied or supplied != Config.ADMIN_API_KEY:
            logger.warning(
                "UNAUTHORIZED ADMIN ATTEMPT: IP=%s Method=%s Path=%s KeyProvided=%s",
                client_ip, request.method, request.path, bool(supplied)
            )
            return jsonify({"error": "Unauthorized. Provide a valid X-Admin-Key header."}), 401
        
        logger.info(
            "AUTHORIZED ADMIN ACTION: IP=%s Method=%s Path=%s",
            client_ip, request.method, request.path
        )
        return view_func(*args, **kwargs)
    return wrapped
