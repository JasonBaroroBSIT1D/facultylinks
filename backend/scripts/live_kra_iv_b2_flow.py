"""
Live KRA IV-B-2 flow against http://127.0.0.1:5000 (run backend first).

Creates a clearly tagged achievement, does not publish/repin/change catalog.
Issues short-lived API tokens via DB (same as mobile login) — no password required.
"""
from __future__ import annotations

import io
import json
import sys
import uuid
from pathlib import Path
from urllib import error, request as urlrequest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from app.models import User
from app.services.auth_context import issue_api_token

BASE = "http://127.0.0.1:5000"
TEST_TITLE = "LIVE-TEST KRA IV-B-2 international attendance 2026-11-09"
FACULTY_EMAIL = "jasonbaroro5@gmail.com"
REVIEWER_EMAIL = "jaso.jary@gmail.com"


def minimal_pdf() -> bytes:
    return b"""%PDF-1.4
1 0 obj<<>>endobj
2 0 obj<</Length 44>>stream
BT /F1 12 Tf 100 700 Td (KRA IV B-2 sample) Tj ET
endstream endobj
3 0 obj<</Type /Page /Parent 4 0 R /Resources<</Font<</F1 5 0 R>>>> /MediaBox[0 0 612 792] /Contents 2 0 R>>endobj
4 0 obj<</Type /Pages /Kids[3 0 R] /Count 1>>endobj
5 0 obj<</Type /Font /Subtype /Type1 /BaseFont /Helvetica>>endobj
6 0 obj<</Type /Catalog /Pages 4 0 R>>endobj
xref
0 7
0000000000 65535 f
0000000009 00000 n
0000000028 00000 n
0000000126 00000 n
0000000295 00000 n
0000000352 00000 n
0000000429 00000 n
trailer<</Size 7 /Root 6 0 R>>
startxref
503
%%EOF
"""


def http_json(method: str, path: str, *, headers: dict | None = None, data: bytes | None = None) -> tuple[int, dict | str]:
    req = urlrequest.Request(f"{BASE}{path}", data=data, headers=headers or {}, method=method)
    try:
        with urlrequest.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode()
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, raw
    except error.HTTPError as exc:
        body = exc.read().decode()
        try:
            return exc.code, json.loads(body)
        except json.JSONDecodeError:
            return exc.code, body


def http_multipart(path: str, *, headers: dict, fields: dict, file_field: tuple[str, bytes, str]) -> tuple[int, dict | str]:
    boundary = f"----facultylink{uuid.uuid4().hex}"
    fname, fbytes, mime = file_field
    parts = []
    for key, val in fields.items():
        parts.append(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"\r\n\r\n{val}\r\n".encode()
        )
    parts.append(
        (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{fname}\"\r\n"
            f"Content-Type: {mime}\r\n\r\n"
        ).encode()
        + fbytes
        + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())
    body = b"".join(parts)
    h = {**headers, "Content-Type": f"multipart/form-data; boundary={boundary}"}
    return http_json("POST", path, headers=h, data=body)


