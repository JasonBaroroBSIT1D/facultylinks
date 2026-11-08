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

## Status (computed, never stored)

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
