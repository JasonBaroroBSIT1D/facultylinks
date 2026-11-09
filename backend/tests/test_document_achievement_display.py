from app.services.document_achievement_display import (
    derive_achievement_display_status,
    enrich_document_dict_for_achievements,
)


def test_approved_parent_display():
    links = [
        {
            "linkedAchievementId": "ach-1",
            "criterionId": "kra-I-B",
            "parentSubmissionStatus": "submitted",
            "parentReviewStatus": "approved",
            "parentAchievementTitle": "Textbook",
        }
    ]
    disp = derive_achievement_display_status(links, indicator_id="kra-I-B-1-1")
    assert disp["displayStatus"] == "part_of_approved_achievement"
    base = {"id": "doc-1", "reviewStatus": "pending", "indicatorId": "kra-I-B-1-1"}
    out = enrich_document_dict_for_achievements(base, links)
    assert out["reviewStatus"] == "pending"
    assert out["displayStatusLabel"] == "Part of approved achievement"
    assert out["linkedAchievementId"] == "ach-1"


def test_criterion_a_unchanged():
    assert derive_achievement_display_status([], indicator_id="kra-I-A-setsef-eval") is None


def test_multiple_parents():
    links = [
        {"parentSubmissionStatus": "submitted", "parentReviewStatus": "approved"},
        {"parentSubmissionStatus": "submitted", "parentReviewStatus": "pending"},
    ]
    disp = derive_achievement_display_status(links, indicator_id="kra-I-B-1-2")
    assert disp["displayStatus"] == "achievement_multiple_parents"
