import '../core/scoring.dart';
import '../models/institution_config.dart';
import '../repositories/mock_repository.dart';

class KraBreakdownLine {
  final String kraId;
  final String name;
  final double rawTotal;
  final double? rawCap;
  final double weight;
  final double weightedContribution;

  KraBreakdownLine({
    required this.kraId,
    required this.name,
    required this.rawTotal,
    this.rawCap,
    required this.weight,
    required this.weightedContribution,
  });
}

class SimulationSnapshot {
  final double weightedTotal;
  final double overallRaw;
  final List<KraBreakdownLine> kras;
  final List<String> missingRequirements;
  final List<String> pendingEvidence;

  SimulationSnapshot({
    required this.weightedTotal,
    required this.overallRaw,
    required this.kras,
    required this.missingRequirements,
    required this.pendingEvidence,
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
        .where((d) => d.reviewStatus == 'pending' || d.reviewStatus == 'correction_requested')
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
  }) {
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
