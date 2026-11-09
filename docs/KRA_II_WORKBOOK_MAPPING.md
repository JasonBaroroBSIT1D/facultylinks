# KRA II — Workbook mapping (source sheet: `KRA II - Research & Innovation`)

Source file: `BONGCAWEL - JC3 Self Assessment.docx.xlsx` (FacultyLink does not store personal SCORE column values).

## KRA envelope

| Field | Workbook | Config |
|-------|----------|--------|
| KRA title | A5 | `kra-II` |
| KRA maximum | B5 = **100** | `maxPoints: 100` |
| Weight | Project JC3 (KRA II = **20%**) | `KRA_WEIGHTS['kra-II']` = 0.2 |
| Weighted contribution | Raw sum (capped at 100) × weight **once** | `scoring_engine.compute_faculty_scores` |

## Criterion A — Research Outputs Published (rows 6–12)

| ID | Workbook rows | Rate (B col) | Criterion cap | Calculation |
|----|---------------|--------------|-----------------|-------------|
| `kra-II-A-1` | A7 | 100 | 100 | `fixed_per_entry` |
| `kra-II-A-2` | A8 | 35 | 100 | `fixed_per_entry` |
| `kra-II-A-3` | A9 | 50 | 100 | `fixed_per_entry` |
| `kra-II-A-4` | A10 | 100 | 100 | `fixed_per_entry` |
| `kra-II-A-5` | A11 | 35 per activity, **Max = 70** | 100 | `fixed_per_entry` + **indicator aggregate cap 70** |
| `kra-II-A-6` | A12 | 10 per citation, **Max = 60** | 100 | `fixed_per_entry` + **indicator aggregate cap 60** |

**Unresolved (not auto-scored):** Section 18–21 eligibility conditions in guideline text (sole authorship, translation tiers, citation qualification). Drafts/evidence allowed; reviewers confirm entitlement.

## Criterion B — Inventions (rows 13–20)

| ID | Workbook rows | Rate | Caps | Calculation notes |
|----|---------------|------|------|-------------------|
| `kra-II-B-1-1` | A15–B17 | A=10, P=20, G=80 | per achievement | **`patent_stage` — one stage per claim; stages do not accumulate** |
| `kra-II-B-1-2` | A18 | Local 5, Intl 10 | **Local max 20, Intl max 30** | `tiered_option` field `commercializationScope` |
| `kra-II-B-2-1` | A19 | New 10, Updated 4 | per achievement | `tiered_option` field `softwareVersionType` |
| `kra-II-B-2-2` | A20 | 10 | per achievement | `fixed_per_entry` |

**Unresolved:** Section 23–24 conditions (patent ownership, utilization proof) — reviewer validation only.

## Criterion C — Creative Works (rows 21–39)

| ID | Row | Points (B) | Notes |
|----|-----|------------|-------|
| `kra-II-C-1-1-1` … `kra-II-C-1-1-5` | 22–26 | 20/20/10/10/20 | Music |
| `kra-II-C-1-2-1`, `kra-II-C-1-2-2` | 27–28 | 20, 10 | Dance |
| `kra-II-C-1-3-1` … `kra-II-C-1-3-4` | 29–32 | 20 each | Theatre |
| `kra-II-C-1-2-visual` | 33 | 20 | Visual arts group |
| `kra-II-C-1-2-design` | **34** | **blank** | **`pending` — unresolved workbook rate** |
| `kra-II-C-1-3-film` | 35 | 20 | Film categories grouped |
| `kra-II-C-1-4-1` … `kra-II-C-1-4-4` | 36–39 | 20/10/2/2 | Literary |

Criterion C cap: **100** (B21).

## Publish / activate (no auto-publish)

1. Admin → Evaluation settings → Rules: import or reconcile draft catalog (includes `kra-ii-catalog.js` merged in `assessment-definitions.js`).
2. Review unresolved rows (`kra-II-C-1-2-design`, guideline-only indicators) in draft UI.
3. **Publish** catalog when ready; faculty assessments pin to published version per existing pin logic.
4. Faculty Flutter loads published catalog via API (`catalogKras`); reviewer portal uses same published blob.

## Tests

- `backend/tests/test_kra_ii_achievements.py` — rules, caps, patent stage, tiered commercialization, scoring.
- `admin_reviewer_web/tests/workspace-achievements-cache.test.mjs` — unchanged KRA I behavior.
- `flutter analyze` — faculty achievement screen KRA II fields.
