"""Time PATCH /set-sef/semesters steps (local; uses configured DATABASE_URL)."""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models import Document, SetSefSemesterRecord, User
from app.routes.set_sef import _active_semester_records, _scoring_bundle
from app.services.activity import log_activity
from app.services.auth_context import faculty_may_access_document
from wsgi import app

DOC_PUBLIC = sys.argv[1] if len(sys.argv) > 1 else "4dbd48ca-a190-4579-87aa-ca251f16b35c"
REVIEWER_EMAIL = sys.argv[2] if len(sys.argv) > 2 else "jaso.jary@gmail.com"


def _ms(t0: float) -> float:
    return round((time.perf_counter() - t0) * 1000, 2)


def run_once(*, commit: bool) -> dict[str, float]:
    timings: dict[str, float] = {}
    t_total = time.perf_counter()

    t = time.perf_counter()
    with app.app_context():
        actor = User.query.filter_by(email=REVIEWER_EMAIL).first()
        timings["auth_user_lookup"] = _ms(t)

        t = time.perf_counter()
        doc = Document.query.options(joinedload(Document.owner)).filter_by(public_id=DOC_PUBLIC).first()
        timings["load_document"] = _ms(t)

        t = time.perf_counter()
        ok = faculty_may_access_document(actor, doc.owner_user_id)
        timings["access_check"] = _ms(t)
        assert ok

        t = time.perf_counter()
        rec = SetSefSemesterRecord.query.filter_by(
            document_id=doc.id, superseded_by_id=None
        ).order_by(SetSefSemesterRecord.id).first()
        timings["load_record"] = _ms(t)

        t = time.perf_counter()
        if rec.set_rating_confirmed is None and rec.set_rating_extracted is None:
            raise SystemExit("No SET rating on sample record")
        rec.set_verification_status = "pending" if commit else rec.set_verification_status
        timings["validation_mutate"] = _ms(t)

        if commit:
            t = time.perf_counter()
            rec.updated_at = rec.updated_at
            log_activity(actor.email, f"benchmark verify record {rec.id}", commit=False)
            db.session.commit()
            timings["db_commit"] = _ms(t)

        t = time.perf_counter()
        records = _active_semester_records(doc.id)
        timings["load_all_records"] = _ms(t)

        t = time.perf_counter()
        bundle = _scoring_bundle(doc, records)
        timings["scoring_aggregate"] = _ms(t)

        t = time.perf_counter()
        profile = doc.owner.full_name if doc.owner else ""
        payload = {"record": rec.to_dict(profile_name=profile), **bundle}
        _ = payload  # serialize
        timings["serialize"] = _ms(t)

    timings["total"] = _ms(t_total)
    return timings


def main() -> None:
    with app.app_context():
        doc = Document.query.filter_by(public_id=DOC_PUBLIC).first()
        if not doc:
            raise SystemExit(f"Document not found: {DOC_PUBLIC}")
        rec = SetSefSemesterRecord.query.filter_by(document_id=doc.id, superseded_by_id=None).first()
        if not rec:
            raise SystemExit("No semester records")
        rec.set_verification_status = "pending"
        db.session.commit()

    print("PATCH benchmark (reset record to pending, then full verify path)")
    warm = run_once(commit=True)
    for label, ms in warm.items():
        print(f"  {label}: {ms} ms")

    print("\nSecond run (already verified; commit + scoring only):")
    rec2 = run_once(commit=True)
    print(f"  total: {rec2['total']} ms (commit {rec2.get('db_commit')} ms)")


if __name__ == "__main__":
    main()
