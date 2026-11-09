import '../core/scoring.dart';
import '../models/institution_config.dart';
import '../models/rank_simulation.dart';
import '../repositories/mock_repository.dart';

class CriterionBreakdownLine {
  final String criterionId;
  final String? name;
  final double rawTotal;
  final double? capMaxPoints;

  CriterionBreakdownLine({
    required this.criterionId,
    this.name,
    required this.rawTotal,
    this.capMaxPoints,
  });
}

class KraBreakdownLine {
  final String kraId;
  final String name;
  final double rawTotal;
  final double? rawCap;
  final double weight;
  final double weightedContribution;
  final bool rawIncomplete;
  final String? incompleteReason;
  final List<CriterionBreakdownLine> criteria;

  KraBreakdownLine({
    required this.kraId,
    required this.name,
    required this.rawTotal,
    this.rawCap,
    required this.weight,
    required this.weightedContribution,
    this.rawIncomplete = false,
    this.incompleteReason,
    this.criteria = const [],
  });
}

class SimulationSnapshot {
  final double weightedTotal;
  final double overallRaw;
  final List<KraBreakdownLine> kras;
  final List<String> missingRequirements;
  final List<String> pendingEvidence;
  final bool scoresFromBackend;
  /// When false, rank simulation must not treat weighted total as authoritative (e.g. KRA IV envelope unresolved).
  final bool scoringAuthoritative;
  final bool usesRankTableWeights;
  final String? rankCategoryLabel;
  final SubRankBracket? subRankBracket;
  final PotentialRankResult? potentialRank;
  final String scoreSourceLabel;
  final String? basisLabel;
  final String? bucketCurrentRank;
  final List<ConditionalRankProjection> conditionalRankProjections;

  SimulationSnapshot({
    required this.weightedTotal,
    required this.overallRaw,
    required this.kras,
    required this.missingRequirements,
    required this.pendingEvidence,
    this.scoresFromBackend = false,
    this.scoringAuthoritative = true,
    this.usesRankTableWeights = false,
    this.rankCategoryLabel,
    this.subRankBracket,
    this.potentialRank,
    this.scoreSourceLabel = 'estimated',
    this.basisLabel,
    this.bucketCurrentRank,
    this.conditionalRankProjections = const [],
  });
}

class RankEvaluation {
  final String potentialRank;
  final double? readinessPercent;
  final String readinessLabel;
  final String simulationStatus;
  final List<String> unmetConditions;

  RankEvaluation({
    required this.potentialRank,
    this.readinessPercent,
    required this.readinessLabel,
    required this.simulationStatus,
    required this.unmetConditions,
  });
}

class WhatIfScenario {
  final Map<String, double> extraWeightedByKra;
  final double extraInstructionRaw;

  const WhatIfScenario({this.extraWeightedByKra = const {}, this.extraInstructionRaw = 0});

  WhatIfScenario copyWith({Map<String, double>? extraWeightedByKra, double? extraInstructionRaw}) =>
      WhatIfScenario(
        extraWeightedByKra: extraWeightedByKra ?? this.extraWeightedByKra,
        extraInstructionRaw: extraInstructionRaw ?? this.extraInstructionRaw,
      );

  static const empty = WhatIfScenario();
}

class SimulationEngine {
  static SimulationSnapshot compute(MockRepository repo, {bool verified = false, WhatIfScenario whatIf = WhatIfScenario.empty}) {
    if (repo.rankSimulationJson != null) {
      final rankSim = FacultyRankSimulation.fromJson(repo.rankSimulationJson);
      return _fromRankSimulation(repo, rankSim, verified: verified, whatIf: whatIf);
    }
    if (repo.scoresConfigured) {
      return _fromBackendScores(repo, verified: verified, whatIf: whatIf);
    }
    return _legacyCompute(repo, verified: verified, whatIf: whatIf);
  }

