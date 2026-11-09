/// Mirrors admin_reviewer_web/js/core/assessment-definitions.js (stable IDs).

const criterionASetSefEvalIndicatorId = 'kra-I-A-setsef-eval';
const criterionASpecialIndicatorId = 'kra-I-A-special';

final setSefDocumentIntakeIds = {
  criterionASetSefEvalIndicatorId,
  'kra-I-A-setsef-combined',
  'kra-I-A-set-pdf',
  'kra-I-A-sef-pdf',
};

bool isAchievementCriterion(String kraId, String criterionId) {
  if (kraId == 'kra-I') {
    return criterionId == 'kra-I-B' || criterionId == 'kra-I-C';
  }
  if (kraId == 'kra-II') {
    return criterionId == 'kra-II-A' || criterionId == 'kra-II-B' || criterionId == 'kra-II-C';
  }
  if (kraId == 'kra-III') {
    return criterionId == 'kra-III-A' ||
        criterionId == 'kra-III-B' ||
        criterionId == 'kra-III-C' ||
        criterionId == 'kra-III-D';
  }
  if (kraId == 'kra-IV') {
    return criterionId == 'kra-IV-A' ||
        criterionId == 'kra-IV-B' ||
        criterionId == 'kra-IV-C' ||
        criterionId == 'kra-IV-D';
  }
  return false;
}

/// Parent KRA id for uploads and API (`kra-I`, not criterion `kra-I-B`).
/// More specific prefixes first — `kra-III-*` must not match `kra-I`.
String kraIdFromCriterion(String criterionId) {
  if (criterionId.startsWith('kra-III')) return 'kra-III';
  if (criterionId.startsWith('kra-II')) return 'kra-II';
  if (criterionId.startsWith('kra-IV')) return 'kra-IV';
  if (criterionId.startsWith('kra-I')) return 'kra-I';
  return 'kra-I';
}

String kraIdFromIndicator(String indicatorId, {String? criterionId}) {
  if (criterionId != null && criterionId.isNotEmpty) {
    return kraIdFromCriterion(criterionId);
  }
  if (indicatorId.startsWith('kra-III')) return 'kra-III';
  if (indicatorId.startsWith('kra-II')) return 'kra-II';
  if (indicatorId.startsWith('kra-IV')) return 'kra-IV';
  if (indicatorId.startsWith('kra-I')) return 'kra-I';
  return 'kra-I';
}

/// Resolve parent KRA from published catalog when [kras] is available.
String? kraIdFromPublishedCatalog(List<KraNode> kras, String indicatorId) {
  for (final kra in kras) {
    for (final crit in kra.criteria) {
      for (final ind in crit.indicators) {
        if (ind.id == indicatorId) return kra.id;
      }
    }
  }
  return null;
}

bool isDocumentIntakeIndicator(IndicatorNode ind) {
  if (setSefDocumentIntakeIds.contains(ind.id)) return true;
  final t = ind.type;
  return t == 'set_sef_unified_pdf' ||
      t == 'set_sef_combined_pdf' ||
      t == 'set_sef_set_pdf' ||
      t == 'set_sef_sef_pdf';
}

/// Scoring rows under Criterion A (excludes PDF intake aliases).
List<IndicatorNode> scoringIndicatorsForCriterion(CriterionNode crit) {
  if (crit.id != 'kra-I-A') return crit.indicators;
  return crit.indicators.where((i) => !isDocumentIntakeIndicator(i)).toList();
}

final setSefDocumentIntakeIndicators = <IndicatorNode>[
  IndicatorNode(
    id: criterionASetSefEvalIndicatorId,
    name: 'SET / SEF Evaluation',
    type: 'set_sef_unified_pdf',
    maxPoints: 60,
  ),
  IndicatorNode(
    id: 'kra-I-A-setsef-combined',
    name: 'Combined SET & SEF (PDF)',
    type: 'set_sef_combined_pdf',
    maxPoints: 60,
  ),
  IndicatorNode(
    id: 'kra-I-A-set-pdf',
    name: 'SET only (PDF)',
    type: 'set_sef_set_pdf',
    maxPoints: 36,
  ),
  IndicatorNode(
    id: 'kra-I-A-sef-pdf',
    name: 'SEF only (PDF)',
    type: 'set_sef_sef_pdf',
    maxPoints: 24,
  ),
];

