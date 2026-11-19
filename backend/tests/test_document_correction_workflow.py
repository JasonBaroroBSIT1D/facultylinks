"""Needs changes → replace → resubmit."""

from __future__ import annotations

import uuid

import pytest

from app.extensions import db
from app.models import Document, Notification, ReviewerAssignment, User, UserRole
from app.services.document_correction import (
    REVIEW_CORRECTION_PREPARED,
    apply_document_replacement,
    faculty_may_replace_document,
    faculty_may_resubmit_document,
    resubmit_document_for_review,
)


def test_apply_replacement_and_resubmit(app):
    with app.app_context():
        tag = uuid.uuid4().hex[:8]
        owner = User(
            email=f"own-{tag}@test.local",
            role=UserRole.faculty,
            full_name="Owner",
            password_hash="x",
        )
        reviewer = User(
            email=f"rev-{tag}@test.local",
            role=UserRole.reviewer,
            full_name="Rev",
            password_hash="x",
        )
        db.session.add_all([owner, reviewer])
        db.session.flush()
        db.session.add(ReviewerAssignment(faculty_user_id=owner.id, reviewer_user_id=reviewer.id))

        old = Document(
            public_id=str(uuid.uuid4()),
            owner_user_id=owner.id,
            object_key=f"k/o-{uuid.uuid4().hex}.pdf",
            original_filename="old.pdf",
            mime_type="application/pdf",
            size_bytes=1,
            upload_status="stored",
            indicator_id="kra-IV-A-1",
            review_status="correction_requested",
            entry_id="ent-1",
        )
        new = Document(
            public_id=str(uuid.uuid4()),
            owner_user_id=owner.id,
            object_key=f"k/n-{uuid.uuid4().hex}.pdf",
            original_filename="new.pdf",
            mime_type="application/pdf",
            size_bytes=1,
            upload_status="stored",
            indicator_id="kra-IV-A-1",
            review_status="pending",
        )
        db.session.add_all([old, new])
        db.session.commit()

        assert faculty_may_replace_document(old)
        apply_document_replacement(old=old, new=new)
        assert old.review_status == "replaced"
        assert old.superseded_by_public_id == new.public_id
        assert new.review_status == REVIEW_CORRECTION_PREPARED
        assert new.verified_points is None

        assert faculty_may_resubmit_document(new)
        resubmit_document_for_review(new, actor=owner)
        assert new.review_status == "pending"
        db.session.commit()
        notes = Notification.query.filter_by(user_id=reviewer.id).all()
        assert notes
        assert "resubmit" in notes[-1].title.lower()

        with pytest.raises(ValueError):
            resubmit_document_for_review(new, actor=owner)


def test_evidence_replace_allowed_via_parent_correction():
    doc = Document(
        public_id=str(uuid.uuid4()),
        owner_user_id=1,
        object_key="k/x.pdf",
        original_filename="x.pdf",
        mime_type="application/pdf",
        size_bytes=1,
        upload_status="stored",
        indicator_id="kra-II-A-3",
        kra_id="kra-II",
        review_status="evidence",
    )
    links = [
        {
            "parentReviewStatus": "correction_requested",
            "parentSubmissionStatus": "submitted",
        }
    ]
    assert faculty_may_replace_document(doc, achievement_links=links)