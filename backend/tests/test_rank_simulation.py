"""Rank simulation — Table 2.2 weights, Table 3.1 brackets, rank category resolution."""

import pytest

from app.services.rank_simulation import (
    DEFAULT_WEIGHT_MATRIX,
    apply_rank_weights,
    compute_rank_simulation_bucket,
    merge_rank_simulation_config,
    resolve_rank_category,
    resolve_sub_rank_bracket,
    validate_rank_simulation_config,
)

SYNTHETIC_RAW = {"kra-I": 80.0, "kra-II": 60.0, "kra-III": 50.0, "kra-IV": 40.0}


def _weighted_for_category(category_id: str) -> float:
    lines, total = apply_rank_weights(SYNTHETIC_RAW, DEFAULT_WEIGHT_MATRIX[category_id])
    assert len(lines) == 4
    return total


@pytest.mark.parametrize(
    "rank,expected",
    [
        ("Instructor I", "instructor"),
        ("Instructor III", "instructor"),
        ("Assistant Professor I", "assistant_professor"),
        ("Assistant Professor IV", "assistant_professor"),
        ("Associate Professor II", "associate_professor"),
        ("Professor VI", "professor"),
        ("College/University Professor", "college_university_professor"),
        ("College University Professor", "college_university_professor"),
    ],
)
def test_rank_category_resolution(rank, expected):
    assert resolve_rank_category(rank) == expected


def test_professor_does_not_match_assistant():
    assert resolve_rank_category("Assistant Professor II") == "assistant_professor"
    assert resolve_rank_category("Professor II") == "professor"


def test_unrecognized_rank():
    assert resolve_rank_category("") is None
    assert resolve_rank_category("Visiting Lecturer") is None


@pytest.mark.parametrize(
    "category,expected_total",
    [
        ("instructor", 68.0),
        ("assistant_professor", 66.0),
        ("associate_professor", 64.0),
        ("professor", 62.0),
        ("college_university_professor", 60.0),
    ],
)
def test_table_22_synthetic_totals(category, expected_total):
    assert _weighted_for_category(category) == expected_total


def test_weight_applied_once_not_double():
    """Overall equals sum of per-KRA raw × weight — no second multiplier."""
    weights = DEFAULT_WEIGHT_MATRIX["instructor"]
    lines, total = apply_rank_weights(SYNTHETIC_RAW, weights)
    manual = sum(l["rawTotal"] * l["weight"] for l in lines)
    assert abs(total - manual) < 1e-6
    assert total != sum(l["rawTotal"] for l in lines)


def test_estimated_vs_verified_buckets():
    score_est = {"byKra": {k: {"rawTotal": v} for k, v in SYNTHETIC_RAW.items()}, "notes": []}
    score_ver = {"byKra": {k: {"rawTotal": v + 5} for k, v in SYNTHETIC_RAW.items()}, "notes": []}
    inst = {"rankOptions": ["Instructor I", "Instructor II", "Instructor III", "Assistant Professor I"]}
    est = compute_rank_simulation_bucket(
        score_summary=score_est,
        current_rank="Instructor I",
        institution_config=inst,
        score_source="estimated",
    )
    ver = compute_rank_simulation_bucket(
        score_summary=score_ver,
        current_rank="Instructor I",
        institution_config=inst,
        score_source="verified",
    )
    assert est["scoreSource"] == "estimated"
    assert ver["scoreSource"] == "verified"
    assert ver["overallWeightedScore"] > est["overallWeightedScore"]


def test_missing_rank_profile_incomplete():
    bucket = compute_rank_simulation_bucket(
        score_summary={"byKra": {}, "notes": []},
        current_rank="",
        institution_config={},
        score_source="estimated",
    )
    assert bucket["configured"] is False
    assert bucket["status"] == "profile_incomplete"


def test_bracket_boundaries_whole_number():
    cfg = merge_rank_simulation_config({})
    assert resolve_sub_rank_bracket(41, cfg)["subRankIncrements"] == 1
    assert resolve_sub_rank_bracket(50, cfg)["subRankIncrements"] == 1
    assert resolve_sub_rank_bracket(51, cfg)["subRankIncrements"] == 2
    assert resolve_sub_rank_bracket(78, cfg)["subRankIncrements"] == 4
    assert resolve_sub_rank_bracket(100, cfg)["subRankIncrements"] == 6


