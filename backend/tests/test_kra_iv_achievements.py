"""KRA IV — professional development rules, aggregate caps, and scoring."""

import copy

from app.services.achievement_rules import expected_points_for_achievement, resolve_achievement_criterion_id
from app.services.achievements_store import create_achievement, list_achievements, submit_achievement, update_achievement_draft
from app.services.scoring_engine import compute_faculty_scores

KRA_IV_CATALOG = {
    "version": "kra-iv-test",
    "kras": [
        {
            "id": "kra-IV",
            "maxPoints": 100,
            "weight": 0.1,
            "scoringPolicy": {
                "coreCriteria": ["kra-IV-A", "kra-IV-B", "kra-IV-C"],
                "additionalCriteria": ["kra-IV-D"],
                "coreMaxSum": 100,
                "additionalMax": 20,
                "kraListedMax": 100,
                "applyKraEnvelopeCap": False,
            },
            "criteria": [
                {
                    "id": "kra-IV-A",
                    "capMaxPoints": 20,
                    "indicators": [
                        {"id": "kra-IV-A-1", "calculation": {"kind": "fixed_per_entry", "maxPoints": 5}}
                    ],
                },
                {
                    "id": "kra-IV-B",
                    "capMaxPoints": 60,
                    "indicators": [
                        {
                            "id": "kra-IV-B-1",
                            "calculation": {
                                "kind": "tiered_option",
                                "options": {
                                    "post_master_diploma": 10,
                                    "doctorate": 40,
                                },
                                "tierField": "qualificationType",
                            },
                        },
                        {
                            "id": "kra-IV-B-2",
                            "calculation": {
                                "kind": "tiered_option",
                                "options": {"local": 1, "international": 2},
                                "tierField": "attendanceScope",
                                "aggregateCap": 10,
                            },
                        },
                        {
                            "id": "kra-IV-B-3-1",
                            "calculation": {
                                "kind": "fixed_per_entry",
                                "maxPoints": 3,
                                "aggregateGroup": "kra-IV-B-presentations",
                                "aggregateCap": 10,
                            },
                        },
                        {
                            "id": "kra-IV-B-3-2",
                            "calculation": {
                                "kind": "fixed_per_entry",
                                "maxPoints": 5,
                                "aggregateGroup": "kra-IV-B-presentations",
                                "aggregateCap": 10,
                            },
                        },
                    ],
                },
                {
                    "id": "kra-IV-C",
                    "capMaxPoints": 20,
                    "indicators": [
                        {
                            "id": "kra-IV-C-1",
                            "calculation": {
                                "kind": "tiered_option",
                                "options": {"institutional": 2, "local_regional": 3, "national": 4},
                                "tierField": "awardLevel",
                            },
                        }
                    ],
                },
                {
                    "id": "kra-IV-D",
                    "capMaxPoints": 20,
                    "indicators": [
                        {
                            "id": "kra-IV-D-1",
                            "calculation": {
                                "kind": "yearly_rate",
                                "roleField": "academicServiceRole",
                                "yearsField": "serviceYears",
                                "requiresNewlyAppointed": True,
                                "newlyAppointedField": "newlyAppointedEligible",
                                "fractionalYearPolicy": "unresolved",
                                "rates": {
                                    "president": 5,
                                    "dept_program_head": 3,
                                    "faculty_member": 2,
                                },
                            },
                        }
                    ],
                },
            ],
        }
    ],
}


def test_membership_five_points():
    rule = expected_points_for_achievement(KRA_IV_CATALOG, "kra-IV-A-1", {})
    assert rule["ruleExpectedPoints"] == 5


def test_qualification_doctorate_forty():
    rule = expected_points_for_achievement(
        KRA_IV_CATALOG, "kra-IV-B-1", {"qualificationType": "doctorate"}
    )
    assert rule["ruleExpectedPoints"] == 40


def test_attendance_international_two():
    rule = expected_points_for_achievement(
        KRA_IV_CATALOG, "kra-IV-B-2", {"attendanceScope": "international"}
    )
    assert rule["ruleExpectedPoints"] == 2


def test_award_national_four():
    rule = expected_points_for_achievement(KRA_IV_CATALOG, "kra-IV-C-1", {"awardLevel": "national"})
    assert rule["ruleExpectedPoints"] == 4


def test_dept_head_three_years():
    rule = expected_points_for_achievement(
        KRA_IV_CATALOG,
        "kra-IV-D-1",
        {
            "newlyAppointedEligible": True,
            "academicServiceRole": "dept_program_head",
            "serviceYears": 3,
        },
    )
    assert rule["ruleExpectedPoints"] == 9