  static SimulationSnapshot _fromRankSimulation(
    MockRepository repo,
    FacultyRankSimulation rankSim, {
    required bool verified,
    required WhatIfScenario whatIf,
  }) {
    final bucket = verified ? rankSim.verified : rankSim.estimated;
    if (!bucket.configured) {
      return SimulationSnapshot(
        weightedTotal: 0,
        overallRaw: 0,
        kras: const [],
        missingRequirements: const [
          'Complete your profile with a recognized current rank before rank simulation can run.',
        ],
        pendingEvidence: const [],
        scoresFromBackend: true,
        scoringAuthoritative: false,
        usesRankTableWeights: true,
        scoreSourceLabel: verified ? 'verified' : 'estimated',
      );
    }

    const kraNames = {
      'kra-I': 'KRA I – Instruction',
      'kra-II': 'KRA II – Research, Innovation and/or Creative Work',
      'kra-III': 'KRA III – Extension Services',
      'kra-IV': 'KRA IV – Professional Development',
    };

    var weighted = bucket.overallWeightedScore;
    final lines = bucket.kras
        .map(
          (k) => KraBreakdownLine(
            kraId: k.kraId,
            name: kraNames[k.kraId] ?? k.kraId,
            rawTotal: k.rawTotal,
            weight: k.weight,
            weightedContribution: k.weightedContribution,
          ),
        )
        .toList();
    final rawSum = lines.fold(0.0, (a, l) => a + l.rawTotal);

    final missing = <String>[
      ...bucket.notes,
      if (!verified) 'Faculty self-assessment (estimated) — not reviewer-verified.',
      if (whatIf != WhatIfScenario.empty)
        'What-if scenario is shown separately and does not change saved assessment or review outcomes.',
    ];
    if (bucket.bracket?.unresolvedReason != null) {
      missing.add(bucket.bracket!.unresolvedReason!);
    }
    for (final n in bucket.potentialRank?.notes ?? const <String>[]) {
      missing.add(n);
    }

    final pending = repo.documents
        .where((d) => d.countsAsPendingForFaculty)
        .map((d) => d.fileName)
        .toList();

    return SimulationSnapshot(
      weightedTotal: weighted,
      overallRaw: rawSum,
      kras: lines,
      missingRequirements: missing,
      pendingEvidence: pending,
      scoresFromBackend: true,
      scoringAuthoritative: bucket.scoringAuthoritative,
      usesRankTableWeights: true,
      rankCategoryLabel: bucket.rankCategoryLabel,
      subRankBracket: bucket.bracket,
      potentialRank: bucket.potentialRank,
      scoreSourceLabel: verified ? 'verified' : 'estimated',
      basisLabel: bucket.basisLabel,
      bucketCurrentRank: bucket.currentRank,
      conditionalRankProjections: bucket.conditionalRankProjections,
    );
  }

  static RankEvaluation evaluateFromSnapshot(SimulationSnapshot snapshot) {
    final pr = snapshot.potentialRank;
    final bracket = snapshot.subRankBracket;
    final basis = snapshot.basisLabel ??
        (snapshot.scoreSourceLabel == 'verified' ? 'Reviewer-verified points' : 'Estimated points');
    if (pr == null || pr.status == 'unresolved' || pr.potentialRank == null) {
      return RankEvaluation(
        potentialRank: bracket?.unresolvedReason ?? 'Projected rank unavailable',
        readinessLabel: 'Not available',
        simulationStatus: 'Basis: $basis',
        unmetConditions: snapshot.missingRequirements,
      );
    }
    final inc = pr.increments;
    final movement = pr.movement;
    final statusCore = pr.displayLabel ?? 'Preparation only — not an official promotion decision';
    return RankEvaluation(
      potentialRank: pr.potentialRank!,
      readinessLabel: movement ?? (inc != null ? 'Sub-rank increment: $inc' : '—'),
      simulationStatus: 'Basis: $basis · $statusCore',
      unmetConditions: [...pr.notes, ...snapshot.missingRequirements],
    );
  }

