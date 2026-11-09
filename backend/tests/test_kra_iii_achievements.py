"""KRA III — extension services rules, caps, linkage, and scoring."""

from app.services.achievement_rules import expected_points_for_achievement, resolve_achievement_criterion_id, validate_claimed_points
from app.services.scoring_engine import compute_faculty_scores

LEGACY_PUBLISHED_KRA_III_B = {
    "version": "integration-draft-postgres",
    "kras": [
        {
            "id": "kra-III",
            "criteria": [
                {
                    "id": "kra-III-B",
                    "capMaxPoints": 50,
                    "indicators": [
                        {
                            "id": "kra-III-B-1-1",
                            "calculation": {"kind": "structured_points", "points": {"local": 8, "international": 10}},
                            "points": {"local": 8, "international": 10},
                        },
                        {
                            "id": "kra-III-B-1-2",
                            "calculation": {
                                "kind": "structured_points",
                                "points": {"researchAward": 2, "academicCompetition": 1},
                            },
                            "points": {"researchAward": 2, "academicCompetition": 1},
                        },
                        {
                            "id": "kra-III-B-1-3",
                            "calculation": {"kind": "structured_points", "points": {"local": 8, "international": 10}},
                            "points": {"local": 8, "international": 10},
                        },
                        {
                            "id": "kra-III-B-1-5",
                            "calculation": {"kind": "structured_points", "points": {"local": 2, "international": 3}},
                            "points": {"local": 2, "international": 3},
                        },
                        {
                            "id": "kra-III-B-2-1",
                            "calculation": {"kind": "structured_points", "points": {"lead": 5, "participant": 2}},
                            "points": {"lead": 5, "participant": 2},
                            "aggregateCap": 30,
                        },
                    ],
                }
            ],
        }
    ],
}

# Mirrors pinned faculty catalog where kra-III-D-1 is only `{ "kind": "pending" }`.
LEGACY_PENDING_KRA_III_CD = {
    "version": "integration-draft-postgres",
    "kras": [
        {
            "id": "kra-III",
            "criteria": [
                {
                    "id": "kra-III-C",
                    "indicators": [
                        {
                            "id": "kra-III-C-1",
                            "name": "Client satisfaction",
                            "calculation": {"kind": "pending"},
                        }
                    ],
                },
                {
                    "id": "kra-III-D",
                    "indicators": [
                        {
                            "id": "kra-III-D-1",
                            "name": "Administrative designation",
                            "pointRule": "designation_table",
                            "calculation": {"kind": "pending"},
                        }
                    ],
                },
            ],
        }
    ],
}


def test_legacy_published_catalog_criterion_b_rules():
    rule_qa = expected_points_for_achievement(
        LEGACY_PUBLISHED_KRA_III_B, "kra-III-B-1-1", {"serviceScope": "international"}
    )
    assert rule_qa["ruleExpectedPoints"] == 10
    rule_judge = expected_points_for_achievement(
        LEGACY_PUBLISHED_KRA_III_B, "kra-III-B-1-2", {"judgeServiceType": "academic_competition"}
    )
    assert rule_judge["ruleExpectedPoints"] == 1
    rule_train = expected_points_for_achievement(
        LEGACY_PUBLISHED_KRA_III_B, "kra-III-B-1-5", {"serviceScope": "local", "hours": 3}
    )
    assert rule_train["ruleExpectedPoints"] == 6
    assert rule_train["permittedMax"] == 6
    rule_isr = expected_points_for_achievement(
        LEGACY_PUBLISHED_KRA_III_B, "kra-III-B-2-1", {"extensionRole": "participant"}
    )
    assert rule_isr["ruleExpectedPoints"] == 2
    assert validate_claimed_points(claimed=7, rule=rule_train) is not None


def test_legacy_published_catalog_judge_camel_case_field():
    rule = expected_points_for_achievement(
        LEGACY_PUBLISHED_KRA_III_B, "kra-III-B-1-2", {"judgeServiceType": "researchAward"}
    )
    assert rule["ruleExpectedPoints"] == 2


