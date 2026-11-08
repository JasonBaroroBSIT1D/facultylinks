/// Mirrors admin_reviewer_web/js/core/assessment-definitions.js (stable IDs).
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
  const IndicatorNode({
    required this.id,
    required this.name,
    this.type,
    this.subType,
    this.maxPoints,
  });
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
          IndicatorNode(id: 'kra-I-A-set', name: 'SET', type: 'set_sef', subType: 'SET', maxPoints: 36),
          IndicatorNode(id: 'kra-I-A-sef', name: 'SEF', type: 'set_sef', subType: 'SEF', maxPoints: 24),
          IndicatorNode(id: 'kra-I-A-special', name: 'Special Status Provisions', maxPoints: null),
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
