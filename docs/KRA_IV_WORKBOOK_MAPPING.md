# KRA IV — Workbook mapping (sheet: `KRA IV - Professional Dev't`, rows 5–17)

Source: `BONGCAWEL - JC3 Self Assessment.docx(9).xlsx` / FacultyLink dump `_workbook_dump.txt`.  
**Import columns A/B only.** Do not import column F sample scores, column G personal evidence notes, or F/G comments.

## KRA envelope

| Field | Workbook (rows) | FacultyLink config |
|-------|-----------------|-------------------|
| Title | A5 | `kra-IV` |
| KRA maximum | B5 **100** | `maxPoints: 100` |
| Weight | JC3 KRA IV **10%** once | `KRA_WEIGHTS['kra-IV']` = 0.1 |
| Example formula | F5 `=SUM(F6+F8+F13+F15)*10%` | Scoring uses `coreSubtotal` + `additionalSubtotal` |

### Envelope policy (**unresolved**)

| Component | Workbook cap (B col) | Sum |
|-----------|----------------------|-----|
| Criterion A | 20 | |
| Criterion B | 60 | |
| Criterion C | 20 | **100** (A+B+C) |
| Criterion D (additional) | 20 | |

B5 states max **100** while F5 sums **A+B+C+D** (up to **120** raw) before ×10%. FacultyLink exposes:

- `coreSubtotal` (A+B+C, capped per criterion)
- `additionalSubtotal` (D, cap 20)
- `rawTotalBeforeKraCap`
- `kraCapPolicyUnresolved: true` when raw > 100 until admin publishes `applyKraEnvelopeCap` / clarified policy in catalog `scoringPolicy`.

**Do not** present weighted rank outcomes as authoritative while envelope policy is unresolved.

## Criterion A — Involvement in Professional Organizations (rows 6–7)

| ID | Rows | Rate | Crit cap | Section | Calculation |
|----|------|------|----------|---------|-------------|
| `kra-IV-A-1` | A7, B7 | **5** per qualifying membership/participation | **20** | Sec. 38 | `fixed_per_entry` |

Section 38 eligibility is **not** automated — reviewer confirms registered organization / conditions.

## Criterion B — Continuing Development (rows 8–12)

Criterion cap **60** (B8).

### B-1 Educational qualifications (A9, B9)

| Tier key | Workbook text | Points |
|----------|---------------|--------|
| `post_master_diploma` | Post-master diploma/certificate | 10 |
| `post_doctorate_diploma` | Post-doctorate diploma/certificate | 10 |
| `additional_masters` | Additional master’s degree | 20 |
| `doctorate` | Doctorate or additional doctorate | 40 |

| ID | Calculation | Field |
|----|-------------|-------|
| `kra-IV-B-1` | `tiered_option` (`qualificationType`) | Sec. 40 conditions → `eligibilityUnresolved` on indicator |

### B-2 Conference / seminar / workshop / industry immersion (A10, B10)

| Scope | Points | Aggregate |
|-------|--------|-----------|
| Local | 1 | **Max 10 combined** local + international |
| International | 2 | |

| ID | Rows | Calculation |
|----|------|-------------|
| `kra-IV-B-2` | A10, B10 | `tiered_option` (`attendanceScope`) + `aggregateCap: 10` |

Section 41 — reviewer confirms conditions; not encoded as automatic rules.

### B-3 Paper presentations (A11–A12, B11–B12)

| ID | Scope | Points | Aggregate |
|----|-------|--------|-----------|
| `kra-IV-B-3-1` | Local | 3 | **Max 10 combined** with international |
| `kra-IV-B-3-2` | International | 5 | |

Shared `aggregateGroup: kra-IV-B-presentations`, `aggregateCap: 10`.  
Section 42 — reviewer confirms conditions.

## Criterion C — Awards and Recognition (rows 13–14)

| Level key | Workbook (B14) | Points |
|-----------|----------------|--------|
| `institutional` | 1.1 Institutional | 2 |
| `local_regional` | 1.2 Local and Regional | 3 |
| `national` | 1.3 National | 4 |

**No international tier** in workbook.

| ID | Cap | Calculation |
|----|-----|-------------|
| `kra-IV-C-1` | Crit **20** | `tiered_option` (`awardLevel`) · Sec. 43 |

## Criterion D — Additional Points for Newly Appointed Faculty (rows 15–17)

Criterion cap **20** combined academic + industry (B15).

**Eligibility:** Workbook marks “*Newly Appointed Faculty”. FacultyLink requires explicit `newlyAppointedEligible: true` on each D achievement; otherwise rule stays **unresolved** (no automatic points).

### D-1 Full-time academic service (A16, B16)

Per **full year** rates (`yearly_rate`, field `serviceYears`, role `academicServiceRole`):

| Role key | Points/year |
|----------|-------------|
| `president` | 5 |
| `vp_dean_director` | 4 |
| `dept_program_head` | 3 |
| `faculty_member` | 2 |

| ID | Source |
|----|--------|
| `kra-IV-D-1` | A16, B16, Sec. 44 |

### D-2 Industry experience (A17, B17)

| Category key | Points/year |
|--------------|-------------|
| `managerial_supervisory` | 4 |
| `technical_skilled` | 3 |
| `support_admin` | 2 |

| ID | Source |
|----|--------|
| `kra-IV-D-2` | A17, Sec. 44 |

### Fractional years (**unresolved**)

F16 cell **comment** (not column B): proportionate points for fractional years.  
Catalog: `fractionalYearPolicy: 'unresolved'`. Only **whole** `serviceYears` (>0 integer) score until admin publishes policy (`proportionate_months`, etc.).

**Not modeled:** overlapping simultaneous roles, multiple concurrent positions (F17 comment) — require reviewer judgment / future policy.

## Stable IDs summary

```
kra-IV-A-1
kra-IV-B-1, kra-IV-B-2, kra-IV-B-3-1, kra-IV-B-3-2
kra-IV-C-1
kra-IV-D-1, kra-IV-D-2
```

## Admin configuration

Publish via existing catalog draft/reconcile/publish — **no** auto-repin faculty assessments.  
Editable: rates, caps, `aggregateGroup`, `scoringPolicy.applyKraEnvelopeCap`, `fractionalYearPolicy`, Section 38–44 eligibility notes.