KRA_III_CATALOG = {
    "version": "kra-iii-test",
    "kras": [
        {
            "id": "kra-III",
            "maxPoints": 100,
            "weight": 0.1,
            "scoringPolicy": {
                "coreCriteria": ["kra-III-A", "kra-III-B", "kra-III-C"],
                "bonusCriterion": "kra-III-D",
                "applyKraEnvelopeCap": False,
            },
            "criteria": [
                {
                    "id": "kra-III-A",
                    "capMaxPoints": 30,
                    "indicators": [
                        {
                            "id": "kra-III-A-2",
                            "calculation": {
                                "kind": "income_tier",
                                "tiers": [
                                    {"id": "t1", "lead": 2, "contributor": 1, "resolved": True, "maxAmount": 100000},
                                    {"id": "t2", "lead": 4, "contributor": 2, "resolved": True, "minAmount": 100001, "maxAmount": 500000},
                                    {"id": "t3", "lead": 6, "contributor": 3, "resolved": False},
                                    {"id": "t4", "lead": 12, "contributor": 6, "resolved": True, "minAmount": 6000001, "maxAmount": 12000000},
                                ],
                            },
                        },
                    ],
                },
                {
                    "id": "kra-III-B",
                    "capMaxPoints": 50,
                    "indicators": [
                        {
                            "id": "kra-III-B-1-5",
                            "calculation": {
                                "kind": "hourly_tier",
                                "rates": {"local": 2, "international": 3},
                                "tierField": "serviceScope",
                            },
                        },
                        {
                            "id": "kra-III-B-1-4-4",
                            "calculation": {"kind": "fixed_per_entry", "maxPoints": 1, "aggregateCap": 10},
                        },
                        {
                            "id": "kra-III-B-2-1",
                            "calculation": {
                                "kind": "tiered_option",
                                "options": {"lead": 5, "participant": 2},
                                "tierField": "extensionRole",
                                "aggregateCap": 30,
                            },
                        },
                    ],
                },
                {
                    "id": "kra-III-C",
                    "capMaxPoints": 20,
                    "indicators": [
                        {
                            "id": "kra-III-C-1",
                            "maxPoints": 20,
                            "calculation": {
                                "kind": "pending",
                                "requiresLinkedAchievement": {
                                    "indicatorId": "kra-III-B-2-1",
                                    "linkField": "linkedIsrProjectId",
                                },
                            },
                        }
                    ],
                },
                {
                    "id": "kra-III-D",
                    "capMaxPoints": 20,
                    "indicators": [
                        {
                            "id": "kra-III-D-1",
                            "calculation": {
                                "kind": "designation_matrix",
                                "matrix": {
                                    "institutional": {"president": 20},
                                    "college_department": {"dean": 6},
                                },
                            },
                        }
                    ],
                },
            ],
        }
    ],
}


def test_resolve_criterion_kra_iii():
    assert resolve_achievement_criterion_id({"criterionId": "kra-III-B"}) == "kra-III-B"
    assert resolve_achievement_criterion_id({"indicatorId": "kra-III-D-1"}) == "kra-III-D"


def test_income_tier_resolved_band():
    rule = expected_points_for_achievement(
        KRA_III_CATALOG, "kra-III-A-2", {"incomeRole": "lead", "incomeAmount": 80000}
    )
    assert rule["ruleExpectedPoints"] == 2
    assert validate_claimed_points(claimed=3, rule=rule) is not None


def test_income_tier_ambiguous_band():
    rule = expected_points_for_achievement(
        KRA_III_CATALOG, "kra-III-A-2", {"incomeRole": "lead", "incomeAmount": 600000}
    )
    assert rule.get("unresolved")
    assert rule["ruleExpectedPoints"] is None


def test_income_tier_unresolved_t3_selection():
    rule = expected_points_for_achievement(
        KRA_III_CATALOG, "kra-III-A-2", {"incomeRole": "lead", "incomeTier": "t3"}
    )
    assert rule.get("unresolved")
    assert rule["ruleExpectedPoints"] is None


def test_hourly_training():
    rule = expected_points_for_achievement(
        KRA_III_CATALOG, "kra-III-B-1-5", {"serviceScope": "local", "hours": 3}
    )
    assert rule["ruleExpectedPoints"] == 6
    assert rule["permittedMax"] == 6


def test_hourly_invalid():
    rule = expected_points_for_achievement(KRA_III_CATALOG, "kra-III-B-1-5", {"serviceScope": "local", "hours": 0})
    assert rule.get("unresolved")


def test_designation_matrix():
    rule = expected_points_for_achievement(
        KRA_III_CATALOG,
        "kra-III-D-1",
        {"designationLevel": "college_department", "designationRole": "dean"},
    )
    assert rule["ruleExpectedPoints"] == 6


def test_legacy_pending_d_designation_dept_head_four():
    rule = expected_points_for_achievement(
        LEGACY_PENDING_KRA_III_CD,
        "kra-III-D-1",
        {"designationLevel": "college_department", "designationRole": "department_head"},
    )
    assert rule.get("unresolved") is None
    assert rule["ruleExpectedPoints"] == 4
    assert rule["permittedMax"] == 4
    unr = rule.get("ruleSummary") or ""
    assert "client satisfaction" not in unr.lower()


