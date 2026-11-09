"""Mark stored KRA I B/C uploads as review_status=evidence (not legacy pending queue)."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.services.review_queue import reconcile_bc_evidence_review_status


def main() -> None:
    app = create_app()
    with app.app_context():
        n = reconcile_bc_evidence_review_status()
        if n:
            db.session.commit()
        print(f"Updated {n} document(s) to review_status=evidence.")


if __name__ == "__main__":
    main()
