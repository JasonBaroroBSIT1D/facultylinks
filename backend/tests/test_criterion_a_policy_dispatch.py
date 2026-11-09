"""Regression: same partial input — legacy incomplete vs flexible estimate under new policy."""

from app.models import SetSefSemesterRecord
from app.services.catalog import CRITERION_A_POLICY_FLEXIBLE, CRITERION_A_POLICY_LEGACY
from app.services.teaching_effectiveness import compute_criterion_a_from_records, compute_manual_set_sef_points


def _legacy_catalog():
    return {
        "version": "legacy-catalog",
        "kras": [
            {
                "id": "kra-I",
                "criteria": [
                    {
                        "id": "kra-I-A",
                        "indicators": [
                            {
                                "id": "kra-I-A-set",
                                "subType": "SET",
                                "maxPoints": 36,
                                "calculation": {"factor": 0.36, "semesterCount": 6},
                            },
                            {
                                "id": "kra-I-A-sef",
                                "subType": "SEF",
                                "maxPoints": 24,
                                "calculation": {"factor": 0.24, "semesterCount": 6},
                            },
                        ],
                    }
                ],
            }
        ],
    }


def _flex_catalog():
    cat = _legacy_catalog()
    for ind in cat["kras"][0]["criteria"][0]["indicators"]:
        ind.setdefault("calculation", {})["policy"] = CRITERION_A_POLICY_FLEXIBLE
    cat["version"] = "flex-catalog"
    return cat


def _one_set_rating_record() -> list[SetSefSemesterRecord]:
    return [
        SetSefSemesterRecord(
            document_id=1,
            owner_user_id=1,
            set_rating_confirmed=90.0,
            set_verification_status="verified",
            sef_verification_status="pending",
            faculty_identity_status="match",
        )
    ]


def test_partial_input_legacy_incomplete_no_points():
    out = compute_criterion_a_from_records(
        _one_set_rating_record(), verified_only=False, catalog=_legacy_catalog()
    )
    assert out["calculationPolicy"] == CRITERION_A_POLICY_LEGACY
    assert out["setPoints"] is None
    assert out["partialSubtotal"] is None
    assert out["criterionAPoints"] is None
    assert out["incomplete"] is True
    assert out["calculationUnavailable"] is True


def test_partial_input_flexible_estimate():
    out = compute_criterion_a_from_records(
        _one_set_rating_record(), verified_only=False, catalog=_flex_catalog()
    )
    assert out["calculationPolicy"] == CRITERION_A_POLICY_FLEXIBLE
    assert out["setPoints"] == 32.4
    assert out["partialSubtotal"] == 32.4
    assert out["criterionAPoints"] is None
    assert out["incomplete"] is True
    assert out["calculationUnavailable"] is False


def test_manual_set_sef_same_dispatch():
    legacy = compute_manual_set_sef_points([90.0], [], catalog=_legacy_catalog())
    flex = compute_manual_set_sef_points([90.0], [], catalog=_flex_catalog())
    assert legacy["setPoints"] is None
    assert flex["setPoints"] == 32.4


def test_unknown_policy_configuration_error():
    bad = _flex_catalog()
    bad["kras"][0]["criteria"][0]["indicators"][0]["calculation"]["policy"] = "experimental_policy"
    out = compute_criterion_a_from_records(_one_set_rating_record(), catalog=bad)
    assert out.get("configurationError") is True
    assert "Unknown" in (out.get("configurationErrorMessage") or "")