def test_decimal_bracket_conditional():
    cfg = merge_rank_simulation_config({})
    b = resolve_sub_rank_bracket(78.02, cfg)
    assert b["status"] == "conditional"
    assert b["subRankIncrements"] is None
    assert b.get("provisionalIncrements") == 4
    assert len(b.get("conditionalProjections") or []) >= 1


def test_decimal_7062_dual_projections():
    cfg = merge_rank_simulation_config({})
    b = resolve_sub_rank_bracket(70.62, cfg)
    assert b["status"] == "conditional"
    projections = {p["policyKey"]: p["subRankIncrements"] for p in b["conditionalProjections"]}
    assert projections.get("floor_to_bracket") == 3
    assert projections.get("round_half_up") == 4


def test_estimated_6942_potential_rank_ladder():
    ladder = [
        "Instructor I",
        "Instructor II",
        "Instructor III",
        "Assistant Professor I",
        "Assistant Professor II",
    ]
    scores = {
        "byKra": {k: {"rawTotal": 69.42} for k in ("kra-I", "kra-II", "kra-III", "kra-IV")},
        "notes": [],
    }
    bucket = compute_rank_simulation_bucket(
        score_summary=scores,
        current_rank="Instructor I",
        institution_config={"rankOptions": ladder, "rankSimulation": {}},
        score_source="estimated",
    )
    assert bucket["overallWeightedScore"] == pytest.approx(69.42)
    assert bucket["basisLabel"] == "Estimated points"
    pr = bucket["potentialRank"]
    assert pr["potentialRank"] == "Assistant Professor I"
    assert pr["increments"] == 3
    assert pr["movement"] == "Instructor I → Assistant Professor I"


def test_below_41_no_increment():
    cfg = merge_rank_simulation_config({})
    b = resolve_sub_rank_bracket(40.99, cfg)
    assert b["status"] == "below_minimum"
    assert b["subRankIncrements"] == 0


def test_unresolved_envelope_blocks_authoritative_potential():
    scores = {
        "byKra": {
            "kra-IV": {"rawTotal": 120, "kraCapPolicyUnresolved": True},
            **{k: {"rawTotal": 0} for k in ("kra-I", "kra-II", "kra-III")},
        },
        "notes": ["Provisional scoring: envelope unresolved."],
    }
    bucket = compute_rank_simulation_bucket(
        score_summary=scores,
        current_rank="Instructor I",
        institution_config={"rankOptions": ["Instructor I", "Instructor II"]},
        score_source="verified",
    )
    assert bucket["scoringAuthoritative"] is False
    assert bucket["basisLabel"] == "Reviewer-verified points"
    pr = bucket["potentialRank"]
    assert pr["potentialRank"] is not None


def test_provisional_scoring_still_names_destination():
    scores = {
        "byKra": {k: {"rawTotal": 69.42} for k in ("kra-I", "kra-II", "kra-III", "kra-IV")},
        "notes": ["Provisional scoring: envelope unresolved."],
        "scoringAuthoritative": False,
    }
    bucket = compute_rank_simulation_bucket(
        score_summary=scores,
        current_rank="Instructor I",
        institution_config={
            "rankOptions": ["Instructor I", "Instructor II", "Instructor III", "Assistant Professor I"],
            "rankSimulation": {},
        },
        score_source="verified",
    )
    assert bucket["scoringAuthoritative"] is False
    assert bucket["potentialRank"]["status"] == "eligibility_required"
    assert bucket["potentialRank"]["potentialRank"] == "Assistant Professor I"
    assert bucket["potentialRank"]["displayLabel"] == "Projected rank — provisional scoring"


def test_validate_weight_matrix_sum():
    bad = {
        "weightMatrixByCategory": {
            "instructor": {"kra-I": 0.5, "kra-II": 0.1, "kra-III": 0.2, "kra-IV": 0.1},
        }
    }
    errs = validate_rank_simulation_config(bad)
    assert any("sum" in e.lower() for e in errs)
