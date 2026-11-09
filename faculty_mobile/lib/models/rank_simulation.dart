class BracketConditionalProjection {
  final String policyKey;
  final String? policyLabel;
  final double? classificationScore;
  final String? bracketLabel;
  final int? subRankIncrements;

  BracketConditionalProjection({
    required this.policyKey,
    this.policyLabel,
    this.classificationScore,
    this.bracketLabel,
    this.subRankIncrements,
  });

  factory BracketConditionalProjection.fromJson(Map<String, dynamic> j) => BracketConditionalProjection(
        policyKey: j['policyKey'] as String? ?? '',
        policyLabel: j['policyLabel'] as String?,
        classificationScore: (j['classificationScore'] as num?)?.toDouble(),
        bracketLabel: j['bracketLabel'] as String?,
        subRankIncrements: (j['subRankIncrements'] as num?)?.toInt(),
      );
}

class ConditionalRankProjection {
  final String? policyKey;
  final String? policyLabel;
  final String? bracketLabel;
  final int? subRankIncrements;
  final PotentialRankResult? potentialRank;

  ConditionalRankProjection({
    this.policyKey,
    this.policyLabel,
    this.bracketLabel,
    this.subRankIncrements,
    this.potentialRank,
  });

  factory ConditionalRankProjection.fromJson(Map<String, dynamic> j) => ConditionalRankProjection(
        policyKey: j['policyKey'] as String?,
        policyLabel: j['policyLabel'] as String?,
        bracketLabel: j['bracketLabel'] as String?,
        subRankIncrements: (j['subRankIncrements'] as num?)?.toInt(),
        potentialRank: j['potentialRank'] != null
            ? PotentialRankResult.fromJson(j['potentialRank'] as Map<String, dynamic>)
            : null,
      );
}

class RankSimulationBucket {
  final bool configured;
  final String scoreSource;
  final String? basisLabel;
  final String? currentRank;
  final String? rankCategoryId;
  final String? rankCategoryLabel;
  final double overallWeightedScore;
  final bool scoringAuthoritative;
  final List<String> notes;
  final List<RankSimulationKraLine> kras;
  final SubRankBracket? bracket;
  final PotentialRankResult? potentialRank;
  final List<ConditionalRankProjection> conditionalRankProjections;

  RankSimulationBucket({
    required this.configured,
    required this.scoreSource,
    this.basisLabel,
    this.currentRank,
    this.rankCategoryId,
    this.rankCategoryLabel,
    this.overallWeightedScore = 0,
    this.scoringAuthoritative = true,
    this.notes = const [],
    this.kras = const [],
    this.bracket,
    this.potentialRank,
    this.conditionalRankProjections = const [],
  });

  factory RankSimulationBucket.fromJson(Map<String, dynamic>? j) {
    if (j == null || j['configured'] == false) {
      return RankSimulationBucket(
        configured: false,
        scoreSource: (j?['scoreSource'] as String?) ?? 'estimated',
        currentRank: j?['currentRank'] as String?,
      );
    }
    final cat = j['rankCategory'] as Map<String, dynamic>?;
    final kras = (j['kras'] as List<dynamic>? ?? [])
        .map((e) => RankSimulationKraLine.fromJson(e as Map<String, dynamic>))
        .toList();
    return RankSimulationBucket(
      configured: true,
      scoreSource: (j['scoreSource'] as String?) ?? 'estimated',
      basisLabel: j['basisLabel'] as String?,
      currentRank: j['currentRank'] as String?,
      rankCategoryId: cat?['id'] as String?,
      rankCategoryLabel: cat?['label'] as String?,
      overallWeightedScore: (j['overallWeightedScore'] as num?)?.toDouble() ?? 0,
      scoringAuthoritative: j['scoringAuthoritative'] != false,
      notes: (j['notes'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? const [],
      kras: kras,
      bracket: j['subRankBracket'] != null
          ? SubRankBracket.fromJson(j['subRankBracket'] as Map<String, dynamic>)
          : null,
      potentialRank: j['potentialRank'] != null
          ? PotentialRankResult.fromJson(j['potentialRank'] as Map<String, dynamic>)
          : null,
      conditionalRankProjections: (j['conditionalRankProjections'] as List<dynamic>? ?? [])
          .map((e) => ConditionalRankProjection.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}

class RankSimulationKraLine {
  final String kraId;
  final double rawTotal;
  final double weight;
  final double weightedContribution;

  RankSimulationKraLine({
    required this.kraId,
    required this.rawTotal,
    required this.weight,
    required this.weightedContribution,
  });

  factory RankSimulationKraLine.fromJson(Map<String, dynamic> j) => RankSimulationKraLine(
        kraId: j['kraId'] as String? ?? '',
        rawTotal: (j['rawTotal'] as num?)?.toDouble() ?? 0,
        weight: (j['weight'] as num?)?.toDouble() ?? 0,
        weightedContribution: (j['weightedContribution'] as num?)?.toDouble() ?? 0,
      );
}

class SubRankBracket {
  final String status;
  final int? subRankIncrements;
  final int? provisionalIncrements;
  final String? label;
  final String? unresolvedReason;
  final List<BracketConditionalProjection> conditionalProjections;

  SubRankBracket({
    required this.status,
    this.subRankIncrements,
    this.provisionalIncrements,
    this.label,
    this.unresolvedReason,
    this.conditionalProjections = const [],
  });

  factory SubRankBracket.fromJson(Map<String, dynamic> j) => SubRankBracket(
        status: j['status'] as String? ?? 'unresolved',
        subRankIncrements: (j['subRankIncrements'] as num?)?.toInt(),
        provisionalIncrements: (j['provisionalIncrements'] as num?)?.toInt(),
        label: j['label'] as String?,
        unresolvedReason: j['unresolvedReason'] as String?,
        conditionalProjections: (j['conditionalProjections'] as List<dynamic>? ?? [])
            .map((e) => BracketConditionalProjection.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}

class PotentialRankResult {
  final String status;
  final String? currentRank;
  final int? increments;
  final String? potentialRank;
  final String? movement;
  final String? displayLabel;
  final List<String> notes;

  PotentialRankResult({
    required this.status,
    this.currentRank,
    this.increments,
    this.potentialRank,
    this.movement,
    this.displayLabel,
    this.notes = const [],
  });

  factory PotentialRankResult.fromJson(Map<String, dynamic> j) => PotentialRankResult(
        status: j['status'] as String? ?? 'unresolved',
        currentRank: j['currentRank'] as String?,
        increments: (j['increments'] as num?)?.toInt(),
        potentialRank: j['potentialRank'] as String?,
        movement: j['movement'] as String?,
        displayLabel: j['displayLabel'] as String?,
        notes: (j['notes'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? const [],
      );
}

class FacultyRankSimulation {
  final bool profileComplete;
  final RankSimulationBucket estimated;
  final RankSimulationBucket verified;

  FacultyRankSimulation({
    required this.profileComplete,
    required this.estimated,
    required this.verified,
  });

  factory FacultyRankSimulation.fromJson(Map<String, dynamic>? j) {
    if (j == null) {
      return FacultyRankSimulation(
        profileComplete: false,
        estimated: RankSimulationBucket(configured: false, scoreSource: 'estimated'),
        verified: RankSimulationBucket(configured: false, scoreSource: 'verified'),
      );
    }
    return FacultyRankSimulation(
      profileComplete: j['profileComplete'] == true,
      estimated: RankSimulationBucket.fromJson(j['estimated'] as Map<String, dynamic>?),
      verified: RankSimulationBucket.fromJson(j['verified'] as Map<String, dynamic>?),
    );
  }
}
