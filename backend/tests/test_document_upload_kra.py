"""Document upload: indicator must match parent kraId (not criterion id)."""

import pytest

from app.services.catalog import CatalogValidationError, validate_indicator_kra

MINIMAL_KRA_III = {
    "version": "kra-iii-upload-test",
    "kras": [
        {
            "id": "kra-III",
            "criteria": [
                {
                    "id": "kra-III-B",
                    "indicators": [
                        {
                            "id": "kra-III-B-2-1",
                            "name": "Extension project",
                            "calculation": {"kind": "tiered_option", "options": {"lead": 5, "participant": 2}},
                        }
                    ],
                }
            ],
        }
    ],
}


def test_validate_extension_project_parent_kra():
    found = validate_indicator_kra(MINIMAL_KRA_III, "kra-III-B-2-1", "kra-III")
    assert found["kra"]["id"] == "kra-III"
    assert found["criterion"]["id"] == "kra-III-B"


def test_reject_criterion_id_as_kra_id():
    with pytest.raises(CatalogValidationError) as exc:
        validate_indicator_kra(MINIMAL_KRA_III, "kra-III-B-2-1", "kra-III-B")
    assert "parent KRA" in str(exc.value) or "kra-III" in str(exc.value)


def test_reject_wrong_parent_kra_prefix_bug():
    with pytest.raises(CatalogValidationError):
        validate_indicator_kra(MINIMAL_KRA_III, "kra-III-B-2-1", "kra-I")


def test_kra_iv_indicator_parent_kra():
    catalog = {
        "kras": [
            {
                "id": "kra-IV",
                "criteria": [{"id": "kra-IV-B", "indicators": [{"id": "kra-IV-B-2"}]}],
            }
        ],
    }
    validate_indicator_kra(catalog, "kra-IV-B-2", "kra-IV")
    with pytest.raises(CatalogValidationError):
        validate_indicator_kra(catalog, "kra-IV-B-2", "kra-IV-B")


def test_kra_i_and_ii_indicators():
    catalog = {
        "kras": [
            {
                "id": "kra-I",
                "criteria": [{"id": "kra-I-B", "indicators": [{"id": "kra-I-B-1-2"}]}],
            },
            {
                "id": "kra-II",
                "criteria": [{"id": "kra-II-B", "indicators": [{"id": "kra-II-B-1-1"}]}],
            },
        ],
    }
    validate_indicator_kra(catalog, "kra-I-B-1-2", "kra-I")
    validate_indicator_kra(catalog, "kra-II-B-1-1", "kra-II")
    with pytest.raises(CatalogValidationError):
        validate_indicator_kra(catalog, "kra-II-B-1-1", "kra-II-B")


def test_missing_indicator():
    with pytest.raises(CatalogValidationError) as exc:
        validate_indicator_kra(MINIMAL_KRA_III, "kra-III-B-9-9", "kra-III")
    assert "not in the published" in str(exc.value).lower() or "not in" in str(exc.value).lower()
