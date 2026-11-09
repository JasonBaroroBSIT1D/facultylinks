"""Regression: upload API document payload uses public UUID as id/publicId, not DB primary key."""

from app.models import Document


def test_document_to_dict_uses_public_uuid_not_internal_id():
    doc = Document(
        public_id="d4e5f6a7-b8c9-0123-def0-234567890abc",
        owner_user_id=1,
        object_key="u/1/x.pdf",
        original_filename="x.pdf",
        mime_type="application/pdf",
        size_bytes=100,
        upload_status="stored",
    )
    # SQLAlchemy would assign numeric doc.id after flush; simulate internal key distinct from public_id.
    doc.id = 99

    payload = doc.to_dict()
    assert payload["id"] == "d4e5f6a7-b8c9-0123-def0-234567890abc"
    assert payload["publicId"] == "d4e5f6a7-b8c9-0123-def0-234567890abc"
    assert payload["id"] != "99"
