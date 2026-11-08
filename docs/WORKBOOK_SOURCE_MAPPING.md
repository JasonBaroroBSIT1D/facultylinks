# Workbook → Interface Mapping

Workbook: `BONGCAWEL - JC3 Self Assessment.docx.xlsx`

| Worksheet | UI surface |
|-----------|------------|
| Luthie KRA Score | Admin reports · Flutter rank simulation (weighted totals) |
| KRA I - Instruction | Assessment tree; SET/SEF grids; Criterion B/C indicators |
| KRA II - Research & Innovation | Indicators kra-II-A-* … kra-II-C-* |
| KRA III - Extension Services | Criteria A–D; pending external ref on Criterion C |
| KRA IV - Professional Dev't | Criteria A–D including newly appointed points |

## Key formulas implemented

| Cell / logic | Implementation |
|--------------|----------------|
| `J11 = SUM(J9:O9)/6*36%` | `computeSetSefPoints(..., 'SET')` |
| `J12 = SUM(J10:O10)/6*24%` | `computeSetSefPoints(..., 'SEF')` |
| `F6 = SUM(F7:F13)` | Teaching Effectiveness subtotal (SET+SEF, cap 60) |
| `F5 = SUM(F6+F14+F21)*60%` | KRA I weighted via `KRA_WEIGHTS` in `scoring.js` / Dart `scoring.dart` |
| KRA II/III/IV `F5` | 20% / 10% / 10% multipliers on criterion sums |
| `G12 = SUM(G8:G11)` | `overallWeighted` across KRAs |

Stable IDs follow `js/core/assessment-definitions.js` and `lib/data/assessment_catalog.dart`.
