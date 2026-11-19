# Evaluation Period (shared contract)

Institution-wide evaluation window: when faculty prepare evidence and when reviewers may begin checking documents.

## Storage (demo phase)

| Client | Location | Sync |
|--------|----------|------|
| Admin / Reviewer web | `localStorage` → `facultylink_demo_state_v1` → `institutionConfig.preparationPeriod` | Same **origin** only: `storage` events + `fl-state-changed` refresh open tabs |
| Faculty Flutter | `SharedPreferences` → `facultylink_institution_config_v1` → `preparationPeriod` | **Not** synced with web until API integration |

JSON field name `preparationPeriod` is retained for backward-compatible demo data; the product label is **Evaluation Period**.

## Field schema

| Field | Type | Required | Label |
|-------|------|----------|-------|
| `start` | ISO date (`YYYY-MM-DD`) | yes | Start Date |
| `end` | ISO date | yes | End Date |
| `reviewerAvailableFrom` | ISO date | no | Reviewer Available From |

## Reviewer review-action window

Calendar dates in **Asia/Manila**. **Evaluation ends** is the **last allowed day** (inclusive through 23:59:59 Manila).

| Rule | Detail |
|------|--------|
| First allowed day | `max(start, reviewerAvailableFrom)` when reviewer start is set; otherwise `start` |
| Last allowed day | `end` (inclusive) |
| After end | Closed — message: **Review period has ended** |
| Before first day | **Review opens {date}.** |

Reviewers may open workspace, history, and PDFs outside the window, but **cannot** approve/reject, request changes, or edit verified scores/remarks (UI + API). **Admins** are not restricted. **Faculty** uploads and self-assessment are unchanged outside the period.

Portal bootstrap includes `reviewWindow` from the API; clients may also compute via `computeReviewerReviewWindow()`.

## Evaluation period status (faculty-facing display)

Compare **calendar dates** (ignore time of day):

| Status | Rule |
|--------|------|
| `Upcoming` | today &lt; start |
| `Open` | start ≤ today ≤ end |
| `Closed` | today &gt; end |

Implementations:

- Web: `admin_reviewer_web/js/core/evaluation-period-service.js`
- Dart: `faculty_mobile/lib/core/evaluation_period_service.dart`

## Validation

- `end` must not be before `start` (date-only comparison).

## Future API (illustrative)

```
GET  /api/institution/evaluation-period
PUT  /api/institution/evaluation-period   # admin only
```

Response body uses the same three fields plus server-computed `status` for convenience. Rank requirement thresholds remain a separate configuration surface (not on the Evaluation Period page).

## Faculty copy

When the period is closed, show (do not block uploads or self-assessment):

> You can still prepare documents and check your estimated points outside this period.