def test_newly_appointed_required():
    rule = expected_points_for_achievement(
        KRA_IV_CATALOG,
        "kra-IV-D-1",
        {"academicServiceRole": "faculty_member", "serviceYears": 2},
    )
    assert rule.get("unresolved")
    assert rule["ruleExpectedPoints"] is None


def test_fractional_years_unresolved():
    rule = expected_points_for_achievement(
        KRA_IV_CATALOG,
        "kra-IV-D-1",
        {
            "newlyAppointedEligible": True,
            "academicServiceRole": "faculty_member",
            "serviceYears": 1.5,
        },
    )
    assert rule.get("unresolved")


def test_attendance_mixed_local_international_shared_cap_ten():
    """Local and international attendance share one indicator aggregate cap of 10."""
    achievements = [
        {
            "id": f"l{i}",
            "indicatorId": "kra-IV-B-2",
            "attendanceScope": "local",
            "submissionStatus": "submitted",
            "reviewStatus": "approved",
            "claimedPoints": 1,
            "reviewerVerifiedPoints": 1,
        }
        for i in range(6)
    ] + [
        {
            "id": f"i{i}",
            "indicatorId": "kra-IV-B-2",
            "attendanceScope": "international",
            "submissionStatus": "submitted",
            "reviewStatus": "approved",
            "claimedPoints": 2,
            "reviewerVerifiedPoints": 2,
        }
        for i in range(3)
    ]
    data = {"entries": {}, "achievements": achievements}
    scores = compute_faculty_scores(data, KRA_IV_CATALOG, {"kra-IV": 0.1})
    b = next(c for c in scores["verified"]["byKra"]["kra-IV"]["criteria"] if c["id"] == "kra-IV-B")
    assert b["rawTotal"] == 10


def test_attendance_aggregate_cap_ten():
    data = {
        "entries": {},
        "achievements": [
            {
                "id": f"a{i}",
                "indicatorId": "kra-IV-B-2",
                "attendanceScope": "international",
                "submissionStatus": "submitted",
                "reviewStatus": "approved",
                "claimedPoints": 2,
                "reviewerVerifiedPoints": 2,
            }
            for i in range(8)
        ],
    }
    scores = compute_faculty_scores(data, KRA_IV_CATALOG, {"kra-IV": 0.1})
    b = next(c for c in scores["verified"]["byKra"]["kra-IV"]["criteria"] if c["id"] == "kra-IV-B")
    assert b["rawTotal"] == 10


def test_presentation_aggregate_cap_ten_mixed():
    data = {
        "entries": {},
        "achievements": [
            {
                "id": "p1",
                "indicatorId": "kra-IV-B-3-1",
                "submissionStatus": "submitted",
                "reviewStatus": "approved",
                "claimedPoints": 3,
                "reviewerVerifiedPoints": 3,
            },
            {
                "id": "p2",
                "indicatorId": "kra-IV-B-3-2",
                "submissionStatus": "submitted",
                "reviewStatus": "approved",
                "claimedPoints": 5,
                "reviewerVerifiedPoints": 5,
            },
            {
                "id": "p3",
                "indicatorId": "kra-IV-B-3-2",
                "submissionStatus": "submitted",
                "reviewStatus": "approved",
                "claimedPoints": 5,
                "reviewerVerifiedPoints": 5,
            },
        ],
    }
    scores = compute_faculty_scores(data, KRA_IV_CATALOG, {"kra-IV": 0.1})
    b = next(c for c in scores["verified"]["byKra"]["kra-IV"]["criteria"] if c["id"] == "kra-IV-B")
    assert b["rawTotal"] == 10


def test_kra_iv_envelope_policy_fields():
    data = {"entries": {}, "achievements": []}
    scores = compute_faculty_scores(data, KRA_IV_CATALOG, {"kra-IV": 0.1})
    kra = scores["verified"]["byKra"]["kra-IV"]
    assert "coreSubtotal" in kra
    assert "additionalSubtotal" in kra
    assert kra["weightedContribution"] == 0.0


def test_resolve_criterion_id_iv():
    assert resolve_achievement_criterion_id({"indicatorId": "kra-IV-B-2"}) == "kra-IV-B"


LEGACY_KRA_IV_PIN = copy.deepcopy(KRA_IV_CATALOG)
LEGACY_KRA_IV_PIN["kras"][0].pop("scoringPolicy", None)
for crit in LEGACY_KRA_IV_PIN["kras"][0]["criteria"]:
    for ind in crit["indicators"]:
        if ind["id"] == "kra-IV-B-2":
            ind["calculation"] = {"kind": "structured_points"}