def test_legacy_pending_d_not_criterion_c_conversion_error():
    rule = expected_points_for_achievement(LEGACY_PENDING_KRA_III_CD, "kra-III-D-1", {})
    msg = (rule.get("unresolved") or "").lower()
    assert "client satisfaction" not in msg
    assert "conversion" not in msg


def test_legacy_pending_c_still_client_satisfaction_unresolved():
    rule = expected_points_for_achievement(LEGACY_PENDING_KRA_III_CD, "kra-III-C-1", {})
    msg = rule.get("unresolved") or ""
    assert "client satisfaction" in msg.lower() or "conversion" in msg.lower()
    assert "Link" in msg or "linkedIsrProjectId" in msg


def test_criterion_c_requires_isr_link():
    ctx = {
        "achievements": [
            {"id": "isr-1", "indicatorId": "kra-III-B-2-1", "submissionStatus": "draft", "reviewStatus": None}
        ]
    }
    rule = expected_points_for_achievement(
        KRA_III_CATALOG,
        "kra-III-C-1",
        {"linkedIsrProjectId": "isr-1"},
        context=ctx,
    )
    assert rule["ruleExpectedPoints"] is None
    assert rule.get("unresolved")
    assert "conversion" in (rule.get("unresolved") or "").lower() or "client" in (rule.get("unresolved") or "").lower()

    missing = expected_points_for_achievement(KRA_III_CATALOG, "kra-III-C-1", {}, context=ctx)
    assert "linkedIsrProjectId" in (missing.get("unresolved") or "") or "Link" in (missing.get("unresolved") or "")


def test_scoring_bonus_metadata():
    data = {
        "entries": {},
        "achievements": [
            {
                "id": "d1",
                "indicatorId": "kra-III-D-1",
                "designationLevel": "institutional",
                "designationRole": "president",
                "submissionStatus": "submitted",
                "reviewStatus": "approved",
                "claimedPoints": 20,
                "reviewerVerifiedPoints": 20,
            },
        ],
    }
    scores = compute_faculty_scores(data, KRA_III_CATALOG, {"kra-III": 0.1})
    kra = scores["verified"]["byKra"]["kra-III"]
    assert kra.get("bonusSubtotal") == 20
    assert kra.get("coreSubtotal") == 0
    assert kra.get("rawTotal") == 20


def test_preview_rule_http_designation_legacy_pending(app, app_ctx, monkeypatch):
    from flask import current_app

    from app.models import User, UserRole
    from app.routes import achievements as ach_routes
    from app.services.auth_context import issue_api_token

    faculty = User.query.filter_by(role=UserRole.faculty).first()
    assert faculty

    def fake_catalog(_uid):
        return LEGACY_PENDING_KRA_III_CD, {}

    monkeypatch.setattr(ach_routes, "_catalog_for_faculty", fake_catalog)

    client = app.test_client()
    token = issue_api_token(faculty, current_app.config["API_TOKEN_TTL_HOURS"])
    headers = {"Authorization": f"Bearer {token}", "X-Client-Type": "faculty_mobile"}
    res = client.post(
        "/api/faculty/achievements/preview-rule",
        json={
            "indicatorId": "kra-III-D-1",
            "designationLevel": "college_department",
            "designationRole": "department_head",
        },
        headers=headers,
    )
    assert res.status_code == 200, res.get_data(as_text=True)
    body = res.get_json()
    assert body["ruleExpectedPoints"] == 4
    assert body.get("unresolved") is None


