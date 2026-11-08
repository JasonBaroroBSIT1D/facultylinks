# Assessment configuration schema (web ↔ future API ↔ Flutter)

Versioned configuration is stored in `MockStore.assessmentConfig` (web) and should map to API `GET /api/config/assessment-versions`.

## Version object

| Field | Type | Notes |
|-------|------|-------|
| `id` | string | Stable version id |
| `label` | string | Human label |
| `status` | `draft` \| `published` \| `archived` | |
| `effectiveDate` | ISO date | Required on publish |
| `catalog` | AssessmentCatalog | Hierarchy below |
| `kraWeights` | Record&lt;kraId, number&gt; | Must sum to 1.0 |
| `changeHistory` | array | `{ at, actor, summary }` |

## Indicator (editable)

| Field | Type |
|-------|------|
| `id` | string (stable, shared with Flutter `assessment_catalog.dart`) |
| `name`, `description` | string |
| `maxPoints` | number? |
| `sourceRef` | string |
| `conditions` | string[] |
| `documentaryRequirements` | string[] |
| `calculation` | structured (see kinds) |
| `contributionAllocation` | `{ mode, defaultPercent, leadPoints?, contributorPoints? }` |

### `calculation.kind` (no free-form formulas)

- `fixed_per_entry`
- `set_sef_average` (+ `factor`, `subType`)
- `role_matrix` (+ `matrix`)
- `structured_points` (+ `points` object)
- `pending`

## Faculty assessment pinning

`assessments[facultyId].configVersionId` — set when assessment starts; **not** updated on publish (no silent historical recalculation).

## Flutter

Mobile retains static `assessment_catalog.dart` for offline demo. Fields align with this schema for future `GET /api/config/active` — **not** auto-synced with web `localStorage` in this phase.