IndicatorNode? indicatorById(List<KraNode> kras, String indicatorId) {
  for (final kra in kras) {
    for (final crit in kra.criteria) {
      for (final ind in crit.indicators) {
        if (ind.id == indicatorId) return ind;
      }
    }
  }
  for (final ind in setSefDocumentIntakeIndicators) {
    if (ind.id == indicatorId) return ind;
  }
  return null;
}
class KraNode {
  final String id;
  final String name;
  final List<CriterionNode> criteria;
  const KraNode({required this.id, required this.name, required this.criteria});

  /// Compact label for dropdowns (full official name remains in [name]).
  String get shortDropdownLabel {
    switch (id) {
      case 'kra-I':
        return 'KRA I · Instruction';
      case 'kra-II':
        return 'KRA II · Research';
      case 'kra-III':
        return 'KRA III · Extension';
      case 'kra-IV':
        return 'KRA IV · Professional Development';
      default:
        return name;
    }
  }
}

class CriterionNode {
  final String id;
  final String name;
  final List<IndicatorNode> indicators;
  const CriterionNode({required this.id, required this.name, required this.indicators});
}

class IndicatorNode {
  final String id;
  final String name;
  final String? type;
  final String? subType;
  final double? maxPoints;
  final Map<String, dynamic>? calculation;
  final Map<String, dynamic>? points;
  const IndicatorNode({
    required this.id,
    required this.name,
    this.type,
    this.subType,
    this.maxPoints,
    this.calculation,
    this.points,
  });
}

List<KraNode> parsePublishedCatalog(Map<String, dynamic> catalog) {
  final krasJson = catalog['kras'] as List<dynamic>? ?? [];
  return krasJson.map((kraRaw) {
    final kra = kraRaw as Map<String, dynamic>;
    final criteria = (kra['criteria'] as List<dynamic>? ?? []).map((critRaw) {
      final crit = critRaw as Map<String, dynamic>;
      final indicators = (crit['indicators'] as List<dynamic>? ?? [])
          .map((indRaw) {
            final ind = indRaw as Map<String, dynamic>;
            return IndicatorNode(
              id: (ind['id'] ?? '').toString(),
              name: (ind['name'] ?? ind['id'] ?? '').toString(),
              type: ind['type'] as String?,
              subType: ind['subType'] as String?,
              maxPoints: (ind['maxPoints'] as num?)?.toDouble(),
              calculation: ind['calculation'] is Map<String, dynamic>
                  ? Map<String, dynamic>.from(ind['calculation'] as Map)
                  : ind['calculation'] is Map
                      ? Map<String, dynamic>.from(ind['calculation'] as Map)
                      : null,
              points: ind['points'] is Map
                  ? Map<String, dynamic>.from(ind['points'] as Map)
                  : null,
            );
          })
          .where((ind) => crit['id'] != 'kra-I-A' || !isDocumentIntakeIndicator(ind))
          .toList();
      return CriterionNode(
        id: (crit['id'] ?? '').toString(),
        name: (crit['name'] ?? crit['id'] ?? '').toString(),
        indicators: indicators,
      );
    }).toList();
    return KraNode(
      id: (kra['id'] ?? '').toString(),
      name: (kra['name'] ?? kra['id'] ?? '').toString(),
      criteria: criteria,
    );
  }).toList();
}

