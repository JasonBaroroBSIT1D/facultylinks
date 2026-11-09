"""KRA II — workbook rules, caps, and achievement scoring."""

from app.services.achievement_rules import expected_points_for_achievement, resolve_achievement_criterion_id, validate_claimed_points
from app.services.scoring_engine import compute_faculty_scores

KRA_II_CATALOG = {
    "version": "kra-ii-test",
    "kras": [
        {
            "id": "kra-II",
            "maxPoints": 100,
            "criteria": [
                {
                    "id": "kra-II-A",
                    "capMaxPoints": 100,
                    "indicators": [
                        {
                            "id": "kra-II-A-3",
                            "maxPoints": 50,
                            "calculation": {"kind": "fixed_per_entry", "maxPoints": 50},
                        },
                        {
                            "id": "kra-II-A-5",
                            "maxPoints": 35,
                            "calculation": {"kind": "fixed_per_entry", "maxPoints": 35, "aggregateCap": 70},
                        },
                        {
                            "id": "kra-II-A-6",
                            "maxPoints": 10,
                            "calculation": {"kind": "fixed_per_entry", "maxPoints": 10, "aggregateCap": 60},
                        },
                    ],
                },
                {
                    "id": "kra-II-B",
                    "capMaxPoints": 100,
                    "indicators": [
                        {
                            "id": "kra-II-B-1-1",
                            "calculation": {"kind": "patent_stage", "stages": {"A": 10, "P": 20, "G": 80}},
                        },
                        {
                            "id": "kra-II-B-1-2",
                            "calculation": {
                                "kind": "tiered_option",
                                "options": {"local": 5, "international": 10},
                                "tierCaps": {"local": 20, "international": 30},
                                "tierField": "commercializationScope",
                            },
                        },
                    ],
                },
                {
                    "id": "kra-II-C",
                    "capMaxPoints": 100,
                    "indicators": [
                        {
                            "id": "kra-II-C-1-2-design",
                            "calculation": {"kind": "pending"},
                        },
                        {
                            "id": "kra-II-C-1-4-3",
                            "maxPoints": 2,
                            "calculation": {"kind": "fixed_per_entry", "maxPoints": 2},
                        },
                    ],
                },
            ],
        }
    ],
}


def test_resolve_criterion_kra_ii():
    assert resolve_achievement_criterion_id({"criterionId": "kra-II-B"}) == "kra-II-B"
    assert resolve_achievement_criterion_id({"indicatorId": "kra-II-A-3"}) == "kra-II-A"


LEGACY_PATENT_CATALOG = {
    "version": "legacy-structured",
    "kras": [
        {
            "id": "kra-II",
            "criteria": [
                {
                    "id": "kra-II-B",
                    "indicators": [
                        {
                            "id": "kra-II-B-1-1",
                            "name": "Patent",
                            "calculation": {"kind": "structured_points", "points": {"A": 10, "P": 20, "G": 80}},
                        },
                    ],
                }
            ],
        }
    ],
}

LEGACY_POINTS_ONLY_CATALOG = {
    "version": "legacy-points",
    "kras": [
        {
            "id": "kra-II",
            "criteria": [
                {
                    "id": "kra-II-B",
                    "indicators": [
                        {
                            "id": "kra-II-B-1-1",
                            "name": "Patent",
                            "points": {"A": 10, "P": 20, "G": 80},
                        },
                    ],
                }
            ],
        }
    ],
}


def test_patent_legacy_structured_points_resolves_stages():
    rule = expected_points_for_achievement(
        LEGACY_PATENT_CATALOG, "kra-II-B-1-1", {"patentStage": "P"}
    )
    assert rule["ruleExpectedPoints"] == 20
    assert rule["permittedMax"] == 20
    assert rule.get("unresolved") is None
    assert validate_claimed_points(claimed=25, rule=rule) is not None


def test_patent_legacy_points_object_resolves_stages():
    rule = expected_points_for_achievement(
        LEGACY_POINTS_ONLY_CATALOG, "kra-II-B-1-1", {"patentStage": "A"}
    )
    assert rule["ruleExpectedPoints"] == 10
    assert validate_claimed_points(claimed=10, rule=rule) is None


def test_patent_invalid_stage():
    rule = expected_points_for_achievement(KRA_II_CATALOG, "kra-II-B-1-1", {"patentStage": "X"})
    assert rule.get("unresolved")
    assert validate_claimed_points(claimed=10, rule=rule) is not None


def test_patent_stage_not_cumulative():
    rule_g = expected_points_for_achievement(KRA_II_CATALOG, "kra-II-B-1-1", {"patentStage": "G"})
    assert rule_g["ruleExpectedPoints"] == 80
    rule_a = expected_points_for_achievement(KRA_II_CATALOG, "kra-II-B-1-1", {"patentStage": "A"})
    assert rule_a["ruleExpectedPoints"] == 10
    assert validate_claimed_points(claimed=80, rule=rule_g) is None
    assert validate_claimed_points(claimed=90, rule=rule_g) is not None