  static SimulationSnapshot _fromBackendScores(
    MockRepository repo, {
    required bool verified,
    required WhatIfScenario whatIf,
  }) {
    final mode = verified ? repo.facultyScoresVerified : repo.facultyScoresEstimated;
    final byKra = (mode?['byKra'] as Map<String, dynamic>?) ?? {};
    final notes = (mode?['notes'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [];

    final lines = <KraBreakdownLine>[];
    var weighted = 0.0;
    var rawSum = 0.0;

    const kraOrder = ['kra-I', 'kra-II', 'kra-III', 'kra-IV'];
    final names = {
      'kra-I': 'KRA I – Instruction',
      'kra-II': 'KRA II – Research, Innovation and/or Creative Work',
      'kra-III': 'KRA III – Extension Services',
      'kra-IV': 'KRA IV – Professional Development',
    };
    final caps = {
      'kra-I': 60.0,
      'kra-II': 100.0,
      'kra-III': 100.0,
      'kra-IV': 100.0,
    };

    for (final kraId in kraOrder) {
      final row = byKra[kraId] as Map<String, dynamic>? ?? {};
      final weight = (row['weight'] as num?)?.toDouble() ?? (repo.kraWeightsFromApi?[kraId] as num?)?.toDouble() ?? kraWeights[kraId] ?? 0.0;
      var raw = (row['rawTotal'] as num?)?.toDouble() ?? 0.0;
      if (kraId == 'kra-I' && whatIf.extraInstructionRaw != 0) {
        raw = cap(raw + whatIf.extraInstructionRaw, caps[kraId]);
      }
      var contrib = (row['weightedContribution'] as num?)?.toDouble() ?? raw * weight;
      if (whatIf.extraInstructionRaw != 0 && kraId == 'kra-I') {
        contrib = raw * weight;
      }
      if (whatIf.extraWeightedByKra.containsKey(kraId)) {
        contrib += whatIf.extraWeightedByKra[kraId]!;
      }
      final incomplete = row['criterionAIncomplete'] == true;
      final reason = row['criterionAIncompleteReason'] as String?;
      final critRaw = (row['criteria'] as List<dynamic>?) ?? [];
      final critLines = critRaw
          .map(
            (c) => CriterionBreakdownLine(
              criterionId: (c as Map)['id'] as String? ?? '',
              name: c['name'] as String?,
              rawTotal: (c['rawTotal'] as num?)?.toDouble() ?? 0,
              capMaxPoints: (c['capMaxPoints'] as num?)?.toDouble(),
            ),
          )
          .where((c) => c.criterionId.isNotEmpty)
          .toList();
      lines.add(KraBreakdownLine(
        kraId: kraId,
        name: row['name'] as String? ?? names[kraId] ?? kraId,
        rawTotal: raw,
        rawCap: caps[kraId],
        weight: weight,
        weightedContribution: contrib,
        rawIncomplete: incomplete,
        incompleteReason: reason,
        criteria: critLines,
      ));
      weighted += contrib;
      rawSum += raw;
    }

    var authoritative = true;
    final missing = <String>[...notes];
    for (final line in lines) {
      if (line.rawIncomplete && line.incompleteReason != null) {
        missing.add(line.incompleteReason!);
      }
    }
    for (final kraId in kraOrder) {
      final row = byKra[kraId] as Map<String, dynamic>? ?? {};
      if (row['kraCapPolicyUnresolved'] == true) {
        authoritative = false;
        final policyNote = row['kraCapPolicyNote'] as String?;
        if (policyNote != null && policyNote.isNotEmpty) {
          missing.add('Provisional KRA IV subtotal — $policyNote');
        }
      }
      if (kraId == 'kra-IV' && row['coreSubtotal'] != null) {
        final core = (row['coreSubtotal'] as num?)?.toDouble();
        final addl = (row['additionalSubtotal'] as num?)?.toDouble();
        if (core != null && addl != null && row['kraCapPolicyUnresolved'] == true) {
          missing.add(
            'KRA IV core (A+B+C): ${core.toStringAsFixed(2)} pts; D additional: ${addl.toStringAsFixed(2)} pts (provisional until envelope policy is published).',
          );
        }
      }
    }

    final pending = repo.documents
        .where((d) => d.countsAsPendingForFaculty)
        .map((d) => d.fileName)
        .toList();

    return SimulationSnapshot(
      weightedTotal: weighted,
      overallRaw: rawSum,
      kras: lines,
      missingRequirements: missing,
      pendingEvidence: pending,
      scoresFromBackend: true,
      scoringAuthoritative: authoritative,
    );
  }

  static SimulationSnapshot _legacyCompute(MockRepository repo, {bool verified = false, WhatIfScenario whatIf = WhatIfScenario.empty}) {
    final set = computeSetSef(repo.setRatings, 'SET');
    final sef = computeSetSef(repo.sefRatings, 'SEF');
    var instructionRaw = cap(set.raw + sef.raw + whatIf.extraInstructionRaw, 60);

    double sumEntries(String kraPrefix, bool useVerified) {
      return repo.entries.where((e) => e.indicatorId.startsWith(kraPrefix)).fold(0.0, (a, e) {
        if (useVerified && e.reviewStatus == 'approved' && e.verifiedPoints != null) {
          return a + e.verifiedPoints!;
        }
        return a + e.estimatedPoints;
      });
    }

    final kraDefs = [
      ('kra-I', 'KRA I – Instruction', instructionRaw, 60.0),
      ('kra-II', 'KRA II – Research, Innovation and/or Creative Work', sumEntries('kra-II', verified), 100.0),
      ('kra-III', 'KRA III – Extension Services', sumEntries('kra-III', verified), 100.0),
      ('kra-IV', 'KRA IV – Professional Development', sumEntries('kra-IV', verified), 100.0),
    ];

    final lines = <KraBreakdownLine>[];
    var weighted = 0.0;
    var rawSum = 0.0;

    for (final row in kraDefs) {
      final w = kraWeights[row.$1] ?? 0;
      var contrib = row.$3 * w;
      if (whatIf.extraWeightedByKra.containsKey(row.$1)) {
        contrib += whatIf.extraWeightedByKra[row.$1]!;
      }
      lines.add(KraBreakdownLine(
        kraId: row.$1,
        name: row.$2,
        rawTotal: row.$3,
        rawCap: row.$4,
        weight: w,
        weightedContribution: contrib,
      ));
      weighted += contrib;
      rawSum += row.$3;
    }

    final missingSet = repo.setRatings.where((r) => r == null).length;
    final missingSef = repo.sefRatings.where((r) => r == null).length;
    final missing = <String>[];
    if (missingSet > 0) missing.add('$missingSet SET semester rating(s) not entered');
    if (missingSef > 0) missing.add('$missingSef SEF semester rating(s) not entered');

    final pending = repo.documents
        .where((d) => d.countsAsPendingForFaculty)
        .map((d) => d.fileName)
        .toList();

    return SimulationSnapshot(
      weightedTotal: weighted,
      overallRaw: rawSum,
      kras: lines,
      missingRequirements: missing,
      pendingEvidence: pending,
    );
  }

  static String nextRankOption(InstitutionConfig cfg, String currentRank) {
    final i = cfg.rankOptions.indexOf(currentRank);
    if (i < 0 || i >= cfg.rankOptions.length - 1) return cfg.rankOptions.length > 1 ? cfg.rankOptions[1] : currentRank;
    return cfg.rankOptions[i + 1];
  }

  static RankEvaluation evaluateTarget({
    required InstitutionConfig cfg,
    required String targetRank,
    required double weightedTotal,
    bool scoringAuthoritative = true,
  }) {
    if (!scoringAuthoritative) {
      return RankEvaluation(
        potentialRank: 'Provisional scoring only',
        readinessLabel: 'Not available',
        simulationStatus: 'Rank simulation unavailable while KRA IV envelope policy is unresolved',
        unmetConditions: const [
          'Weighted totals may include provisional KRA IV subtotals. Publish envelope policy before using rank simulation.',
        ],
      );
    }
    if (cfg.rankMappingStatus != 'configured') {
      return RankEvaluation(
        potentialRank: 'Pending configuration',
        readinessLabel: 'Not available',
        simulationStatus: 'Rank mapping pending configuration',
        unmetConditions: const ['Institution rank requirements are not published.'],
      );
    }
    final req = cfg.rankRequirements[targetRank];
    if (req?.minWeightedTotal == null) {
      return RankEvaluation(
        potentialRank: 'Requirements to be confirmed',
        readinessLabel: 'Not available',
        simulationStatus: 'Target rank requirements not configured',
        unmetConditions: ['No minimum weighted total configured for $targetRank.'],
      );
    }
    final min = req!.minWeightedTotal!;
    final met = weightedTotal >= min;
    final pct = met ? 100.0 : (weightedTotal / min * 100).clamp(0, 99).roundToDouble();
    return RankEvaluation(
      potentialRank: met ? targetRank : '$targetRank (below minimum)',
      readinessPercent: met ? 100 : pct,
      readinessLabel: met ? '100% toward configured minimum' : '${pct.toStringAsFixed(0)}% of configured minimum',
      simulationStatus: met ? 'Meets configured minimum (preparation only)' : 'Below configured minimum',
      unmetConditions: met
          ? const []
          : ['Weighted total ${weightedTotal.toStringAsFixed(2)} below configured minimum $min for $targetRank.'],
    );
  }
}
