"""
Security helpers: signed API tokens and basic rate limiting.
"""
from __future__ import annotations

import secrets
import time
from typing import Dict, List

from flask import current_app, jsonify, request, session
from flask_login import current_user
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer


_FAILED_LOGINS: Dict[str, List[float]] = {}


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="api-token")


def _ensure_nonce() -> str:
    if "api_token_nonce" not in session:
        session["api_token_nonce"] = secrets.token_urlsafe(16)
    return session["api_token_nonce"]


def get_api_token() -> str | None:
    if not current_user.is_authenticated:
        return None
    nonce = _ensure_nonce()
    payload = {"uid": current_user.id, "nonce": nonce}
    return _serializer().dumps(payload)


def verify_api_token(token: str, max_age_seconds: int = 6 * 60 * 60) -> bool:
    if not token or not current_user.is_authenticated:
        return False
    try:
        data = _serializer().loads(token, max_age=max_age_seconds)
    except (BadSignature, SignatureExpired):
        return False
    if data.get("uid") != current_user.id:
        return False
    if data.get("nonce") != session.get("api_token_nonce"):
        return False
    return True


def api_token_required():
    """
    Decorator for JSON endpoints to require a signed API token.
    Reads token from `X-API-Token` header or `api_token` field in JSON body.
    """
    def decorator(fn):
        def wrapper(*args, **kwargs):
            token = request.headers.get("X-API-Token")
            if not token and request.is_json:
                token = (request.get_json(silent=True) or {}).get("api_token")
            if not verify_api_token(token or ""):
                return jsonify({"error": "Invalid or missing API token"}), 403
            return fn(*args, **kwargs)
        wrapper.__name__ = fn.__name__
        return wrapper
    return decorator


def rate_limit_check(ip: str, limit: int = 5, window_seconds: int = 15 * 60) -> bool:
    """Returns True if request is allowed, False if rate limited."""
    now = time.time()
    attempts = _FAILED_LOGINS.get(ip, [])
    attempts = [t for t in attempts if now - t < window_seconds]
    _FAILED_LOGINS[ip] = attempts
    return len(attempts) < limit


def record_failed_login(ip: str) -> None:
    _FAILED_LOGINS.setdefault(ip, []).append(time.time())


def clear_failed_login(ip: str) -> None:
    _FAILED_LOGINS.pop(ip, None)
