"""KRA I Criteria B/C achievements: claims, review, caps, and Criterion A isolation."""

import pytest

from app.models import User, UserRole
from app.services.achievement_rules import expected_points_for_achievement, validate_claimed_points
from app.services.achievement_rules import resolve_achievement_criterion_id
from app.services.achievements_store import create_achievement, list_achievements, review_achievement, submit_achievement
from app.services.scoring_engine import compute_faculty_scores
from app.services.teaching_effectiveness import compute_criterion_a_from_records

KRA_I_BC_CATALOG = {
    "version": "jc3-bc-test",
    "kras": [
        {
            "id": "kra-I",
            "criteria": [
                {
                    "id": "kra-I-B",
                    "capMaxPoints": 30,
                    "indicators": [
                        {
                            "id": "kra-I-B-1-2",
                            "maxPoints": 16,
                            "calculation": {"kind": "fixed_per_entry", "maxPoints": 16},
                        },
                        {
                            "id": "kra-I-B-2",
                            "maxPoints": 10,
                            "contributorPoints": 5,
                            "calculation": {"kind": "fixed_per_entry", "maxPoints": 10},
                        },
                    ],
                },
                {
                    "id": "kra-I-C",
                    "capMaxPoints": 10,
                    "indicators": [
                        {
                            "id": "kra-I-C-1",
                            "maxPoints": 10,
                            "calculation": {
                                "kind": "role_matrix",
                                "matrix": {
                                    "adviser": {"SP_CP": 3, "UT": 5, "MT": 8, "DD": 10},
                                    "panel": {"SP_CP": 1, "UT": 1, "MT": 2, "DD": 2},
                                },
                            },
                        },
                        {
                            "id": "kra-I-C-2",
                            "maxPoints": 3,
                            "perService": 3,
                            "calculation": {"kind": "fixed_per_entry", "maxPoints": 3, "perService": 3},
                        },
                    ],
                },
            ],
        }
    ],
}


def test_workbook_rule_module_fixed():
    rule = expected_points_for_achievement(KRA_I_BC_CATALOG, "kra-I-B-1-2", {"title": "Mod"})
    assert rule["ruleExpectedPoints"] == 16
    assert validate_claimed_points(claimed=16, rule=rule) is None
    assert "exceed" in (validate_claimed_points(claimed=20, rule=rule) or "")


def test_workbook_rule_lead_vs_contributor():
    lead = expected_points_for_achievement(KRA_I_BC_CATALOG, "kra-I-B-2", {"role": "lead"})
    contrib = expected_points_for_achievement(KRA_I_BC_CATALOG, "kra-I-B-2", {"role": "contributor"})
    assert lead["ruleExpectedPoints"] == 10
    assert contrib["ruleExpectedPoints"] == 5


def test_workbook_rule_adviser_matrix():
    rule = expected_points_for_achievement(
        KRA_I_BC_CATALOG,
        "kra-I-C-1",
        {"role": "adviser", "thesisType": "UT", "quantity": 2},
    )
    assert rule["ruleExpectedPoints"] == 10


def test_submit_achievement_persists_submitted_status(app_ctx, monkeypatch):
    from app.services import achievements_store as store

    draft = {
        "id": "ach-textbook",
        "indicatorId": "kra-I-B-1-2",
        "criterionId": "kra-I-B",
        "title": "Foundations of Applied Mathematics",
        "submissionStatus": "draft",
        "reviewStatus": None,
        "claimedPoints": 16.0,
        "documentIds": ["doc-uuid-1"],
    }
    persisted: list[dict] = []

    class Row:
        data = {
            "achievements": [dict(draft)],
            "setSef": {"SET": [], "SEF": []},
            "entries": {},
        }

    def fake_row(_uid):
        return Row()

    def capture_persist(row, data):
        row.data = data
        persisted.append(data)

    monkeypatch.setattr(store, "_row", fake_row)
    monkeypatch.setattr(store, "_persist_assessment_row", capture_persist)
    monkeypatch.setattr(
        store,
        "_ensure_owned_documents",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        store,
        "_ensure_documents_not_linked_elsewhere",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        "app.services.achievements_store.get_catalog_for_assessment",
        lambda _data: (KRA_I_BC_CATALOG, {}),
    )

    out = store.submit_achievement(1, "ach-textbook", catalog=KRA_I_BC_CATALOG, patch={})
    assert out["submissionStatus"] == "submitted"
    assert out["reviewStatus"] == "pending"
    assert persisted, "submit must persist assessment JSON"
    saved = persisted[-1]["achievements"][0]
    assert saved["submissionStatus"] == "submitted"
    assert saved["reviewStatus"] == "pending"
    assert saved.get("submittedAt")


