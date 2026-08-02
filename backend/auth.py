"""
Small token-based auth layer.

On login, the server hands back a signed token containing the user's id,
email and role. The frontend sends that token back in an
`Authorization: Bearer <token>` header on requests that need it, and
`require_role()` verifies the signature and role server-side before an
endpoint runs. A token can't be forged or edited by the client the way a
value in localStorage can, so setting `role` to "admin" in the browser
no longer gets anyone into the admin endpoints.
"""

import os
from functools import wraps

from flask import jsonify, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

# In production this must be set via an environment variable and kept
# secret. The fallback below is fine for local development only.
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-secret-change-me")
TOKEN_MAX_AGE_SECONDS = 60 * 60 * 12  # 12 hours

_serializer = URLSafeTimedSerializer(SECRET_KEY, salt="hostel-finder-auth")


def issue_token(user):
    payload = {
        "user_id": user.get("_id"),
        "email": user.get("email"),
        "role": user.get("role", "student"),
    }
    return _serializer.dumps(payload)


def _decode_token(token):
    return _serializer.loads(token, max_age=TOKEN_MAX_AGE_SECONDS)


def get_current_user():
    """Returns the decoded token payload for the current request, or None."""
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    token = header[len("Bearer "):].strip()
    try:
        return _decode_token(token)
    except (BadSignature, SignatureExpired):
        return None


def require_role(*allowed_roles):
    """Decorator: reject the request unless it carries a valid token for
    one of the allowed roles."""

    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            payload = get_current_user()
            if payload is None:
                return jsonify({"error": "Login required"}), 401
            if payload.get("role") not in allowed_roles:
                return jsonify({"error": "Not authorized"}), 403
            return view_func(*args, **kwargs)

        return wrapped

    return decorator