def test_review_rejects_excess_designation_points(app_ctx, monkeypatch):
    from app.models import User, UserRole
    from app.services import achievements_store as store
    from app.services.catalog import CatalogValidationError

    faculty = User.query.filter_by(role=UserRole.faculty).first()
    assert faculty

    draft = {
        "id": "ach-dept-head-cap",
        "indicatorId": "kra-III-D-1",
        "criterionId": "kra-III-D",
        "title": "Department Head",
        "designationLevel": "college_department",
        "designationRole": "department_head",
        "submissionStatus": "submitted",
        "reviewStatus": "pending",
        "claimedPoints": 4.0,
        "documentIds": ["doc-dept-head"],
    }

    class Row:
        data = {"achievements": [dict(draft)], "setSef": {"SET": [], "SEF": []}, "entries": {}}

    monkeypatch.setattr(store, "_row", lambda _uid: Row())
    monkeypatch.setattr(store, "_persist_assessment_row", lambda row, data: setattr(row, "data", data))
    monkeypatch.setattr(store, "_ensure_owned_documents", lambda *_a, **_k: None)
    monkeypatch.setattr(
        "app.services.achievements_store.get_catalog_for_assessment",
        lambda _d: (LEGACY_PENDING_KRA_III_CD, {}),
    )

    reviewer = User(email="rcap@t", full_name="RC", role=UserRole.reviewer, is_active=True)
    try:
        store.review_achievement(
            faculty.id,
            "ach-dept-head-cap",
            actor=reviewer,
            review_status="approved",
            reviewer_verified_points=5,
            remarks="too high",
            score_change_reason=None,
        )
        raised = False
    except CatalogValidationError as e:
        raised = True
        assert "exceed" in str(e).lower() or "4" in str(e)
    assert raised


def test_submit_review_designation_legacy_pending(app_ctx, monkeypatch):
    from app.models import User, UserRole
    from app.services import achievements_store as store

    faculty = User.query.filter_by(role=UserRole.faculty).first()
    assert faculty

    draft = {
        "id": "ach-dept-head-d",
        "indicatorId": "kra-III-D-1",
        "criterionId": "kra-III-D",
        "title": "Department Head",
        "designationLevel": "college_department",
        "designationRole": "department_head",
        "submissionStatus": "draft",
        "claimedPoints": 4.0,
        "documentIds": ["doc-dept-head"],
    }

    class Row:
        data = {"achievements": [dict(draft)], "setSef": {"SET": [], "SEF": []}, "entries": {}}

    monkeypatch.setattr(store, "_row", lambda _uid: Row())
    monkeypatch.setattr(store, "_persist_assessment_row", lambda row, data: setattr(row, "data", data))
    monkeypatch.setattr(store, "_ensure_owned_documents", lambda *_a, **_k: None)
    monkeypatch.setattr(store, "_ensure_documents_not_linked_elsewhere", lambda *_a, **_k: None)
    monkeypatch.setattr(
        "app.services.achievements_store.get_catalog_for_assessment",
        lambda _d: (LEGACY_PENDING_KRA_III_CD, {}),
    )

    out = store.submit_achievement(faculty.id, "ach-dept-head-d", catalog=LEGACY_PENDING_KRA_III_CD, patch={})
    assert out["submissionStatus"] == "submitted"
    assert out["claimedPoints"] == 4
    assert out.get("ruleExpectedPoints") == 4
    assert not out.get("ruleUnresolved")

    reviewer = User(email="r2@t", full_name="R2", role=UserRole.reviewer, is_active=True)
    reviewed = store.review_achievement(
        faculty.id,
        "ach-dept-head-d",
        actor=reviewer,
        review_status="approved",
        reviewer_verified_points=4,
        remarks="ok",
        score_change_reason=None,
    )
    assert reviewed["reviewerVerifiedPoints"] == 4
    assert reviewed["reviewStatus"] == "approved"


def test_preview_rule_http_training_legacy(app, app_ctx, monkeypatch):
    from flask import current_app

    from app.models import User, UserRole
    from app.routes import achievements as ach_routes
    from app.services.auth_context import issue_api_token

    faculty = User.query.filter_by(role=UserRole.faculty).first()
    assert faculty

    def fake_catalog(_uid):
        return LEGACY_PUBLISHED_KRA_III_B, {}

    monkeypatch.setattr(ach_routes, "_catalog_for_faculty", fake_catalog)

    client = app.test_client()
    token = issue_api_token(faculty, current_app.config["API_TOKEN_TTL_HOURS"])
    headers = {"Authorization": f"Bearer {token}", "X-Client-Type": "faculty_mobile"}
    res = client.post(
        "/api/faculty/achievements/preview-rule",
        json={"indicatorId": "kra-III-B-1-5", "serviceScope": "local", "hours": 3},
        headers=headers,
    )
    assert res.status_code == 200, res.get_data(as_text=True)
    body = res.get_json()
    assert body["ruleExpectedPoints"] == 6
    assert body.get("unresolved") is None


