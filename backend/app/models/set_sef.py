from datetime import datetime, timezone

from app.extensions import db


class DocumentProcessingJob(db.Model):
    __tablename__ = "document_processing_jobs"

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    job_type = db.Column(db.String(32), nullable=False, default="set_sef_ocr")
    status = db.Column(db.String(32), nullable=False, default="pending", index=True)
    attempts = db.Column(db.Integer, nullable=False, default=0)
    last_error = db.Column(db.String(500), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    started_at = db.Column(db.DateTime(timezone=True), nullable=True)
    finished_at = db.Column(db.DateTime(timezone=True), nullable=True)

    document = db.relationship("Document", backref=db.backref("processing_jobs", lazy="dynamic"))


class SetSefSemesterRecord(db.Model):
    __tablename__ = "set_sef_semester_records"

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    owner_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year = db.Column(db.String(32), nullable=True)
    semester = db.Column(db.String(32), nullable=True)
    semester_key = db.Column(db.String(64), nullable=True, index=True)
    faculty_name_extracted = db.Column(db.String(200), nullable=True)
    faculty_identity_status = db.Column(db.String(32), nullable=False, default="missing")
    set_rating_extracted = db.Column(db.Numeric(10, 2), nullable=True)
    set_scale_extracted = db.Column(db.String(64), nullable=True)
    set_rating_confirmed = db.Column(db.Numeric(10, 2), nullable=True)
    set_verification_status = db.Column(db.String(32), nullable=False, default="pending")
    set_source_pages = db.Column(db.JSON, nullable=True)
    set_excerpt = db.Column(db.Text, nullable=True)
    sef_rating_extracted = db.Column(db.Numeric(10, 2), nullable=True)
    sef_scale_extracted = db.Column(db.String(64), nullable=True)
    sef_rating_confirmed = db.Column(db.Numeric(10, 2), nullable=True)
    sef_verification_status = db.Column(db.String(32), nullable=False, default="pending")
    sef_source_pages = db.Column(db.JSON, nullable=True)
    sef_excerpt = db.Column(db.Text, nullable=True)
    ocr_raw_fragment = db.Column(db.Text, nullable=True)
    superseded_by_id = db.Column(db.Integer, db.ForeignKey("set_sef_semester_records.id"), nullable=True)
    document = db.relationship("Document", backref=db.backref("set_sef_semester_records", lazy="dynamic"))
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self, profile_name: str | None = None) -> dict:
        return {
            "id": self.id,
            "academicYear": self.academic_year or "",
            "semester": self.semester or "",
            "semesterKey": self.semester_key or "",
            "facultyNameExtracted": self.faculty_name_extracted or "",
            "profileFacultyName": profile_name or "",
            "facultyIdentityStatus": self.faculty_identity_status,
            "setRatingExtracted": float(self.set_rating_extracted) if self.set_rating_extracted is not None else None,
            "setScaleExtracted": self.set_scale_extracted or "",
            "setRatingConfirmed": float(self.set_rating_confirmed) if self.set_rating_confirmed is not None else None,
            "setVerificationStatus": self.set_verification_status,
            "setSourcePages": self.set_source_pages or [],
            "setExcerpt": self.set_excerpt or "",
            "sefRatingExtracted": float(self.sef_rating_extracted) if self.sef_rating_extracted is not None else None,
            "sefScaleExtracted": self.sef_scale_extracted or "",
            "sefRatingConfirmed": float(self.sef_rating_confirmed) if self.sef_rating_confirmed is not None else None,
            "sefVerificationStatus": self.sef_verification_status,
            "sefSourcePages": self.sef_source_pages or [],
            "sefExcerpt": self.sef_excerpt or "",
        }


class DocumentValidationFinding(db.Model):
    __tablename__ = "document_validation_findings"

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    rule_id = db.Column(db.String(64), nullable=False)
    outcome = db.Column(db.String(32), nullable=False)
    affected_field = db.Column(db.String(64), nullable=True)
    semester_key = db.Column(db.String(64), nullable=True)
    explanation = db.Column(db.Text, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self) -> dict:
        return {
            "ruleId": self.rule_id,
            "outcome": self.outcome,
            "affectedField": self.affected_field or "",
            "semesterKey": self.semester_key or "",
            "explanation": self.explanation,
        }
