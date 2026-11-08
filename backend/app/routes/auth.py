from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models import UserRole
from app.services.auth_context import (
    authenticate_credentials,
    current_user,
    issue_api_token,
    login_user_web,
    logout_user_all,
    revoke_api_token,
)

bp = Blueprint("auth", __name__)


@bp.post("/api/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    user = authenticate_credentials(email, password)
    if not user:
        return jsonify({"error": "Invalid email or password."}), 401

    client = (request.headers.get("X-Client-Type") or "web").lower()
    body = {"user": user.to_public_dict()}

    if client == "faculty_mobile":
        from flask import current_app

        token = issue_api_token(user, current_app.config["API_TOKEN_TTL_HOURS"])
        body["token"] = token
        body["email"] = user.email
    else:
        login_user_web(user)

    return jsonify(body)


@bp.get("/api/auth/me")
def me():
    user = current_user()
    if not user:
        return jsonify({"error": "Not authenticated."}), 401
    return jsonify({"user": user.to_public_dict()})


@bp.post("/api/auth/logout")
def logout():
    user = current_user()
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        revoke_api_token(auth[7:].strip())
    if user:
        logout_user_all(user)
    else:
        from flask import session

        session.clear()
    return jsonify({"ok": True})
