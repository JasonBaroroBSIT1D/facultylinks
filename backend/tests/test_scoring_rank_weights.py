"""Rank-category KRA weights (JC3 Table 2.2) applied once after raw KRA totals."""

import pytest

from app.services.rank_simulation import (
    DEFAULT_WEIGHT_MATRIX,
    apply_rank_weights,
    merge_rank_simulation_config,
    resolve_rank_category,
    resolve_rank_kra_weights,
)
from app.services.scoring_engine import compute_faculty_scores

KRA_I_RAW = {"kra-I": 58.92, "kra-II": 0.0, "kra-III": 0.0, "kra-IV": 0.0}


@pytest.mark.parametrize(
    "rank,expected_category",
    [
        ("Instructor I", "instructor"),
        ("Instructor II", "instructor"),
        ("Instructor III", "instructor"),
        ("Assistant Professor I", "assistant_professor"),
        ("Assistant Professor IV", "assistant_professor"),
        ("Associate Professor II", "associate_professor"),
        ("Associate Professor V", "associate_professor"),
        ("Professor III", "professor"),
        ("Professor VI", "professor"),
        ("College/University Professor", "college_university_professor"),
    ],
)
def test_sub_ranks_share_category(rank, expected_category):
    assert resolve_rank_category(rank) == expected_category


@pytest.mark.parametrize(
    "category,expected_contrib",
    [
        ("instructor", 35.352),
        ("assistant_professor", 29.46),
        ("associate_professor", 23.568),
        ("professor", 17.676),
        ("college_university_professor", 11.784),
    ],
)
def test_kra_i_58_92_weighted_contribution(category, expected_contrib):
    lines, total = apply_rank_weights(KRA_I_RAW, DEFAULT_WEIGHT_MATRIX[category])
    assert lines[0]["weightedContribution"] == pytest.approx(expected_contrib, abs=1e-3)
    assert total == pytest.approx(expected_contrib, abs=1e-3)


def test_weighted_sum_equals_overall():
    raw = {"kra-I": 58.92, "kra-II": 12.0, "kra-III": 30.0, "kra-IV": 8.0}
    weights = DEFAULT_WEIGHT_MATRIX["assistant_professor"]
    lines, total = apply_rank_weights(raw, weights)
    manual = sum(l["weightedContribution"] for l in lines)
    assert manual == pytest.approx(total, abs=1e-6)


def test_unknown_rank_no_instructor_fallback():
    res = resolve_rank_kra_weights("Visiting Lecturer", {})
    assert not res.ok
    assert res.error
    assert res.weights is None


def test_custom_saved_weights():
    inst = {
        "rankSimulation": {
            "weightMatrixByCategory": {
                "instructor": {"kra-I": 0.55, "kra-II": 0.15, "kra-III": 0.2, "kra-IV": 0.1},
            }
        }
    }
    res = resolve_rank_kra_weights("Instructor II", inst)
    assert res.ok
    assert res.weights["kra-I"] == pytest.approx(0.55)
    lines, total = apply_rank_weights(KRA_I_RAW, res.weights)
    assert lines[0]["weightedContribution"] == pytest.approx(58.92 * 0.55, abs=1e-3)


def test_invalid_weight_sum_configuration_error():
    inst = {
        "rankSimulation": {
            "weightMatrixByCategory": {
                "professor": {"kra-I": 0.3, "kra-II": 0.3, "kra-III": 0.2, "kra-IV": 0.1},
            }
        }
    }
    res = resolve_rank_kra_weights("Professor I", inst)
    assert not res.ok
    assert "100%" in res.error or "sum" in res.error.lower()


MINIMAL_CATALOG = {
    "kras": [
        {"id": "kra-I", "name": "Instruction", "maxPoints": 60, "criteria": []},
        {"id": "kra-II", "name": "Research", "maxPoints": 100, "criteria": []},
        {"id": "kra-III", "name": "Extension", "maxPoints": 100, "criteria": []},
        {"id": "kra-IV", "name": "Prof Dev", "maxPoints": 100, "criteria": []},
    ],
}


def test_compute_faculty_scores_uses_rank_weights_not_catalog():
    """Catalog kraWeights must not override rank matrix when faculty_rank is supplied."""
    scores = compute_faculty_scores(
        {"setSef": {"SET": [], "SEF": []}, "entries": {}},
        MINIMAL_CATALOG,
        {"kra-I": 0.25, "kra-II": 0.25, "kra-III": 0.25, "kra-IV": 0.25},
        faculty_rank="Instructor I",
        institution_config=merge_rank_simulation_config({}),
    )
    est = scores["estimated"]
    assert est["byKra"]["kra-I"]["weight"] == pytest.approx(0.6)
    assert est["rankWeightResolution"]["ok"] is True
    assert est["rankWeightResolution"]["categoryId"] == "instructor"