def main() -> int:
    code, health = http_json("GET", "/api/health")
    if code != 200:
        print(f"FAIL health: {code} {health}", file=sys.stderr)
        return 1

    app = create_app()
    with app.app_context():
        faculty = User.query.filter_by(email=FACULTY_EMAIL).first()
        reviewer = User.query.filter_by(email=REVIEWER_EMAIL).first()
        if not faculty or not reviewer:
            print("FAIL missing faculty/reviewer users", file=sys.stderr)
            return 1
        faculty_token = issue_api_token(faculty, app.config["API_TOKEN_TTL_HOURS"])
        reviewer_token = issue_api_token(reviewer, app.config["API_TOKEN_TTL_HOURS"])
        faculty_portal_id = faculty.portal_id()

    f_headers = {
        "Authorization": f"Bearer {faculty_token}",
        "X-Client-Type": "faculty_mobile",
    }
    r_headers = {
        "Authorization": f"Bearer {reviewer_token}",
        "X-Client-Type": "web",
    }

    code, me = http_json("GET", "/api/auth/me", headers=f_headers)
    print("faculty auth/me", code, str(me)[:200])
    if code != 200:
        return 1

    pdf = minimal_pdf()
    up_code, up_body = http_multipart(
        "/api/documents",
        headers=f_headers,
        fields={
            "indicatorId": "kra-IV-B-2",
            "kraId": "kra-IV",
            "title": TEST_TITLE,
            "estimatedPoints": "2",
        },
        file_field=("live-kra-iv-b2-sample.pdf", pdf, "application/pdf"),
    )
    print("upload", up_code, str(up_body)[:300])
    if up_code not in (200, 201):
        return 1
    doc_id = (up_body.get("document") or {}).get("publicId") if isinstance(up_body, dict) else None

    ach_id = f"ach-live-{uuid.uuid4().hex[:10]}"
    create_body = {
        "id": ach_id,
        "indicatorId": "kra-IV-B-2",
        "kraId": "kra-IV",
        "criterionId": "kra-IV-B",
        "title": TEST_TITLE,
        "description": "Live verification — international conference attendance",
        "attendanceScope": "international",
        "claimedPoints": 2,
        "documentIds": [doc_id] if doc_id else [],
    }
    cr_code, cr_body = http_json(
        "POST",
        "/api/faculty/achievements",
        headers={**f_headers, "Content-Type": "application/json"},
        data=json.dumps(create_body).encode(),
    )
    print("create", cr_code)
    if cr_code not in (200, 201):
        print(cr_body, file=sys.stderr)
        return 1
    ach = (cr_body.get("achievement") if isinstance(cr_body, dict) else {}) or {}
    ach_id = ach.get("id", ach_id)
    print("created", ach_id, "attendanceScope", ach.get("attendanceScope"), "docIds", ach.get("documentIds"))

    patch = {
        "description": create_body["description"] + " (reopened draft)",
        "attendanceScope": "international",
        "claimedPoints": 2,
    }
    upd_code, _ = http_json(
        "PUT",
        f"/api/faculty/achievements/{ach_id}",
        headers={**f_headers, "Content-Type": "application/json"},
        data=json.dumps(patch).encode(),
    )
    print("update", upd_code)
    re_code, re_body = http_json("GET", f"/api/faculty/achievements/{ach_id}", headers=f_headers)
    ach2 = (re_body.get("achievement") if isinstance(re_body, dict) else {}) or {}
    print("reget", re_code, "scope", ach2.get("attendanceScope"))

    sub_code, sub_body = http_json(
        "POST",
        f"/api/faculty/achievements/{ach_id}/submit",
        headers={**f_headers, "Content-Type": "application/json"},
        data=b"{}",
    )
    sub_ach = (sub_body.get("achievement") if isinstance(sub_body, dict) else {}) or {}
    print("submit", sub_code, sub_ach.get("submissionStatus"))
    if sub_code != 200:
        print(sub_body, file=sys.stderr)
        return 1

    portal_code, portal_body = http_json(
        "GET",
        f"/api/portal/faculty/{faculty_portal_id}/achievements?indicatorId=kra-IV-B-2&submitted=true",
        headers=r_headers,
    )
    items = (portal_body.get("achievements") if isinstance(portal_body, dict) else []) or []
    hit = next((a for a in items if a.get("id") == ach_id), None)
    print("reviewer list", portal_code, "found", bool(hit), "review", (hit or {}).get("reviewStatus"))

    if doc_id:
        view_code, view_body = http_json("GET", f"/api/documents/{doc_id}/view-url", headers=r_headers)
        url_len = len(((view_body.get("url") if isinstance(view_body, dict) else "") or ""))
        print("view-url", view_code, "url_len", url_len)

    rev_code, rev_body = http_json(
        "PATCH",
        f"/api/portal/achievements/{ach_id}/review",
        headers={**r_headers, "Content-Type": "application/json"},
        data=json.dumps(
            {
                "facultyId": faculty_portal_id,
                "reviewStatus": "approved",
                "reviewerVerifiedPoints": 2,
                "remarks": "LIVE-TEST approval — KRA IV-B-2 international",
            }
        ).encode(),
    )
    rev_ach = (rev_body.get("achievement") if isinstance(rev_body, dict) else {}) or {}
    print("review", rev_code, rev_ach.get("reviewStatus"))

    list_code, list_body = http_json("GET", "/api/faculty/achievements?indicatorId=kra-IV-B-2", headers=f_headers)
    final = next(
        (a for a in ((list_body.get("achievements") if isinstance(list_body, dict) else []) or []) if a.get("id") == ach_id),
        {},
    )
    print(
        "faculty refresh",
        final.get("submissionStatus"),
        final.get("reviewStatus"),
        final.get("reviewerVerifiedPoints"),
        final.get("documentIds"),
    )

    sc_code, sc_body = http_json("GET", "/api/faculty/scores", headers=f_headers)
    if sc_code == 200 and isinstance(sc_body, dict):
        body = sc_body.get("scores") or {}
        kra_iv = (body.get("verified") or {}).get("byKra", {}).get("kra-IV", {})
        print("scores kra-IV raw", kra_iv.get("rawTotal"), "weighted", kra_iv.get("weightedContribution"))

    print("SUMMARY_JSON", json.dumps({"achievementId": ach_id, "documentId": doc_id, "title": TEST_TITLE}))
    return 0 if rev_code == 200 else 1


if __name__ == "__main__":
    raise SystemExit(main())
