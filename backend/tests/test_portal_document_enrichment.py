from app.services.portal_document_enrichment import enrich_portal_documents


def test_enrich_dedupes_and_links_parent_achievement():
    assessments = {
        "u-1": {
            "achievements": [
                {
                    "id": "ach-1",
                    "title": "Textbook",
                    "submissionStatus": "submitted",
                    "reviewStatus": "approved",
                    "documentIds": ["doc-a", "doc-a"],
                }
            ]
        }
    }
    raw = [
        {"id": "doc-a", "fileName": "a.pdf", "reviewStatus": "pending"},
        {"id": "doc-a", "fileName": "a.pdf", "reviewStatus": "pending"},
        {"id": "doc-b", "fileName": "b.pdf", "reviewStatus": "pending"},
    ]
    out = enrich_portal_documents(raw, assessments)
    assert len(out) == 2
    by_id = {d["id"]: d for d in out}
    assert by_id["doc-a"]["linkedAchievementId"] == "ach-1"
    assert by_id["doc-a"]["parentReviewStatus"] == "approved"
    assert "linkedAchievementId" not in by_id["doc-b"]
