"""Notification recipient scoping and deduplication."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.extensions import db
from app.models import Document, Notification, ReviewerAssignment, User, UserRole
from app.services.notification_service import (
    create_notification,
    notifications_for_user,
    notify_faculty_document_review,
    notify_reviewers_document_resubmitted,
    unread_count_for_user,
)


def _seed_users():
    tag = uuid.uuid4().hex[:8]
    faculty = User(
        email=f"f1-{tag}@test.local",
        role=UserRole.faculty,
        full_name="Fac One",
        password_hash="x",
    )
    faculty2 = User(
        email=f"f2-{tag}@test.local",
        role=UserRole.faculty,
        full_name="Fac Two",
        password_hash="x",
    )
    reviewer = User(
        email=f"r1-{tag}@test.local",
        role=UserRole.reviewer,
        full_name="Rev One",
        password_hash="x",
    )
    reviewer2 = User(
        email=f"r2-{tag}@test.local",
        role=UserRole.reviewer,
        full_name="Rev Two",
        password_hash="x",
    )
    db.session.add_all([faculty, faculty2, reviewer, reviewer2])
    db.session.flush()
    db.session.add(ReviewerAssignment(faculty_user_id=faculty.id, reviewer_user_id=reviewer.id))
    db.session.add(ReviewerAssignment(faculty_user_id=faculty2.id, reviewer_user_id=reviewer2.id))
    db.session.commit()
    return faculty.id, faculty2.id, reviewer.id


def test_faculty_only_sees_own_notifications(app):
    with app.app_context():
        f1_id, f2_id, rev_id = _seed_users()
        faculty = User.query.get(f1_id)
        faculty2 = User.query.get(f2_id)
        reviewer = User.query.get(rev_id)
        doc = Document(
            public_id=str(uuid.uuid4()),
            owner_user_id=f1_id,
            object_key=f"k/a-{uuid.uuid4().hex}.pdf",
            original_filename="a.pdf",
            mime_type="application/pdf",
            size_bytes=1,
            upload_status="stored",
            review_status="approved",
            reviewed_at=datetime.now(timezone.utc),
        )
        db.session.add(doc)
        db.session.flush()
        notify_faculty_document_review(owner=faculty, doc=doc, actor=reviewer, status="approved")
        db.session.commit()

        f1 = notifications_for_user(faculty)
        f2 = notifications_for_user(faculty2)
        assert len(f1) == 1
        assert len(f2) == 0
        assert f1[0]["targetDocumentPublicId"] == doc.public_id
        assert unread_count_for_user(f2_id) == 0


def test_reviewer_inbox_not_faculty_messages(app):
    with app.app_context():
        f1_id, _, rev_id = _seed_users()
        faculty = User.query.get(f1_id)
        reviewer = User.query.get(rev_id)
        doc = Document(
            public_id=str(uuid.uuid4()),
            owner_user_id=f1_id,
            object_key=f"k/b-{uuid.uuid4().hex}.pdf",
            original_filename="b.pdf",
            mime_type="application/pdf",
            size_bytes=1,
            upload_status="stored",
            review_status="pending",
        )
        db.session.add(doc)
        db.session.flush()
        doc.reviewed_at = datetime.now(timezone.utc)
        notify_faculty_document_review(
            owner=faculty,
            doc=doc,
            actor=reviewer,
            status="correction_requested",
        )
        notify_reviewers_document_resubmitted(doc)
        db.session.commit()

        rev_notes = notifications_for_user(reviewer)
        fac_notes = notifications_for_user(faculty)
        assert len(fac_notes) == 1
        assert fac_notes[0]["eventType"] == "document_review_decision"
        assert len(rev_notes) == 1
        assert rev_notes[0]["eventType"] == "document_resubmitted"
        assert all(n["eventType"] != "document_review_decision" for n in rev_notes)


def test_dedupe_same_event(app):
    with app.app_context():
        f1_id, _, _ = _seed_users()
        faculty = User.query.get(f1_id)
        n1 = create_notification(
            recipient_user_id=faculty.id,
            event_type="document_submitted",
            title="x",
            body="y",
            dedupe_key=f"test:{uuid.uuid4().hex}",
        )
        n2 = create_notification(
            recipient_user_id=faculty.id,
            event_type="document_submitted",
            title="x",
            body="y",
            dedupe_key=n1.dedupe_key,
        )
        db.session.commit()
        assert n1 is not None and n2 is not None
        assert n1.id == n2.id
        assert Notification.query.filter_by(user_id=faculty.id, dedupe_key=n1.dedupe_key).count() == 1