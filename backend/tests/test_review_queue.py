"""Reviewer queue must not count B/C evidence files as legacy pending documents."""

from app.services.review_queue import classify_bc_evidence_file, document_counts_toward_legacy_pending


class _Doc:
    def __init__(self, public_id, indicator_id, review_status="pending", upload_status="stored"):
        self.public_id = public_id
        self.indicator_id = indicator_id
        self.review_status = review_status
        self.upload_status = upload_status
        self.owner_user_id = 1


def test_bc_evidence_excluded_from_legacy_pending():
    doc = _Doc("d1", "kra-I-B-1-2")
    assert document_counts_toward_legacy_pending(doc, []) is False


def test_set_doc_still_pending():
    doc = _Doc("d2", "kra-I-A-setsef-combined")
    assert document_counts_toward_legacy_pending(doc, []) is True


def test_classify_unlinked_bc_upload():
    doc = _Doc("d3", "kra-I-C-1")
    assert classify_bc_evidence_file(doc, []) == "uploaded_unlinked"


def test_classify_submitted_achievement():
    doc = _Doc("d4", "kra-I-B-1-2")
    ach = [
        {
            "id": "a1",
            "documentIds": ["d4"],
            "submissionStatus": "submitted",
            "reviewStatus": "pending",
        }
    ]
    assert classify_bc_evidence_file(doc, ach) == "submitted_for_review"

