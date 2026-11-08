# FacultyLink — Implementation Checklist

**Sources:** `CHAPTER 1-3.docx` (Downloads), `BONGCAWEL - JC3 Self Assessment.docx.xlsx` (Downloads)  
**Authority:** DBM–CHED Joint Circular No. 3, s. 2022 (Enhanced Implementing Guidelines, NBC 461, 9th cycle)

## From manuscript
- [x] Preparatory self-assessment; not official committee decision
- [x] Web (Admin + Reviewer) + Flutter (Faculty); Flask/PostgreSQL/Tesseract deferred
- [x] Mock repositories + future API interfaces
- [x] Demo authentication (documented, non-production)
- [x] OCR simulated in review flows
- [x] Rule-based scoring where workbook supports it

## From workbook → UI
- [x] KRA I–IV hierarchy with stable IDs
- [x] SET/SEF: 3 AYs × 2 semesters; formulas `avg(6 ratings)` × 36% / × 24%
- [x] Teaching Effectiveness = SET points + SEF points (Criterion A)
- [x] KRA weighted totals: I×60%, II×20%, III×10%, IV×10% (per sheet F5 formulas)
- [x] Instructional materials caps, research advising matrix, extension nested points
- [ ] Rank mapping — **Pending configuration** (not in workbook)

## Deliverables
- [x] `admin_reviewer_web/` runnable static SPA
- [x] `faculty_mobile/` Flutter project
- [x] `docs/` accounts, navigation map, source mapping, unresolved issues, backend guide

## Verification (frontend)
- Landing scroll + responsive
- Login role routing
- Admin CRUD + assessment config publish draft
- Reviewer document approve/reject/correct + score updates
- Flutter assessment SET/SEF, documents, simulation notice
