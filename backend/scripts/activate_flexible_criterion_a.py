"""Publish prepared flexible Criterion A draft and reassign ONE affected faculty.

Mirrors admin UI:
  1) Publish draft (archives previous active published; does not rewrite its catalog blob)
  2) Faculty → Scoring rules → Apply reassignment (audited)

Does not mass-repin other faculty.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from app import create_app
from app.extensions import db
from app.models import FacultyAssessment, SetSefSemesterRecord, User
from app.services.catalog import (
    CRITERION_A_POLICY_FLEXIBLE,
    criterion_a_calculation_params,
    get_assessment_config,
    get_catalog_for_assessment,
    reassign_assessment_config_version,
)
from app.services.settings_store import ASSESSMENT_CONFIG_KEY, CATALOG_PUBLISHED_KEY, set_json

FACULTY_EMAIL = "jasonbaroro4@gmail.com"
DRAFT_ID = "cfg-draft-1794174779956"


def main() -> None:
    app = create_app()
    with app.app_context():
        cfg = get_assessment_config()
        draft = next((v for v in cfg.get("versions") or [] if v.get("id") == DRAFT_ID), None)
        if not draft:
            raise SystemExit(f"Draft {DRAFT_ID} not found")
        if draft.get("status") != "draft":
            print("Draft already", draft.get("status"), "- skipping publish; will reassign if needed")
            new_id = draft["id"] if draft.get("status") == "published" else cfg.get("activePublishedId")
        else:
            params = criterion_a_calculation_params(draft.get("catalog") or {})
            if params["calculation_policy"] != CRITERION_A_POLICY_FLEXIBLE:
                raise SystemExit(f"Draft policy is {params['calculation_policy']!r}, expected flexible")

            prev_id = cfg.get("activePublishedId")
            for v in cfg.get("versions") or []:
                if v.get("id") == prev_id and v.get("status") == "published":
                    v["status"] = "archived"
                    hist = v.setdefault("changeHistory", [])
                    hist.append(
                        {
                            "at": datetime.now(timezone.utc).isoformat(),
                            "actor": "system@activation",
                            "summary": f"Superseded by {DRAFT_ID}",
                        }
                    )

            draft["status"] = "published"
            draft["effectiveDate"] = date.today().isoformat()
            draft["publishedAt"] = datetime.now(timezone.utc).isoformat()
            draft["publishedBy"] = "system@activation"
            draft["label"] = f"published-{draft['effectiveDate']}-flexible-criterion-a"
            draft.setdefault("changeHistory", []).append(
                {
                    "at": draft["publishedAt"],
                    "actor": "system@activation",
                    "summary": "Published average_available_max_six for Criterion A SET/SEF",
                }
            )
            cfg["activePublishedId"] = DRAFT_ID
            cfg["draftId"] = None
            cfg["previewDraft"] = False
            set_json(ASSESSMENT_CONFIG_KEY, cfg)
            set_json(CATALOG_PUBLISHED_KEY, draft.get("catalog"))
            new_id = DRAFT_ID
            print("Published", new_id, "previous active archived:", prev_id)

        user = User.query.filter_by(email=FACULTY_EMAIL).first()
        if not user:
            raise SystemExit(f"Faculty {FACULTY_EMAIL} not found")
        row = FacultyAssessment.query.get(user.id)
        data = dict(row.data or {}) if row else {}
        old_pin = data.get("configVersionId")
        if old_pin == new_id:
            print("Faculty already pinned to", new_id)
        else:
            data = reassign_assessment_config_version(
                data,
                new_version_id=new_id,
                actor_email="system@activation",
                reason="Activate average_available_max_six for Criterion A after SET/SEF extraction fix",
            )
            if not row:
                row = FacultyAssessment(user_id=user.id, data=data)
                db.session.add(row)
            else:
                row.data = data
            db.session.commit()
            print("Reassigned", FACULTY_EMAIL, old_pin, "->", new_id)

        # Backfill confirmed values for rows already marked verified (preserves review intent).
        from app.models import Document

        docs = Document.query.filter_by(owner_user_id=user.id).all()
        fixed = 0
        for doc in docs:
            for rec in SetSefSemesterRecord.query.filter_by(document_id=doc.id, superseded_by_id=None):
                changed = False
                if rec.set_verification_status == "verified" and rec.set_rating_confirmed is None and rec.set_rating_extracted is not None:
                    rec.set_rating_confirmed = float(rec.set_rating_extracted)
                    changed = True
                if rec.sef_verification_status == "verified" and rec.sef_rating_confirmed is None and rec.sef_rating_extracted is not None:
                    rec.sef_rating_confirmed = float(rec.sef_rating_extracted)
                    changed = True
                if changed:
                    fixed += 1
        if fixed:
            db.session.commit()
            print("Backfilled confirmed ratings on", fixed, "semester rows")

        cat, _ = get_catalog_for_assessment(row.data if row else {})
        print("Resolved policy now:", criterion_a_calculation_params(cat)["calculation_policy"])


if __name__ == "__main__":
    main()
