"""Multi-document upload: SET/SEF docs are not auto-superseded by default."""

from app.routes import documents as documents_route


def test_images_to_pdf_helper_available_for_multipage_scan():
    from PIL import Image
    import io

    def jpeg(color):
        img = Image.new("RGB", (40, 40), color=color)
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        return buf.getvalue()

    pdf = documents_route._images_to_pdf_bytes([jpeg((255, 0, 0)), jpeg((0, 255, 0))])
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 100


def test_set_sef_aggregation_flags_conflicting_ratings():
    from app.services.set_sef_aggregation import AggregationConflict, _pick_best
    from app.models import Document, SetSefSemesterRecord
    from decimal import Decimal
    from types import SimpleNamespace

    # Lightweight stand-ins: _pick_best only needs rating fields + document id/created_at.
    rec_a = SimpleNamespace(
        semester_key="2024|1",
        set_rating_extracted=Decimal("4.2"),
        set_rating_confirmed=None,
        set_verification_status="pending",
        sef_rating_extracted=None,
        sef_rating_confirmed=None,
        sef_verification_status="pending",
        document_id=1,
    )
    rec_b = SimpleNamespace(
        semester_key="2024|1",
        set_rating_extracted=Decimal("3.1"),
        set_rating_confirmed=None,
        set_verification_status="pending",
        sef_rating_extracted=None,
        sef_rating_confirmed=None,
        sef_verification_status="pending",
        document_id=2,
    )
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    doc_a = SimpleNamespace(id=1, created_at=now)
    doc_b = SimpleNamespace(id=2, created_at=now)


    winner, conflicts = _pick_best([(rec_a, doc_a), (rec_b, doc_b)], "set")
    assert winner is not None
    assert conflicts
    assert isinstance(conflicts[0], AggregationConflict)
    assert "Conflicting SET" in conflicts[0].explanation