def test_submit_review_training_legacy(app_ctx, monkeypatch):
    from app.models import User, UserRole
    from app.services import achievements_store as store

    faculty = User.query.filter_by(role=UserRole.faculty).first()
    assert faculty

    draft = {
        "id": "ach-train-3h",
        "indicatorId": "kra-III-B-1-5",
        "criterionId": "kra-III-B",
        "title": "Workshop facilitation",
        "serviceScope": "local",
        "hours": 3,
        "submissionStatus": "draft",
        "claimedPoints": 6.0,
        "documentIds": ["doc-k3-training"],
    }

    class Row:
        data = {"achievements": [dict(draft)], "setSef": {"SET": [], "SEF": []}, "entries": {}}

    monkeypatch.setattr(store, "_row", lambda _uid: Row())
    monkeypatch.setattr(store, "_persist_assessment_row", lambda row, data: setattr(row, "data", data))
    monkeypatch.setattr(store, "_ensure_owned_documents", lambda *_a, **_k: None)
    monkeypatch.setattr(store, "_ensure_documents_not_linked_elsewhere", lambda *_a, **_k: None)
    monkeypatch.setattr("app.services.achievements_store.get_catalog_for_assessment", lambda _d: (LEGACY_PUBLISHED_KRA_III_B, {}))

    out = store.submit_achievement(faculty.id, "ach-train-3h", catalog=LEGACY_PUBLISHED_KRA_III_B, patch={})
    assert out["submissionStatus"] == "submitted"
    assert out["claimedPoints"] == 6
    assert out.get("ruleExpectedPoints") == 6

    reviewer = User(email="r@t", full_name="R", role=UserRole.reviewer, is_active=True)
    reviewed = store.review_achievement(
        faculty.id,
        "ach-train-3h",
        actor=reviewer,
        review_status="approved",
        reviewer_verified_points=6,
        remarks="ok",
        score_change_reason=None,
    )
    assert reviewed["reviewerVerifiedPoints"] == 6
    assert reviewed["reviewStatus"] == "approved"


def test_media_aggregate_cap_guest_expert():
    catalog = {
        "version": "media-cap",
        "kras": [
            {
                "id": "kra-III",
                "criteria": [
                    {
                        "id": "kra-III-B",
                        "capMaxPoints": 50,
                        "indicators": [
                            {
                                "id": "kra-III-B-1-4-4",
                                "calculation": {"kind": "fixed_per_entry", "maxPoints": 1, "aggregateCap": 10},
                            }
                        ],
                    }
                ],
            }
        ],
    }
    data = {
        "entries": {},
        "achievements": [
            {
                "id": f"g{i}",
                "indicatorId": "kra-III-B-1-4-4",
                "submissionStatus": "submitted",
                "reviewStatus": "approved",
                "claimedPoints": 1,
                "reviewerVerifiedPoints": 1,
            }
            for i in range(12)
        ],
    }
    scores = compute_faculty_scores(data, catalog, {"kra-III": 0.1})
    b = next(c for c in scores["verified"]["byKra"]["kra-III"]["criteria"] if c["id"] == "kra-III-B")
    assert b["rawTotal"] == 10


def test_criterion_b_cap_50():
    catalog = {
        "version": "b-cap",
        "kras": [
            {
                "id": "kra-III",
                "criteria": [
                    {
                        "id": "kra-III-B",
                        "capMaxPoints": 50,
                        "indicators": [
                            {
                                "id": "kra-III-B-1-4-2",
                                "calculation": {"kind": "fixed_per_entry", "maxPoints": 10},
                            }
                        ],
                    }
                ],
            }
        ],
    }
    data = {
        "entries": {},
        "achievements": [
            {
                "id": f"c{i}",
                "indicatorId": "kra-III-B-1-4-2",
                "submissionStatus": "submitted",
                "reviewStatus": "approved",
                "claimedPoints": 10,
                "reviewerVerifiedPoints": 10,
            }
            for i in range(6)
        ],
    }
    scores = compute_faculty_scores(data, catalog, {"kra-III": 0.1})
    b = next(c for c in scores["verified"]["byKra"]["kra-III"]["criteria"] if c["id"] == "kra-III-B")
    assert b["rawTotal"] == 50


def test_isr_aggregate_cap():
    data = {
        "entries": {},
        "achievements": [
            {
                "id": f"isr-{i}",
                "indicatorId": "kra-III-B-2-1",
                "extensionRole": "lead",
                "submissionStatus": "submitted",
                "reviewStatus": "approved",
                "claimedPoints": 5,
                "reviewerVerifiedPoints": 5,
            }
            for i in range(8)
        ],
    }
    scores = compute_faculty_scores(data, KRA_III_CATALOG, {"kra-III": 0.1})
    b_total = next(c for c in scores["verified"]["byKra"]["kra-III"]["criteria"] if c["id"] == "kra-III-B")
    assert b_total["rawTotal"] == 30
