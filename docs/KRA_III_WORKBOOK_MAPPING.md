# KRA III — Workbook mapping (sheet: `KRA III - Extension Services`, rows 5–23)

Source: `BONGCAWEL - JC3 Self Assessment.docx.xlsx` (FacultyLink does not import column F/G sample scores or personal activity notes).

## KRA envelope

| Field | Workbook | Config |
|-------|----------|--------|
| KRA title | A5 | `kra-III` |
| KRA maximum (B5) | **100** | `maxPoints: 100` |
| Weight | JC3 (KRA III = **10%**) | `KRA_WEIGHTS['kra-III']` = 0.1 |
| Score line (definitions) | SUM(A+B+C+D) × 10% | see **Bonus / envelope policy** below |

### Bonus / envelope policy (unresolved in workbook rows 5–23)

| Component | Criterion caps (B col) | Sum of core caps |
|-----------|-------------------------|------------------|
| A | 30 | |
| B | 50 | |
| C | 20 | **100** |
| D (bonus) | 20 | |

B5 lists KRA max **100** while D allows **20** bonus points. FacultyLink exposes **coreSubtotal**, **bonusSubtotal**, and **rawTotalBeforeKraCap** on KRA III scoring summaries. **`applyKraEnvelopeCap: false`** until implementing guidelines confirm whether bonus stacks above the 100-point envelope or replaces part of it. Weight is applied **once** to the credited raw total shown in simulation.

## Criterion A — Service to the Institution (rows 6–8)

| ID | Rows | Rate | Cap | Calculation |
|----|------|------|-----|-------------|
| `kra-III-A-1` | A7, B7 | 5 per activity | Crit A **30** | `fixed_per_entry` |
| `kra-III-A-2` | A8, B8 | Lead **2,4,6,12,18**; Contributor **1,2,3,6,9** by amount band | Crit A **30** | `income_tier` |

### Income tier bands (Section 31) — **tier 3 unresolved**

Workbook text includes **“500,000 to 6,000,0000”** (typo/extra zero) and overlapping boundary wording. Config tier `t3` is **`resolved: false`** until an admin confirms bounds in the published catalog. Amount auto-matching skips the ambiguous band; selecting tier `t3` blocks automatic points until confirmed.

| Tier | Workbook label | Lead | Contributor | Auto-match |
|------|----------------|------|-------------|------------|
| t1 | 100,000 and below | 2 | 1 | ≤ 100,000 |
| t2 | 100,001 to 500,000 | 4 | 2 | 100,001–500,000 |
| t3 | 500,000 to 6,000,0000 | 6 | 3 | **Unresolved — not auto-matched** |
| t4 | 6,000,001 to 12,000,000 | 12 | 6 | 6,000,001–12,000,000 |
| t5 | Above 12,000,000 | 18 | 9 | > 12,000,000 |

## Criterion B — Service to the Community (rows 9–19)

Criterion cap **50**. **ISR subgroup** (rows 18–19): indicator `kra-III-B-2-1` **aggregateCap 30** (independent of criterion cap).

| ID | Rows | Rate | Unit / cap | Calculation |
|----|------|------|------------|-------------|
| `kra-III-B-1-1` | A10 | Local **8**, Intl **10** | per service | `tiered_option` (`serviceScope`) |
| `kra-III-B-1-2` | A11 | Research awards **2**, Academic competitions **1** | per service | `tiered_option` (`judgeServiceType`) |
| `kra-III-B-1-3` | A12 | Local **8**, Intl **10** | short-term consultant | `tiered_option` (`serviceScope`) |
| `kra-III-B-1-4-1` | A13 | **2** | **aggregate max 10** | `fixed_per_entry` + `aggregateCap: 10` |
| `kra-III-B-1-4-2` | A14 | **10** | regular column | `fixed_per_entry` |
| `kra-III-B-1-4-3` | A15 | **10** | host | `fixed_per_entry` |
| `kra-III-B-1-4-4` | A16 | **1** | **aggregate max 10** | `fixed_per_entry` + `aggregateCap: 10` |
| `kra-III-B-1-5` | A17 | Local **2**/hr, Intl **3**/hr | hours | `hourly_tier` (`serviceScope`, `hours`) |
| `kra-III-B-2-1` | A18–B19 | Lead **5**, Participant **2** | **ISR max 30** | `tiered_option` (`extensionRole`) + `aggregateCap: 30` |

Eligibility (Sections 33–34) is **not** automated; reviewers confirm conditions.

## Criterion C — Relevance and Quality (rows 20–21)

| ID | Rows | Workbook | Status |
|----|------|----------|--------|
| `kra-III-C-1` | A21, B21, F21 | Max **20**; F21 refs `[1]Luthie!$P$21` | **`pending` + `requiresLinkedAchievement`** |

- **No** satisfaction-to-points conversion (do not use cached F21 sample).
- **Dependency:** extension project must be declared under **`kra-III-B-2-1`** via stable achievement id field **`linkedIsrProjectId`** (not title match).
- Draft/evidence allowed; points remain **unresolved** until rule is published and reviewer verifies.

## Criterion D — Bonus (rows 22–23)

| ID | Rows | Cap | Calculation |
|----|------|-----|-------------|
| `kra-III-D-1` | A23, B23 | **20** | `designation_matrix` |

### Designation points (B23 column, read in order)

**Institutional level (`designationLevel: institutional`)**

| Role key | Workbook | Pts |
|----------|----------|-----|
| `president` | 1.1.1 President or OIC President | 20 |
| `vice_president` | 1.1.2 Vice-President | 15 |
| `chancellor` | 1.1.3 Chancellor | 10 |
| `vice_chancellor` | 1.1.4 Vice-Chancellor | 8 |
| `campus_director` | 1.1.5 Campus Director/Administrator | 8 |
| `faculty_trustee` | 1.1.6 Faculty Trustee/Regent | 8 |
| `office_director` | 1.1.7 Office Director | 6 |
| `university_secretary` | 1.1.8 University/College Secretary | 6 |
| `project_head` | 1.1.9 Project Head | 4 |
| `inst_committee_chair` | 1.1.10 Chair | 3 |
| `inst_committee_member` | 1.1.10 Member | 2 |
| `inst_coordinator` | 1.1.11 Coordinators | 2 |

**College/department level (`designationLevel: college_department`)**

| Role key | Pts |
|----------|-----|
| `dean` | 6 |
| `associate_dean` | 5 |
| `college_secretary` | 3 |
| `department_head` | 4 |
| `program_chair` | 3 |
| `dept_committee_chair` | 2 |
| `dept_committee_member` | 1 |
| `dept_coordinator` | 1 |

**Unresolved (G23):** “CCIR Coordinator 1 or 2 points???” — not mapped to a distinct role; use `inst_coordinator` only after admin confirmation.

## Legacy published catalogs (`structured_points`)

Older published blobs may store Criterion B as `calculation.kind: structured_points` with `points` objects and camelCase judge keys. The API rule engine **normalizes at preview/submit/scoring time** to `tiered_option` / `hourly_tier` with `serviceScope`, `judgeServiceType`, `extensionRole`, and `hours`. Admin **Publish** after merging `kra-iii-catalog.js` persists the explicit kinds so the catalog JSON matches runtime behavior without relying on normalization.

## Publish / activate

1. Admin → Scoring Rules: merge workbook reference (`kra-iii-catalog.js` in `assessment-definitions.js`).
2. Resolve income tier `t3` and Criterion C conversion in draft when source is confirmed.
3. **Publish**; faculty pins unchanged until explicit version reassignment.

## Tests

- `backend/tests/test_kra_iii_achievements.py`
