# Rank simulation (JC3 Tables 2.2 & 3.1)

## Weighting (Table 2.2)

Promotion **overall weighted score** uses the faculty member’s **current rank category** only:

`overallWeighted = Σ (KRA rawTotal × rank weight)` for kra-I … kra-IV.

- KRA raw totals come from the scoring engine (criterion caps and envelope rules applied **before** weighting).
- Catalog `kraWeights` (workbook F5 JC3 multipliers) are **not** used for rank simulation.
- Weights are applied **once** — never multiply an already-weighted total.

## Sub-rank increments (Table 3.1)

| Overall weighted score | Sub-ranks |
|------------------------|-----------|
| 41–50 | 1 |
| 51–60 | 2 |
| 61–70 | 3 |
| 71–80 | 4 |
| 81–90 | 5 |
| 91–100 | 6 |

Scores **below 41**: increment 0; table does not define advancement.

**Decimal scores** (e.g. 78.02): default `decimalBracketPolicy: unresolved` — show provisional bracket context only until admin publishes a rule (`floor_to_bracket`, `round_half_up`, etc.).

## Potential rank

Advance along `institutionConfig.rankOptions` by resolved sub-rank count from **current** rank. Category crossings and College/University Professor appointment require eligibility verification (not points alone).

## API

`GET /api/faculty/scores` includes `rankSimulation` with `estimated` and `verified` buckets.

## Admin

Evaluation Settings → **Rank simulation** tab: edit weight matrix, brackets, decimal policy. Validated on save (`PUT /api/config/institution`). Does not republish assessment catalog or faculty pins.
