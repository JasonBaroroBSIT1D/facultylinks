import uuid

from flask import Blueprint, current_app, jsonify, request

from app.extensions import db
from app.models import Document, FacultyAssessment, UserRole
from app.services.auth_context import current_user, faculty_may_access_document, require_roles
from app.services.assessment_sync import attach_upload_to_assessment, supersede_prior_documents
from app.services.catalog import (
    CatalogValidationError,
    document_kind_for_set_sef_indicator,
    get_catalog_for_assessment,
    get_published_catalog_and_weights,
    is_kra_i_achievement_indicator,
    is_set_sef_pdf_upload,
    validate_indicator_kra,
)
from app.services.set_sef_processor import enqueue_set_sef_job
from app.services.storage import (
    StorageNotConfiguredError,
    build_object_key,
    delete_private_file,
    presigned_get_url,
    upload_private_file,
)

bp = Blueprint("documents", __name__)


@bp.post("/api/documents")
@require_roles(UserRole.faculty)
def upload_document():
    user = current_user()
    assert user
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"error": "No file provided."}), 400

    mime = (f.mimetype or "application/octet-stream").split(";")[0].strip().lower()
    allowed = current_app.config["ALLOWED_UPLOAD_MIME"]
    if mime not in allowed:
        return jsonify({"error": "File type not allowed."}), 400

    f.stream.seek(0, 2)
    size = f.stream.tell()
    f.stream.seek(0)
    max_bytes = current_app.config["MAX_UPLOAD_BYTES"]
    if size <= 0 or size > max_bytes:
        return jsonify({"error": "File exceeds size limit."}), 400

    indicator_id = (request.form.get("indicatorId") or request.form.get("indicator_id") or "").strip() or None
    kra_id = (request.form.get("kraId") or request.form.get("kra_id") or "").strip() or None
    row = FacultyAssessment.query.get(user.id)
    assessment_data = row.data if row else {}
    catalog, _weights = get_catalog_for_assessment(assessment_data)
    if not catalog:
        catalog, _weights = get_published_catalog_and_weights()
    if not catalog:
        return jsonify({"error": "Scoring configuration is not published yet."}), 503
    try:
        validate_indicator_kra(catalog, indicator_id or "", kra_id or "")
    except CatalogValidationError as exc:
        return jsonify({"error": str(exc)}), 400

    is_set_sef_pdf = is_set_sef_pdf_upload(indicator_id, kra_id)
    if is_set_sef_pdf and mime != "application/pdf":
        return jsonify({"error": "SET/SEF PDF evidence must be a PDF file."}), 400

    est_raw = request.form.get("estimatedPoints")
    estimated_points = float(est_raw) if est_raw not in (None, "") and not is_set_sef_pdf else None
    title = (request.form.get("title") or "").strip() or None

    doc = Document(
        public_id=str(uuid.uuid4()),
        owner_user_id=user.id,
        object_key=build_object_key(user.id, f.filename),
        original_filename=f.filename,
        mime_type=mime,
        size_bytes=size,
        upload_status="pending",
        indicator_id=indicator_id,
        kra_id=kra_id,
        review_status="evidence" if is_kra_i_achievement_indicator(indicator_id) else "pending",
        estimated_points=estimated_points,
        document_kind=document_kind_for_set_sef_indicator(indicator_id or "") if is_set_sef_pdf else None,
        ocr_status="pending" if is_set_sef_pdf else "none",
        processing_status="queued" if is_set_sef_pdf else "none",
    )
    db.session.add(doc)
    db.session.flush()
    achievement_evidence = is_kra_i_achievement_indicator(indicator_id)
    if not achievement_evidence:
        supersede_prior_documents(user.id, indicator_id, doc.public_id)

    try:
        upload_private_file(key=doc.object_key, stream=f.stream, mime_type=mime, size=size)
        doc.upload_status = "stored"
        if not achievement_evidence:
            attach_upload_to_assessment(doc, title=title, estimated_points=estimated_points)
        if is_set_sef_pdf:
            enqueue_set_sef_job(doc)
        db.session.commit()
    except StorageNotConfiguredError:
        db.session.rollback()
        return jsonify({"error": "Document storage is not configured on the server."}), 503
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Upload failed."}), 500

    return jsonify({"document": doc.to_dict()}), 201


@bp.get("/api/documents")
def list_documents():
    user = current_user()
    if not user:
        return jsonify({"error": "Not authenticated."}), 401

    if user.role == UserRole.faculty:
        docs = Document.query.filter_by(owner_user_id=user.id).order_by(Document.created_at.desc()).all()
    elif user.role == UserRole.admin:
        docs = Document.query.order_by(Document.created_at.desc()).limit(200).all()
    else:
        from app.models import ReviewerAssignment

        faculty_ids = [
            a.faculty_user_id
            for a in ReviewerAssignment.query.filter_by(reviewer_user_id=user.id).all()
        ]
        if not faculty_ids:
            docs = []
        else:
            docs = (
                Document.query.filter(Document.owner_user_id.in_(faculty_ids))
                .order_by(Document.created_at.desc())
                .all()
            )

    from app.services.document_achievement_display import (
        achievement_links_for_user,
        enrich_document_dict_for_achievements,
    )

    links_by_doc: dict[str, list] = {}
    if user.role == UserRole.faculty:
        links_by_doc = achievement_links_for_user(user.id)
    owner_link_cache: dict[int, dict[str, list]] = {}
    payload = []
    for d in docs:
        base = d.to_dict()
        if user.role == UserRole.faculty:
            links = links_by_doc.get(d.public_id, [])
        elif user.role == UserRole.admin:
            links = []
        else:
            if d.owner_user_id not in owner_link_cache:
                owner_link_cache[d.owner_user_id] = achievement_links_for_user(d.owner_user_id)
            links = owner_link_cache[d.owner_user_id].get(d.public_id, [])
        payload.append(enrich_document_dict_for_achievements(base, links))
    return jsonify({"documents": payload})


@bp.get("/api/documents/<public_id>/view-url")
def document_view_url(public_id: str):
    user = current_user()
    if not user:
        return jsonify({"error": "Not authenticated."}), 401

    doc = Document.query.filter_by(public_id=public_id, upload_status="stored").first()
    if not doc:
        return jsonify({"error": "Not found."}), 404

    if not faculty_may_access_document(user, doc.owner_user_id):
        return jsonify({"error": "Forbidden."}), 403

    try:
        url = presigned_get_url(doc.object_key, expires_in=300)
    except StorageNotConfiguredError:
        return jsonify({"error": "Storage not configured."}), 503

    from app.services.document_achievement_display import (
        achievement_links_for_user,
        enrich_document_dict_for_achievements,
    )

    links = achievement_links_for_user(doc.owner_user_id).get(doc.public_id, [])
    doc_payload = enrich_document_dict_for_achievements(doc.to_dict(), links)
    return jsonify({"url": url, "expiresInSeconds": 300, "document": doc_payload})


@bp.delete("/api/documents/<public_id>")
@require_roles(UserRole.faculty)
def delete_document(public_id: str):
    user = current_user()
    doc = Document.query.filter_by(public_id=public_id, owner_user_id=user.id).first()
    if not doc:
        return jsonify({"error": "Not found."}), 404
    key = doc.object_key
    db.session.delete(doc)
    db.session.commit()
    delete_private_file(key)
    return jsonify({"ok": True})