def test_tiered_legacy_structured_points():
    catalog = {
        "version": "legacy-tier",
        "kras": [
            {
                "id": "kra-II",
                "criteria": [
                    {
                        "id": "kra-II-B",
                        "indicators": [
                            {
                                "id": "kra-II-B-1-2",
                                "calculation": {
                                    "kind": "structured_points",
                                    "points": {"local": 5, "international": 10},
                                    "tierField": "commercializationScope",
                                },
                            }
                        ],
                    }
                ],
            }
        ],
    }
    rule = expected_points_for_achievement(
        catalog, "kra-II-B-1-2", {"commercializationScope": "local"}
    )
    assert rule["ruleExpectedPoints"] == 5
    assert rule["permittedMax"] == 5
    assert validate_claimed_points(claimed=6, rule=rule) is not None


def test_commercialization_tier():
    rule = expected_points_for_achievement(
        KRA_II_CATALOG, "kra-II-B-1-2", {"commercializationScope": "international"}
    )
    assert rule["ruleExpectedPoints"] == 10


def test_unresolved_design_indicator():
    rule = expected_points_for_achievement(KRA_II_CATALOG, "kra-II-C-1-2-design", {"title": "Lobby"})
    assert rule["ruleExpectedPoints"] is None
    assert rule.get("unresolved")


def test_scoring_aggregate_caps_and_kra_cap():
    data = {
        "entries": {},
        "achievements": [
            {
                "id": "a1",
                "indicatorId": "kra-II-A-5",
                "submissionStatus": "submitted",
                "reviewStatus": "approved",
                "claimedPoints": 35,
                "reviewerVerifiedPoints": 35,
            },
            {
                "id": "a2",
                "indicatorId": "kra-II-A-5",
                "submissionStatus": "submitted",
                "reviewStatus": "approved",
                "claimedPoints": 35,
                "reviewerVerifiedPoints": 35,
            },
            {
                "id": "a3",
                "indicatorId": "kra-II-A-5",
                "submissionStatus": "submitted",
                "reviewStatus": "approved",
                "claimedPoints": 35,
                "reviewerVerifiedPoints": 35,
            },
            {
                "id": "p1",
                "indicatorId": "kra-II-C-1-4-3",
                "submissionStatus": "submitted",
                "reviewStatus": "approved",
                "claimedPoints": 2,
                "reviewerVerifiedPoints": 2,
            },
        ],
    }
    scores = compute_faculty_scores(data, KRA_II_CATALOG, {"kra-II": 0.2})
    kra_ver = scores["verified"]["byKra"]["kra-II"]
    # 70 aggregate cap on kra-II-A-5 (3×35) + 2 poetry
    assert kra_ver["rawTotal"] == 72.0
    assert kra_ver["weightedContribution"] == round(72.0 * 0.2, 4)
    crit_a = next(c for c in kra_ver["criteria"] if c["id"] == "kra-II-A")
    assert crit_a["rawTotal"] == 70.0
    kra_est = scores["estimated"]["byKra"]["kra-II"]
    assert kra_est["rawTotal"] == kra_ver["rawTotal"]


def test_commercialization_tier_subcap_in_scoring():
    data = {
        "entries": {},
        "achievements": [
            {
                "id": f"c{i}",
                "indicatorId": "kra-II-B-1-2",
                "commercializationScope": "local",
                "submissionStatus": "submitted",
                "reviewStatus": "approved",
                "claimedPoints": 5,
                "reviewerVerifiedPoints": 5,
            }
            for i in range(6)
        ],
    }
    scores = compute_faculty_scores(data, KRA_II_CATALOG, {"kra-II": 0.2})
    crit_b = next(c for c in scores["verified"]["byKra"]["kra-II"]["criteria"] if c["id"] == "kra-II-B")
    assert crit_b["rawTotal"] == 20.0  # 6×5 local, tier cap 20


def test_kra_ii_raw_total_capped_at_kra_max():
    """Workbook KRA II max 100 — credited raw sum must not exceed kra maxPoints."""
    data = {
        "entries": {},
        "achievements": [
            {
                "id": f"a{i}",
                "indicatorId": "kra-II-A-3",
                "submissionStatus": "submitted",
                "reviewStatus": "approved",
                "claimedPoints": 100,
                "reviewerVerifiedPoints": 100,
            }
            for i in range(2)
        ],
    }
    scores = compute_faculty_scores(data, KRA_II_CATALOG, {"kra-II": 0.2})
    kra_ver = scores["verified"]["byKra"]["kra-II"]
    assert kra_ver["rawTotal"] == 100.0
    assert kra_ver["weightedContribution"] == 20.0
