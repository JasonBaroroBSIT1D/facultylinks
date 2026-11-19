import io
import uuid

from flask import Blueprint, current_app, jsonify, request
from werkzeug.datastructures import FileStorage

from app.extensions import db
from app.models import Document, FacultyAssessment, UserRole
from app.services.auth_context import current_user, faculty_may_access_document, require_roles
from app.services.assessment_sync import attach_upload_to_assessment, supersede_prior_documents
from app.services.document_correction import (
    REVIEW_CORRECTION_PREPARED,
    apply_document_replacement,
    faculty_may_replace_document,
    finalize_replacement_assessment,
    resubmit_document_for_review,
    swap_achievement_document_reference,
)
from app.services.catalog import (
    CatalogValidationError,
    document_kind_for_set_sef_indicator,
    get_catalog_for_assessment,
    get_published_catalog_and_weights,
    is_kra_i_achievement_indicator,
    is_set_sef_pdf_upload,
    validate_indicator_kra,
)
from app.services.document_ocr_processor import enqueue_general_ocr_job
from app.services.document_text import IMAGE_MIME, supports_general_ocr
from app.services.set_sef_processor import enqueue_set_sef_job
from app.services.storage import (
    StorageNotConfiguredError,
    build_object_key,
    delete_private_file,
    presigned_get_url,
    upload_private_file,
)

bp = Blueprint("documents", __name__)


def _read_upload(fs: FileStorage) -> tuple[bytes, str, str]:
    mime = (fs.mimetype or "application/octet-stream").split(";")[0].strip().lower()
    data = fs.read()
    name = (fs.filename or "upload.bin").strip() or "upload.bin"
    return data, mime, name


def _images_to_pdf_bytes(image_blobs: list[bytes]) -> bytes:
    """Archive multi-page camera scans as one PDF. OCR still runs on image-based pages."""
    import fitz
    from PIL import Image

    out = fitz.open()
    try:
        for blob in image_blobs:
            img = Image.open(io.BytesIO(blob))
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            width, height = img.size
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=90)
            jpeg = buf.getvalue()
            page = out.new_page(width=float(width), height=float(height))
            page.insert_image(page.rect, stream=jpeg)
        return out.tobytes()
    finally:
        out.close()