def test_review_requires_explanation_when_score_changes(app_ctx, monkeypatch):
    from app.services.catalog import CatalogValidationError

    actor = User(email="rev@test", full_name="Rev", role=UserRole.reviewer, is_active=True)
    actor.id = 99
    ach = {
        "id": "ach-1",
        "indicatorId": "kra-I-B-1-2",
        "submissionStatus": "submitted",
        "reviewStatus": "pending",
        "claimedPoints": 16,
        "originalClaimedPoints": 16,
        "title": "Module",
        "documentIds": ["d1"],
    }

    from app.services import achievements_store as store

    def fake_get(_uid, _aid):
        return ach

    def fake_row(_uid):
        class R:
            data = {"achievements": [ach], "setSef": {"SET": [], "SEF": []}, "entries": {}}

        return R()

    monkeypatch.setattr(store, "get_achievement", fake_get)
    monkeypatch.setattr(store, "_row", fake_row)
    monkeypatch.setattr(
        "app.services.achievements_store.get_catalog_for_assessment",
        lambda _data: (KRA_I_BC_CATALOG, {}),
    )

    with pytest.raises(CatalogValidationError, match="Explain"):
        review_achievement(
            1,
            "ach-1",
            actor=actor,
            review_status="approved",
            reviewer_verified_points=14,
            remarks="ok",
            score_change_reason=None,
        )


def test_criterion_b_cap(app_ctx):
    data = {
        "achievements": [
            {
                "id": "a1",
                "indicatorId": "kra-I-B-1-2",
                "submissionStatus": "submitted",
                "reviewStatus": "approved",
                "claimedPoints": 16,
                "originalClaimedPoints": 16,
                "reviewerVerifiedPoints": 16,
            },
            {
                "id": "a2",
                "indicatorId": "kra-I-B-1-2",
                "submissionStatus": "submitted",
                "reviewStatus": "approved",
                "claimedPoints": 16,
                "originalClaimedPoints": 16,
                "reviewerVerifiedPoints": 16,
            },
        ],
        "entries": {},
        "setSef": {"SET": [], "SEF": []},
    }
    weights = {"kra-I": 0.2}
    scores = compute_faculty_scores(data, KRA_I_BC_CATALOG, weights)
    kra_i = scores["verified"]["byKra"]["kra-I"]
    assert kra_i["rawTotal"] == 30


def test_score_not_multiplied_by_document_count(app_ctx):
    data = {
        "achievements": [
            {
                "id": "a1",
                "indicatorId": "kra-I-B-1-2",
                "submissionStatus": "submitted",
                "reviewStatus": "approved",
                "claimedPoints": 16,
                "originalClaimedPoints": 16,
                "reviewerVerifiedPoints": 16,
                "documentIds": ["d1", "d2", "d3"],
            }
        ],
        "entries": {},
        "setSef": {"SET": [], "SEF": []},
    }
    scores = compute_faculty_scores(data, KRA_I_BC_CATALOG, {"kra-I": 0.2})
    assert scores["verified"]["byKra"]["kra-I"]["rawTotal"] == 16


