import '../models/institution_config.dart';
import '../services/simulation_engine.dart';

/// Shared labels for the home simulation card and result sheet (same state).
class SimulationPresenter {
  static bool rulesConfigured(InstitutionConfig cfg) => cfg.rankMappingStatus == 'configured';

  static String potentialRankLabel(RankEvaluation eval, InstitutionConfig cfg, {bool usesRankTable = false}) {
    if (usesRankTable) return eval.potentialRank;
    if (!rulesConfigured(cfg)) return 'Not available yet';
    if (eval.potentialRank == 'Pending configuration' || eval.potentialRank == 'Requirements to be confirmed') {
      return 'Not available yet';
    }
    return eval.potentialRank;
  }

  static String? readinessLine(RankEvaluation eval, InstitutionConfig cfg) {
    if (!rulesConfigured(cfg) || eval.readinessPercent == null) return null;
    return eval.readinessLabel;
  }

  static String statusLine(RankEvaluation eval, InstitutionConfig cfg, {bool usesRankTable = false}) {
    if (usesRankTable) return eval.simulationStatus;
    if (!rulesConfigured(cfg)) return 'Using your estimated points';
    return eval.simulationStatus;
  }

  static String? rankRulesNotice(InstitutionConfig cfg) {
    if (rulesConfigured(cfg)) return null;
    return 'Rank requirements are not set yet.';
  }
}