def test_legacy_pinned_b2_normalizes_attendance_cap():
    rule = expected_points_for_achievement(LEGACY_KRA_IV_PIN, "kra-IV-B-2", {"attendanceScope": "international"})
    assert rule["ruleExpectedPoints"] == 2


def test_envelope_unresolved_surfaces_in_score_notes():
    data = {
        "entries": {},
        "achievements": [
            *[
                {
                    "id": f"a{i}",
                    "indicatorId": "kra-IV-A-1",
                    "submissionStatus": "submitted",
                    "reviewStatus": "approved",
                    "claimedPoints": 5,
                    "reviewerVerifiedPoints": 5,
                }
                for i in range(4)
            ],
            {
                "id": "q1",
                "indicatorId": "kra-IV-B-1",
                "qualificationType": "doctorate",
                "submissionStatus": "submitted",
                "reviewStatus": "approved",
                "claimedPoints": 40,
                "reviewerVerifiedPoints": 40,
            },
            {
                "id": "q2",
                "indicatorId": "kra-IV-B-1",
                "qualificationType": "additional_masters",
                "submissionStatus": "submitted",
                "reviewStatus": "approved",
                "claimedPoints": 20,
                "reviewerVerifiedPoints": 20,
            },
            *[
                {
                    "id": f"c{i}",
                    "indicatorId": "kra-IV-C-1",
                    "awardLevel": "national",
                    "submissionStatus": "submitted",
                    "reviewStatus": "approved",
                    "claimedPoints": 4,
                    "reviewerVerifiedPoints": 4,
                }
                for i in range(5)
            ],
            {
                "id": "d1",
                "indicatorId": "kra-IV-D-1",
                "newlyAppointedEligible": True,
                "academicServiceRole": "president",
                "serviceYears": 4,
                "submissionStatus": "submitted",
                "reviewStatus": "approved",
                "claimedPoints": 20,
                "reviewerVerifiedPoints": 20,
            },
        ],
    }
    scores = compute_faculty_scores(data, KRA_IV_CATALOG, {"kra-IV": 0.1})
    kra = scores["verified"]["byKra"]["kra-IV"]
    assert kra.get("kraCapPolicyUnresolved") is True
    assert kra.get("coreSubtotal") == 100
    assert kra.get("additionalSubtotal") == 20
    assert kra.get("rawTotalBeforeKraCap") == 120
    assert any("Provisional" in n for n in scores["verified"].get("notes") or [])


def test_kra_iv_service_fields_persist_create_update_submit(app_ctx, monkeypatch):
    from app.services import achievements_store as store
    from app.services import catalog as catalog_mod

    payload = {"achievements": [], "entries": {}, "setSef": {"SET": [], "SEF": []}}

    class R:
        data = payload

    monkeypatch.setattr(store, "_row", lambda _uid: R())
    monkeypatch.setattr(store, "_persist_assessment_row", lambda row, data: None)
    monkeypatch.setattr(store, "_ensure_owned_documents", lambda *a, **k: None)
    monkeypatch.setattr(store, "_ensure_documents_not_linked_elsewhere", lambda *a, **k: None)
    monkeypatch.setattr(catalog_mod, "pin_assessment_config_version_if_needed", lambda uid, data: data)

    body = create_achievement(
        1,
        {
            "indicatorId": "kra-IV-D-1",
            "title": "Dept head service",
            "claimedPoints": 9,
            "newlyAppointedEligible": True,
            "academicServiceRole": "dept_program_head",
            "serviceYears": 3,
            "documentIds": ["doc-iv-1"],
        },
        catalog=KRA_IV_CATALOG,
    )
    assert body["serviceYears"] == 3
    assert body["academicServiceRole"] == "dept_program_head"
    assert body["newlyAppointedEligible"] is True

    updated = update_achievement_draft(
        1,
        body["id"],
        {"serviceYears": 4, "role": "lead"},
        catalog=KRA_IV_CATALOG,
    )
    assert updated["serviceYears"] == 4
    assert updated["role"] == "lead"

    submitted = submit_achievement(1, body["id"], catalog=KRA_IV_CATALOG)
    assert submitted["submissionStatus"] == "submitted"
    assert submitted["serviceYears"] == 4

    listed = list_achievements(1, criterion_id="kra-IV-D")
    assert listed[0]["serviceYears"] == 4
    assert listed[0]["newlyAppointedEligible"] is True