def test_list_achievements_filters_b_vs_c(app_ctx, monkeypatch):
    from app.services import achievements_store as store

    payload = {
        "achievements": [
            {
                "id": "b1",
                "indicatorId": "kra-I-B-1-2",
                "criterionId": "kra-I-B",
                "submissionStatus": "submitted",
                "reviewStatus": "pending",
                "claimedPoints": 16,
            },
            {
                "id": "c1",
                "indicatorId": "kra-I-C-1",
                "criterionId": "kra-I-C",
                "submissionStatus": "submitted",
                "reviewStatus": "pending",
                "claimedPoints": 5,
            },
            {
                "id": "b_legacy",
                "indicatorId": "kra-I-B-2",
                "submissionStatus": "submitted",
                "reviewStatus": "pending",
                "claimedPoints": 10,
            },
        ],
        "entries": {},
        "setSef": {"SET": [], "SEF": []},
    }

    def fake_row(_uid):
        class R:
            data = payload

        return R()

    monkeypatch.setattr(store, "_row", fake_row)

    b_only = list_achievements(1, criterion_id="kra-I-B")
    c_only = list_achievements(1, criterion_id="kra-I-C")
    assert {a["id"] for a in b_only} == {"b1", "b_legacy"}
    assert {a["id"] for a in c_only} == {"c1"}
    assert resolve_achievement_criterion_id({"indicatorId": "kra-I-B-2"}) == "kra-I-B"


def test_kra_i_aggregates_b_and_c_with_independent_caps(app_ctx):
    data = {
        "achievements": [
            {
                "id": "b1",
                "indicatorId": "kra-I-B-1-2",
                "submissionStatus": "submitted",
                "reviewStatus": "approved",
                "claimedPoints": 16,
                "originalClaimedPoints": 16,
                "reviewerVerifiedPoints": 16,
            },
            {
                "id": "b2",
                "indicatorId": "kra-I-B-1-2",
                "submissionStatus": "submitted",
                "reviewStatus": "approved",
                "claimedPoints": 16,
                "originalClaimedPoints": 16,
                "reviewerVerifiedPoints": 16,
            },
            {
                "id": "c1",
                "indicatorId": "kra-I-C-1",
                "submissionStatus": "submitted",
                "reviewStatus": "approved",
                "claimedPoints": 8,
                "originalClaimedPoints": 8,
                "reviewerVerifiedPoints": 8,
            },
            {
                "id": "c2",
                "indicatorId": "kra-I-C-2",
                "submissionStatus": "submitted",
                "reviewStatus": "approved",
                "claimedPoints": 3,
                "originalClaimedPoints": 3,
                "reviewerVerifiedPoints": 3,
            },
        ],
        "entries": {},
        "setSef": {"SET": [], "SEF": []},
    }
    scores = compute_faculty_scores(data, KRA_I_BC_CATALOG, {"kra-I": 0.2})
    kra_i = scores["verified"]["byKra"]["kra-I"]
    assert kra_i["rawTotal"] == 40
    by_crit = {c["id"]: c["rawTotal"] for c in kra_i["criteria"]}
    assert by_crit["kra-I-B"] == 30
    assert by_crit["kra-I-C"] == 10


def test_criterion_a_unaffected_by_achievements(app_ctx):
    from app.models import SetSefSemesterRecord

    rec = SetSefSemesterRecord(
        document_id=1,
        owner_user_id=1,
        set_rating_confirmed=90.0,
        set_verification_status="verified",
        faculty_identity_status="match",
    )
    flex = {
        "version": "x",
        "kras": [
            {
                "id": "kra-I",
                "criteria": [
                    {
                        "id": "kra-I-A",
                        "indicators": [
                            {
                                "id": "kra-I-A-set",
                                "calculation": {"policy": "average_available_max_six", "factor": 0.36},
                            }
                        ],
                    }
                ],
            }
        ],
    }
    out = compute_criterion_a_from_records([rec], catalog=flex, verified_only=False)
    assert out.get("setPoints") == 32.4
