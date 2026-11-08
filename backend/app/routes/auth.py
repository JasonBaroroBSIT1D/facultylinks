from flask import Blueprint, current_app, jsonify, request

from app.extensions import db
from app.models import UserRole
from app.services.account_provisioning import resend_credentials
from app.services.auth_context import (
    authenticate_credentials,
    current_user,
    issue_api_token,
    login_user_web,
    logout_user_all,
    require_authenticated,
    require_roles,
    revoke_api_token,
    revoke_other_api_sessions,
)
from app.services.password_policy import validate_new_password
from app.services.password_recovery import (
    complete_password_reset,
    request_recovery_code,
    verify_recovery_code,
)
from app.services.passwords import hash_password, verify_password

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
        token = issue_api_token(user, current_app.config["API_TOKEN_TTL_HOURS"])
        body["token"] = token
        body["email"] = user.email
    else:
        login_user_web(user)

    return jsonify(body)


@bp.get("/api/auth/me")
@require_authenticated
def me():
    user = current_user()
    assert user
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


@bp.post("/api/auth/change-password")
@require_authenticated
def change_password():
    user = current_user()
    assert user
    data = request.get_json(silent=True) or {}
    new_pw = data.get("newPassword") or ""
    confirm = data.get("confirmPassword") or ""
    err = validate_new_password(new_pw, confirm)
    if err:
        return jsonify({"error": err}), 400
    if verify_password(user.password_hash, new_pw):
        return jsonify({"error": "Your new password must be different from your current password."}), 400

    user.password_hash = hash_password(new_pw)
    user.must_change_password = False
    db.session.commit()

    client = (request.headers.get("X-Client-Type") or "web").lower()
    body = {"ok": True, "user": user.to_public_dict()}

    if client == "faculty_mobile":
        old = ""
        auth = request.headers.get("Authorization", "")
        if auth.lower().startswith("bearer "):
            old = auth[7:].strip()
        revoke_other_api_sessions(user, keep_raw_token=old or None)
        new_token = issue_api_token(user, current_app.config["API_TOKEN_TTL_HOURS"])
        if old:
            revoke_api_token(old)
        body["token"] = new_token
    else:
        revoke_other_api_sessions(user)

    return jsonify(body)


@bp.post("/api/auth/password-recovery/request")
def recovery_request():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()
    if not email or "@" not in email:
        return jsonify({"error": "Enter a valid email address."}), 400
    result = request_recovery_code(email)
    return jsonify(result)


@bp.post("/api/auth/password-recovery/verify")
def recovery_verify():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()
    code = data.get("code") or ""
    if not email:
        return jsonify({"error": "Email is required."}), 400
    result = verify_recovery_code(email, code)
    if not result.get("ok"):
        return jsonify({"error": result.get("error") or "Verification failed."}), 400
    return jsonify({"ok": True, "resetToken": result["resetToken"]})


@bp.post("/api/auth/password-recovery/complete")
def recovery_complete():
    data = request.get_json(silent=True) or {}
    token = data.get("resetToken") or ""
    password = data.get("newPassword") or ""
    confirm = data.get("confirmPassword") or ""
    if not token:
        return jsonify({"error": "Reset authorization is required."}), 400
    result = complete_password_reset(token, password, confirm)
    if not result.get("ok"):
        return jsonify({"error": result.get("error") or "Reset failed."}), 400
    return jsonify({"ok": True, "message": result.get("message")})


@bp.post("/api/admin/faculty/<portal_id>/resend-credentials")
@require_roles(UserRole.admin)
def resend_faculty_credentials(portal_id: str):
    from app.services.portal_state import parse_portal_user_id

    uid = parse_portal_user_id(portal_id)
    if not uid:
        return jsonify({"error": "Invalid id."}), 400
    from app.models import User

    faculty = User.query.filter_by(id=uid, role=UserRole.faculty).first()
    if not faculty:
        return jsonify({"error": "Not found."}), 404
    _, delivery = resend_credentials(faculty)
    from app.services.activity import log_activity
    from app.services.portal_state import reviewer_id_for_faculty

    actor = current_user()
    log_activity(actor.email, f"Credential email resent for faculty: {faculty.full_name}")
    return jsonify(
        {
            "faculty": faculty.to_faculty_dict(reviewer_id_for_faculty(faculty.id)),
            "emailDelivery": delivery,
        }
    )


@bp.post("/api/admin/reviewers/<portal_id>/resend-credentials")
@require_roles(UserRole.admin)
def resend_reviewer_credentials(portal_id: str):
    from app.services.portal_state import parse_portal_user_id, assigned_faculty_ids

    uid = parse_portal_user_id(portal_id)
    if not uid:
        return jsonify({"error": "Invalid id."}), 400
    from app.models import User

    reviewer = User.query.filter_by(id=uid, role=UserRole.reviewer).first()
    if not reviewer:
        return jsonify({"error": "Not found."}), 404
    _, delivery = resend_credentials(reviewer)
    from app.services.activity import log_activity

    actor = current_user()
    log_activity(actor.email, f"Credential email resent for reviewer: {reviewer.full_name}")
    return jsonify(
        {
            "reviewer": reviewer.to_reviewer_dict(assigned_faculty_ids(reviewer.id)),
            "emailDelivery": delivery,
        }
    )
