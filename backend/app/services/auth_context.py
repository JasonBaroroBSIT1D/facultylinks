import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import g, jsonify, request, session

from app.extensions import db
from app.models import User, UserRole, UserSession
from app.services.passwords import verify_password


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def authenticate_credentials(email: str, password: str) -> User | None:
    user = User.query.filter_by(email=email.strip().lower()).first()
    if not user or not user.is_active:
        return None
    if not verify_password(user.password_hash, password):
        return None
    if user.role == UserRole.faculty:
        # Faculty must use mobile client header for now
        client = (request.headers.get("X-Client-Type") or "").lower()
        if client != "faculty_mobile":
            return None
    if user.role in (UserRole.admin, UserRole.reviewer):
        client = (request.headers.get("X-Client-Type") or "").lower()
        if client == "faculty_mobile":
            return None
    return user


def issue_api_token(user: User, ttl_hours: int) -> str:
    raw = secrets.token_urlsafe(32)
    row = UserSession(
        user_id=user.id,
        token_hash=_hash_token(raw),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=ttl_hours),
    )
    db.session.add(row)
    db.session.commit()
    return raw


def revoke_api_token(raw_token: str) -> None:
    h = _hash_token(raw_token)
    UserSession.query.filter_by(token_hash=h).delete()
    db.session.commit()


def revoke_other_api_sessions(user: User, keep_raw_token: str | None = None) -> None:
    q = UserSession.query.filter_by(user_id=user.id)
    if keep_raw_token:
        keep_h = _hash_token(keep_raw_token)
        q = q.filter(UserSession.token_hash != keep_h)
    q.delete(synchronize_session=False)
    db.session.commit()


def _user_from_bearer() -> User | None:
    auth = request.headers.get("Authorization", "")
    if not auth.lower().startswith("bearer "):
        return None
    raw = auth[7:].strip()
    if not raw:
        return None
    h = _hash_token(raw)
    row = (
        UserSession.query.filter_by(token_hash=h)
        .filter(UserSession.expires_at > datetime.now(timezone.utc))
        .first()
    )
    return row.user if row else None


_CACHED_USER = object()


def current_user() -> User | None:
    cached = getattr(g, "_current_user", _CACHED_USER)
    if cached is not _CACHED_USER:
        return None if cached is False else cached
    user = _user_from_bearer()
    if not user:
        uid = session.get("user_id")
        if uid:
            user = db.session.get(User, uid)
    g._current_user = user if user and user.is_active else None
    if g._current_user is None:
        g._current_user = False
    return g._current_user if g._current_user is not False else None


def login_user_web(user: User) -> None:
    session.clear()
    session["user_id"] = user.id
    session.permanent = True


def logout_user_all(user: User) -> None:
    try:
        if session.get("user_id") == user.id:
            session.clear()
    except RuntimeError:
        # No Flask request context (CLI / background jobs) — only revoke API tokens.
        pass
    UserSession.query.filter_by(user_id=user.id).delete()
    db.session.commit()


def require_roles(*roles: UserRole):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = current_user()
            if not user or user.role not in roles:
                return jsonify({"error": "Forbidden"}), 403
            if user.must_change_password:
                return (
                    jsonify(
                        {
                            "error": "Password change required.",
                            "code": "MUST_CHANGE_PASSWORD",
                        }
                    ),
                    403,
                )
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def require_authenticated(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user:
            return jsonify({"error": "Not authenticated."}), 401
        return fn(*args, **kwargs)

    return wrapper


def faculty_may_access_document(user: User, owner_user_id: int) -> bool:
    if user.role == UserRole.admin:
        return True
    if user.role == UserRole.faculty:
        return user.id == owner_user_id
    if user.role == UserRole.reviewer:
        from app.models import ReviewerAssignment

        return (
            ReviewerAssignment.query.filter_by(
                reviewer_user_id=user.id,
                faculty_user_id=owner_user_id,
            ).first()
            is not None
        )
    return False
