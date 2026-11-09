"""Isolated checks: catalog parameters drive Criterion A math (no live DB policy changes)."""

import pytest

from app.models import SetSefSemesterRecord
from app.services.catalog import (
    CRITERION_A_POLICY_LEGACY,
    criterion_a_calculation_params,
    get_catalog_for_assessment,
    reassign_assessment_config_version,
)
from app.services.teaching_effectiveness import compute_criterion_a_from_records

SAMPLE_CATALOG = {
    "version": "isolated-test-v1",
    "kras": [
        {
            "id": "kra-I",
            "criteria": [
                {
                    "id": "kra-I-A",
                    "maxPoints": 60,
                    "indicators": [
                        {
                            "id": "kra-I-A-set",
                            "subType": "SET",
                            "maxPoints": 36,
                            "calculation": {"kind": "set_sef_average", "factor": 0.30, "semesterCount": 6},
                        },
                        {
                            "id": "kra-I-A-sef",
                            "subType": "SEF",
                            "maxPoints": 24,
                            "calculation": {"kind": "set_sef_average", "factor": 0.24, "semesterCount": 6},
                        },
                    ],
                }
            ],
        }
    ],
}

PINNED_META = {
    "versions": [
        {
            "id": "pinned-v1",
            "status": "published",
            "catalog": SAMPLE_CATALOG,
            "kraWeights": {"kra-I": 0.25},
        },
        {
            "id": "active-v2",
            "status": "published",
            "catalog": {**SAMPLE_CATALOG, "version": "active-v2"},
            "kraWeights": {"kra-I": 0.25},
        },
    ],
    "activePublishedId": "active-v2",
}


def _six_verified_records() -> list[SetSefSemesterRecord]:
    records = []
    for i in range(6):
        records.append(
            SetSefSemesterRecord(
                document_id=1,
                owner_user_id=1,
                set_rating_extracted=100.0,
                set_rating_confirmed=100.0,
                set_verification_status="verified",
                sef_rating_extracted=100.0,
                sef_rating_confirmed=100.0,
                sef_verification_status="verified",
                academic_year="2023-2024",
                semester=f"Sem {i + 1}",
            )
        )
    return records


def test_criterion_a_params_from_catalog():
    params = criterion_a_calculation_params(SAMPLE_CATALOG)
    assert params["set_factor"] == 0.30
    assert params["sef_factor"] == 0.24
    assert params["required_slots"] == 6
    assert params["set_max"] == 36.0
    assert params["calculation_policy"] == CRITERION_A_POLICY_LEGACY


def test_criterion_a_scoring_uses_catalog_factor_not_hardcoded():
    records = _six_verified_records()
    default_out = compute_criterion_a_from_records(records, verified_only=True, catalog=None)
    custom_out = compute_criterion_a_from_records(records, verified_only=True, catalog=SAMPLE_CATALOG)

    assert default_out["setPoints"] == 36.0
    assert default_out["calculationPolicy"] == CRITERION_A_POLICY_LEGACY
    assert default_out["parametersSource"] == "defaults"
    assert custom_out["setPoints"] == 30.0
    assert custom_out["parametersSource"] == "catalog"
    assert custom_out["criterionAPoints"] == 54.0


def test_pinned_assessment_uses_version_record_not_active(app_ctx, monkeypatch):
    store = {
        "assessment_config_meta": PINNED_META,
    }

    def fake_get_json(key, default=None):
        return store.get(key, default)

    monkeypatch.setattr("app.services.catalog.get_json", fake_get_json)
    assessment = {"configVersionId": "pinned-v1", "setSef": {"SET": [], "SEF": []}, "entries": {}}
    catalog, weights = get_catalog_for_assessment(assessment)
    assert catalog is not None
    assert catalog.get("version") == "isolated-test-v1"
    assert weights == {"kra-I": 0.25}


def test_reassign_records_audit_trail(app_ctx, monkeypatch):
    store = {"assessment_config_meta": PINNED_META}

    def fake_get_json(key, default=None):
        return store.get(key, default)

    monkeypatch.setattr("app.services.catalog.get_json", fake_get_json)
    data = {"configVersionId": "pinned-v1", "entries": {}}
    updated = reassign_assessment_config_version(
        data, new_version_id="active-v2", actor_email="admin@test", reason="Policy update"
    )
    assert updated["configVersionId"] == "active-v2"
    hist = updated["configVersionHistory"]
    assert len(hist) == 1
    assert hist[0]["from"] == "pinned-v1"
    assert hist[0]["to"] == "active-v2"
    assert hist[0]["actor"] == "admin@test"


@pytest.fixture
def settings_memory(app_ctx, monkeypatch):
    """In-memory app_settings for draft/publish isolation tests."""
    store: dict = {}

    def get_json(key, default=None):
        return store.get(key, default)

    def set_json(key, value):
        store[key] = value

    monkeypatch.setattr("app.services.settings_store.get_json", get_json)
    monkeypatch.setattr("app.services.settings_store.set_json", set_json)
    return store


def test_draft_meta_save_does_not_replace_published_catalog(settings_memory):
    from app.services.settings_store import ASSESSMENT_CONFIG_KEY, CATALOG_DRAFT_KEY, CATALOG_PUBLISHED_KEY, set_json

    live_pub = {"version": "live-v1", "kras": [{"id": "kra-I", "criteria": []}]}
    set_json(CATALOG_PUBLISHED_KEY, live_pub)
    draft_meta = {
        **PINNED_META,
        "draftId": "draft-xyz",
        "versions": PINNED_META["versions"]
        + [{"id": "draft-xyz", "status": "draft", "catalog": {"version": "draft-only"}}],
    }
    set_json(ASSESSMENT_CONFIG_KEY, draft_meta)
    set_json(CATALOG_DRAFT_KEY, {"catalog": {"version": "draft-only"}})

    assert settings_memory[CATALOG_PUBLISHED_KEY]["version"] == "live-v1"
    assert settings_memory[ASSESSMENT_CONFIG_KEY]["draftId"] == "draft-xyz"


def test_publish_swaps_published_blob_from_active_version(settings_memory):
    from app.services.settings_store import ASSESSMENT_CONFIG_KEY, CATALOG_PUBLISHED_KEY, set_json

    active_catalog = {**SAMPLE_CATALOG, "version": "published-2026"}
    meta = {
        "activePublishedId": "published-2026",
        "draftId": None,
        "versions": [
            {"id": "published-2026", "status": "published", "catalog": active_catalog, "kraWeights": {}},
        ],
    }
    set_json(ASSESSMENT_CONFIG_KEY, meta)
    set_json(CATALOG_PUBLISHED_KEY, {"version": "old"})

    # Mirror publish_catalog meta branch
    published = next(v for v in meta["versions"] if v["id"] == meta["activePublishedId"])
    set_json(CATALOG_PUBLISHED_KEY, published["catalog"])

    assert settings_memory[CATALOG_PUBLISHED_KEY]["version"] == "published-2026"
    assert params_factor(settings_memory[CATALOG_PUBLISHED_KEY]) == 0.30


def params_factor(catalog):
    return criterion_a_calculation_params(catalog)["set_factor"]