@bp.post("/api/documents")
@require_roles(UserRole.faculty)
def upload_document():
    user = current_user()
    assert user

    page_files = [p for p in request.files.getlist("pages") if p and p.filename]
    single = request.files.get("file")
    if not page_files and (not single or not single.filename):
        return jsonify({"error": "No file provided."}), 400

    allowed = current_app.config["ALLOWED_UPLOAD_MIME"]
    max_bytes = current_app.config["MAX_UPLOAD_BYTES"]

    indicator_id = (request.form.get("indicatorId") or request.form.get("indicator_id") or "").strip() or None
    kra_id = (request.form.get("kraId") or request.form.get("kra_id") or "").strip() or None
    criterion_id = (
        request.form.get("criterionId") or request.form.get("criterion_id") or ""
    ).strip() or None
    row = FacultyAssessment.query.get(user.id)
    assessment_data = row.data if row else {}
    catalog, _weights = get_catalog_for_assessment(assessment_data)
    if not catalog:
        catalog, _weights = get_published_catalog_and_weights()
    if not catalog:
        return jsonify({"error": "Scoring configuration is not published yet."}), 503
    try:
        found = validate_indicator_kra(
            catalog,
            indicator_id or "",
            kra_id or "",
            criterion_id=criterion_id,
        )
    except CatalogValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    # Prefer catalog criterion when client omitted criterionId.
    resolved_criterion_id = criterion_id or ((found.get("criterion") or {}).get("id"))
    pinned_version = (assessment_data or {}).get("configVersionId") or (catalog or {}).get("version")

    is_set_sef = is_set_sef_pdf_upload(indicator_id, kra_id)
    set_sef_allowed = frozenset({"application/pdf"}) | IMAGE_MIME

    payloads: list[tuple[bytes, str, str]] = []
    if page_files:
        for fs in page_files:
            data, mime, name = _read_upload(fs)
            if mime not in allowed:
                return jsonify({"error": f"File type not allowed: {mime}"}), 400
            if is_set_sef and mime not in set_sef_allowed:
                return jsonify({"error": "SET/SEF evidence must be a PDF or clear photo/scan (JPEG, PNG, WebP)."}), 400
            if not data or len(data) > max_bytes:
                return jsonify({"error": "File exceeds size limit."}), 400
            payloads.append((data, mime, name))
    else:
        data, mime, name = _read_upload(single)
        if mime not in allowed:
            return jsonify({"error": "File type not allowed."}), 400
        if is_set_sef and mime not in set_sef_allowed:
            return jsonify({"error": "SET/SEF evidence must be a PDF or clear photo/scan (JPEG, PNG, WebP)."}), 400
        if not data or len(data) > max_bytes:
            return jsonify({"error": "File exceeds size limit."}), 400
        payloads.append((data, mime, name))

    # Multi-page camera scan → one archived PDF (image pages have no embedded text;
    # SET/SEF and general OCR pipelines run Tesseract on those pages).
    if len(payloads) > 1:
        if any(m == "application/pdf" for _, m, _ in payloads):
            return jsonify({"error": "Multi-page upload accepts photos/scans only (not mixed with PDF)."}), 400
        if any(m not in IMAGE_MIME and m != "image/jpg" for _, m, _ in payloads):
            return jsonify({"error": "Multi-page upload accepts JPEG, PNG, or WebP photos only."}), 400
        try:
            pdf_bytes = _images_to_pdf_bytes([b for b, _, _ in payloads])
        except Exception:
            return jsonify({"error": "Could not assemble multi-page scan. Try again with clearer photos."}), 400
        if len(pdf_bytes) > max_bytes:
            return jsonify({"error": "Assembled scan exceeds size limit."}), 400
        store_bytes = pdf_bytes
        store_mime = "application/pdf"
        store_name = (request.form.get("title") or "camera_scan").strip() or "camera_scan"
        if not store_name.lower().endswith(".pdf"):
            store_name = f"{store_name}.pdf"
    else:
        store_bytes, store_mime, store_name = payloads[0]

    est_raw = request.form.get("estimatedPoints")
    estimated_points = float(est_raw) if est_raw not in (None, "") and not is_set_sef else None
    title = (request.form.get("title") or "").strip() or None

    doc = Document(
        public_id=str(uuid.uuid4()),
        owner_user_id=user.id,
        object_key=build_object_key(user.id, store_name),
        original_filename=store_name,
        mime_type=store_mime,
        size_bytes=len(store_bytes),
        upload_status="pending",
        indicator_id=indicator_id,
        kra_id=kra_id,
        criterion_id=resolved_criterion_id,
        config_version=str(pinned_version) if pinned_version else None,
        review_status="evidence" if is_kra_i_achievement_indicator(indicator_id) else "pending",
        estimated_points=estimated_points,
        document_kind=document_kind_for_set_sef_indicator(indicator_id or "") if is_set_sef else None,
        ocr_status=(
            "pending"
            if is_set_sef or supports_general_ocr(store_mime)
            else "none"
        ),
        processing_status=(
            "queued"
            if is_set_sef or supports_general_ocr(store_mime)
            else "none"
        ),
    )
    db.session.add(doc)
    db.session.flush()
    achievement_evidence = is_kra_i_achievement_indicator(indicator_id)
    replaces_public_id = (request.form.get("replacesDocumentId") or "").strip() or None
    replaced_prior: Document | None = None
    if replaces_public_id:
        replaced_prior = Document.query.filter_by(
            public_id=replaces_public_id, owner_user_id=user.id, upload_status="stored"
        ).first()
        if not replaced_prior or not faculty_may_replace_document(replaced_prior):
            db.session.rollback()
            return jsonify({"error": "This document cannot be replaced."}), 400
        if replaced_prior.indicator_id and indicator_id and replaced_prior.indicator_id != indicator_id:
            db.session.rollback()
            return jsonify({"error": "Replacement must use the same indicator context."}), 400
        if not indicator_id and replaced_prior.indicator_id:
            indicator_id = replaced_prior.indicator_id
            doc.indicator_id = indicator_id
        if not kra_id and replaced_prior.kra_id:
            kra_id = replaced_prior.kra_id
            doc.kra_id = kra_id
        if not resolved_criterion_id and replaced_prior.criterion_id:
            doc.criterion_id = replaced_prior.criterion_id
        apply_document_replacement(old=replaced_prior, new=doc)
    elif not achievement_evidence and not is_set_sef and request.form.get("replacePrior") == "1":
        # Generic legacy indicator upload (non targeted).
        supersede_prior_documents(user.id, indicator_id, doc.public_id)

    try:
        upload_private_file(
            key=doc.object_key,
            stream=io.BytesIO(store_bytes),
            mime_type=store_mime,
            size=len(store_bytes),
        )
        doc.upload_status = "stored"
        if replaced_prior is not None:
            finalize_replacement_assessment(doc, title=title)
            swap_achievement_document_reference(user.id, replaced_prior.public_id, doc.public_id)
        elif not achievement_evidence:
            attach_upload_to_assessment(doc, title=title, estimated_points=estimated_points)
        if is_set_sef:
            enqueue_set_sef_job(doc)
        else:
            enqueue_general_ocr_job(doc)
        db.session.commit()
    except StorageNotConfiguredError:
        db.session.rollback()
        return jsonify({"error": "Document storage is not configured on the server."}), 503
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Upload failed."}), 500

    payload = doc.to_dict()
    if replaced_prior is not None:
        payload["replacesPublicId"] = replaced_prior.public_id
        payload["canResubmit"] = doc.review_status == REVIEW_CORRECTION_PREPARED
    return jsonify({"document": payload}), 201


@bp.post("/api/documents/<public_id>/resubmit")
@require_roles(UserRole.faculty)
def resubmit_document(public_id: str):
    user = current_user()
    assert user
    doc = Document.query.filter_by(public_id=public_id, owner_user_id=user.id, upload_status="stored").first()
    if not doc:
        return jsonify({"error": "Not found."}), 404
    try:
        resubmit_document_for_review(doc, actor=user)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    if doc.processing_status not in ("queued", "processing", "pending"):
        pass
    db.session.commit()
    return jsonify({"document": {**doc.to_dict(), "canResubmit": False}})


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