const assessmentKras = <KraNode>[
  KraNode(
    id: 'kra-I',
    name: 'KRA I – Instruction',
    criteria: [
      CriterionNode(
        id: 'kra-I-A',
        name: 'Criterion A – Teaching Effectiveness',
        indicators: [
          IndicatorNode(
            id: 'kra-I-A-set',
            name: 'Student Evaluation of Teachers (SET)',
            type: 'set_sef',
            subType: 'SET',
            maxPoints: 36,
          ),
          IndicatorNode(
            id: 'kra-I-A-sef',
            name: "Supervisor's Evaluation of Faculty (SEF)",
            type: 'set_sef',
            subType: 'SEF',
            maxPoints: 24,
          ),
          IndicatorNode(
            id: criterionASpecialIndicatorId,
            name: 'For Faculty with Special Status',
            maxPoints: null,
          ),
        ],
      ),
      CriterionNode(
        id: 'kra-I-B',
        name: 'Criterion B – Instructional Materials Development',
        indicators: [
          IndicatorNode(id: 'kra-I-B-1-1', name: 'Sole Author Textbook', maxPoints: 30),
          IndicatorNode(id: 'kra-I-B-1-2', name: 'Sole Author Module', maxPoints: 16),
          IndicatorNode(id: 'kra-I-B-1-3', name: 'Instructional Manual', maxPoints: 16),
          IndicatorNode(id: 'kra-I-B-1-4', name: 'Multimedia Materials', maxPoints: 16),
          IndicatorNode(id: 'kra-I-B-2', name: 'Academic Program Lead/Contributor', maxPoints: 10),
        ],
      ),
      CriterionNode(
        id: 'kra-I-C',
        name: 'Criterion C – Research Advising & Mentorship',
        indicators: [
          IndicatorNode(id: 'kra-I-C-1', name: 'Adviser / Panel services', maxPoints: 10),
          IndicatorNode(id: 'kra-I-C-2', name: 'Mentorship', maxPoints: 3),
        ],
      ),
    ],
  ),
  KraNode(
    id: 'kra-II',
    name: 'KRA II – Research, Innovation and/or Creative Work',
    criteria: [
      CriterionNode(
        id: 'kra-II-A',
        name: 'Criterion A – Research Outputs Published',
        indicators: [
          IndicatorNode(id: 'kra-II-A-1', name: 'Academic Book', maxPoints: 100),
          IndicatorNode(id: 'kra-II-A-2', name: 'Book Chapter', maxPoints: 35),
          IndicatorNode(id: 'kra-II-A-3', name: 'Journal Article', maxPoints: 50),
          IndicatorNode(id: 'kra-II-A-4', name: 'Monograph', maxPoints: 100),
          IndicatorNode(id: 'kra-II-A-5', name: 'Translation to policy/product', maxPoints: 35),
          IndicatorNode(id: 'kra-II-A-6', name: 'Publication cited', maxPoints: 10),
        ],
      ),
      CriterionNode(
        id: 'kra-II-B',
        name: 'Criterion B – Inventions',
        indicators: [
          IndicatorNode(id: 'kra-II-B-1-1', name: 'Patent stages', maxPoints: 80),
          IndicatorNode(id: 'kra-II-B-2-1', name: 'Software product', maxPoints: 10),
        ],
      ),
      CriterionNode(
        id: 'kra-II-C',
        name: 'Criterion C – Creative Works',
        indicators: [
          IndicatorNode(id: 'kra-II-C-1-1-1', name: 'Musical composition', maxPoints: 20),
          IndicatorNode(id: 'kra-II-C-1-4-1', name: 'Novel', maxPoints: 20),
          IndicatorNode(id: 'kra-II-C-1-4-3', name: 'Poetry', maxPoints: 2),
        ],
      ),
    ],
  ),
  KraNode(
    id: 'kra-III',
    name: 'KRA III – Extension Services',
    criteria: [
      CriterionNode(
        id: 'kra-III-A',
        name: 'Service to the Institution',
        indicators: [IndicatorNode(id: 'kra-III-A-1', name: 'Linkages', maxPoints: 5)],
      ),
      CriterionNode(
        id: 'kra-III-B',
        name: 'Service to the Community',
        indicators: [IndicatorNode(id: 'kra-III-B-2-1', name: 'Extension project', maxPoints: 5)],
      ),
      CriterionNode(
        id: 'kra-III-C',
        name: 'Relevance & Quality',
        indicators: [IndicatorNode(id: 'kra-III-C-1', name: 'Client satisfaction', maxPoints: 20)],
      ),
      CriterionNode(
        id: 'kra-III-D',
        name: 'Bonus administrative designation',
        indicators: [IndicatorNode(id: 'kra-III-D-1', name: 'Designation points', maxPoints: 20)],
      ),
    ],
  ),
  KraNode(
    id: 'kra-IV',
    name: 'KRA IV – Professional Development',
    criteria: [
      CriterionNode(
        id: 'kra-IV-A',
        name: 'Professional organizations',
        indicators: [IndicatorNode(id: 'kra-IV-A-1', name: 'Membership', maxPoints: 5)],
      ),
      CriterionNode(
        id: 'kra-IV-B',
        name: 'Continuing development',
        indicators: [
          IndicatorNode(id: 'kra-IV-B-2', name: 'Conference attendance', maxPoints: 2),
          IndicatorNode(id: 'kra-IV-B-3-1', name: 'Paper presentation local', maxPoints: 3),
        ],
      ),
      CriterionNode(
        id: 'kra-IV-C',
        name: 'Awards',
        indicators: [IndicatorNode(id: 'kra-IV-C-1', name: 'Award of distinction', maxPoints: 4)],
      ),
      CriterionNode(
        id: 'kra-IV-D',
        name: 'Newly appointed faculty points',
        indicators: [IndicatorNode(id: 'kra-IV-D-1', name: 'Prior academic service', maxPoints: 5)],
      ),
    ],
  ),
];
