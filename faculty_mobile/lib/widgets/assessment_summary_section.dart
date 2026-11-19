import 'package:flutter/material.dart';

import '../core/simulation_presenter.dart';
import '../core/ui_strings.dart';
import '../models/institution_config.dart';
import '../services/assessment_overview_model.dart';
import '../services/simulation_engine.dart';
import '../theme/app_spacing.dart';
import '../theme/app_theme.dart';

/// Single assessment summary: current rank, score mode, overall score, potential rank.
class AssessmentSummarySection extends StatelessWidget {
  final AssessmentOverviewModel model;
  final InstitutionConfig institutionConfig;
  final String currentProfileRank;
  final bool showVerified;
  final ValueChanged<bool> onShowVerifiedChanged;
  final TextScaler scale;

  const AssessmentSummarySection({
    super.key,
    required this.model,
    required this.institutionConfig,
    required this.currentProfileRank,
    required this.showVerified,
    required this.onShowVerifiedChanged,
    required this.scale,
  });

  SimulationSnapshot get _active {
    if (showVerified && model.verifiedAvailable && model.verified != null) {
      return model.verified!;
    }
    return model.estimated;
  }

  bool get _hasVerifiedSnapshot => model.verifiedAvailable && model.verified != null;

  bool get _partialVerification {
    if (!showVerified || !_hasVerifiedSnapshot) return false;
    if (model.verified!.kras.any((k) => k.rawIncomplete)) return true;
    final notes = model.verified!.missingRequirements.map((e) => e.toLowerCase());
    return notes.any((n) => n.contains('partial') || n.contains('incomplete'));
  }

  @override
  Widget build(BuildContext context) {
    final active = _active;
    final usesRankTable = active.usesRankTableWeights;
    final target = SimulationEngine.nextRankOption(institutionConfig, currentProfileRank);
    final eval = usesRankTable
        ? SimulationEngine.evaluateFromSnapshot(active)
        : SimulationEngine.evaluateTarget(
            cfg: institutionConfig,
            targetRank: target,
            weightedTotal: active.weightedTotal,
            scoringAuthoritative: active.scoringAuthoritative,
          );
    final displayCurrent = active.bucketCurrentRank ?? currentProfileRank;
    final potential = SimulationPresenter.potentialRankLabel(
      eval,
      institutionConfig,
      usesRankTable: usesRankTable,
    );
    final rulesNote = usesRankTable ? null : SimulationPresenter.rankRulesNotice(institutionConfig);
    final decimalConditional = _decimalPolicyConditional(active);
    final subRankInc =
        active.subRankBracket?.subRankIncrements ?? active.subRankBracket?.provisionalIncrements;
    final scoreLabel = model.scoresWeighted ? 'Overall weighted score' : 'Overall raw score';

    final verifiedMissing = showVerified && !_hasVerifiedSnapshot;
    final scoreDisplay = verifiedMissing ? 'Not yet verified' : active.weightedTotal.toStringAsFixed(2);
    final scoreMuted = verifiedMissing;
    final potentialText = verifiedMissing
        ? 'Not yet verified'
        : _potentialDisplay(
            potential: potential,
            rulesNote: rulesNote,
            usesRankTable: usesRankTable,
            eval: eval,
          );

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        FlSurfaceCard(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(Icons.school_outlined, size: scale.scale(22), color: AppColors.primaryBlue),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Current rank',
                      style: TextStyle(
                        fontSize: scale.scale(13),
                        color: AppColors.textMuted,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      displayCurrent,
                      style: TextStyle(
                        fontSize: scale.scale(18),
                        fontWeight: FontWeight.w700,
                        color: AppColors.textMain,
                        height: 1.3,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: FlLayout.sectionGap),
        Semantics(
          label: 'Choose estimated or reviewer verified points',
          child: _ScoreModeSelector(
            scale: scale,
            showVerified: showVerified,
            onChanged: onShowVerifiedChanged,
          ),
        ),
        const SizedBox(height: FlLayout.sectionGap),
        FlSurfaceCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                scoreLabel,
                style: TextStyle(
                  fontSize: scale.scale(13),
                  color: AppColors.textMuted,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 6),
              Wrap(
                crossAxisAlignment: WrapCrossAlignment.center,
                spacing: 4,
                children: [
                  Text(
                    scoreDisplay,
                    style: TextStyle(
                      fontSize: scale.scale(scoreMuted ? 18 : 32),
                      fontWeight: FontWeight.w800,
                      color: scoreMuted ? AppColors.amberText : AppColors.textNavy,
                      height: 1.1,
                    ),
                  ),
                  if (!scoreMuted && model.scoresWeighted)
                    Text(
                      '/ 100',
                      style: TextStyle(
                        fontSize: scale.scale(18),
                        fontWeight: FontWeight.w600,
                        color: AppColors.textMuted,
                      ),
                    ),
                ],
              ),
              if (_partialVerification) ...[
                const SizedBox(height: 8),
                Text(
                  'Partial verification — some areas still need reviewer confirmation.',
                  style: TextStyle(fontSize: scale.scale(13), color: AppColors.amberText, height: 1.4),
                ),
              ],
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 16),
                child: Divider(height: 1, color: AppColors.border),
              ),
              Text(
                decimalConditional && !verifiedMissing
                    ? 'Conditional potential rank'
                    : 'Potential rank',
                style: TextStyle(
                  fontSize: scale.scale(13),
                  color: AppColors.textMuted,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                potentialText,
                style: TextStyle(
                  fontSize: scale.scale(verifiedMissing ? 18 : 22),
                  fontWeight: FontWeight.w800,
                  color: verifiedMissing ? AppColors.amberText : AppColors.textNavy,
                  height: 1.25,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Simulation for preparation only — not an official rank decision.',
                style: TextStyle(fontSize: scale.scale(13), color: AppColors.textMuted, height: 1.4),
              ),
              if (!verifiedMissing && subRankInc != null) ...[
                const SizedBox(height: 6),
                Text(
                  'From $displayCurrent · $subRankInc sub-rank increment${subRankInc == 1 ? '' : 's'}',
                  style: TextStyle(fontSize: scale.scale(14), height: 1.4, color: AppColors.textMain),
                ),
              ],
              if (!verifiedMissing && rulesNote != null) ...[
                const SizedBox(height: 8),
                Text(rulesNote, style: TextStyle(fontSize: scale.scale(14), color: AppColors.amberText, height: 1.4)),
              ],
              if (!verifiedMissing && _qualification(active, decimalConditional).isNotEmpty) ...[
                const SizedBox(height: 8),
                Text(
                  _qualification(active, decimalConditional),
                  style: TextStyle(fontSize: scale.scale(13), color: AppColors.amberText, height: 1.4),
                ),
              ],
              if (!verifiedMissing && usesRankTable && active.rankCategoryLabel != null) ...[
                const SizedBox(height: 12),
                Text(
                  'Weights: ${active.rankCategoryLabel} (Table 2.2 · current-rank weights)',
                  style: TextStyle(fontSize: scale.scale(12), color: AppColors.textMuted, height: 1.35),
                ),
                Text(
                  'Promotion score = sum of (capped KRA raw × current-rank weight). '
                  'Raw KRA sum ${active.overallRaw.toStringAsFixed(2)} is not the promotion score.',
                  style: TextStyle(fontSize: scale.scale(12), color: AppColors.textMuted, height: 1.35),
                ),
              ],
            ],
          ),
        ),
      ],
    );
  }

  String _potentialDisplay({
    required String potential,
    required String? rulesNote,
    required bool usesRankTable,
    required RankEvaluation eval,
  }) {
    if (!usesRankTable && rulesNote != null) {
      return 'Not available yet';
    }
    final lower = potential.toLowerCase();
    if (lower.contains('pending configuration') ||
        lower.contains('requirements to be confirmed') ||
        lower == 'not available yet') {
      return 'Not available yet';
    }
    if (potential.trim().isEmpty) {
      return 'Not available yet';
    }
    return potential;
  }

  bool _decimalPolicyConditional(SimulationSnapshot active) {
    final b = active.subRankBracket;
    if (b == null) return false;
    return b.status == 'conditional' ||
        (b.subRankIncrements == null && b.provisionalIncrements != null);
  }

  String _qualification(SimulationSnapshot active, bool decimalPolicyConditional) {
    if (decimalPolicyConditional) {
      return 'Subject to confirmation of the scoring policy.';
    }
    if (!active.scoringAuthoritative) {
      return 'Provisional scoring — not confirmed.';
    }
    final pr = active.potentialRank;
    if (pr?.status == 'eligibility_required') {
      return 'Eligibility subject to verification.';
    }
    if (pr?.displayLabel != null &&
        pr!.displayLabel!.isNotEmpty &&
        pr.displayLabel != UiStrings.simDisclaimer &&
        !pr.displayLabel!.toLowerCase().contains('preparation only')) {
      return pr.displayLabel!;
    }
    return '';
  }
}

class _ScoreModeSelector extends StatelessWidget {
  final TextScaler scale;
  final bool showVerified;
  final ValueChanged<bool> onChanged;

  const _ScoreModeSelector({
    required this.scale,
    required this.showVerified,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    Widget option({required bool selected, required String label, required VoidCallback onTap}) {
      return Material(
        color: selected ? AppColors.primarySoft : AppColors.cardWhite,
        borderRadius: BorderRadius.circular(12),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(12),
          child: Container(
            constraints: const BoxConstraints(minHeight: 48),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: selected ? AppColors.primaryBlue : AppColors.border,
                width: selected ? 1.5 : 1,
              ),
            ),
            alignment: Alignment.center,
            child: Text(
              label,
              textAlign: TextAlign.center,
              softWrap: true,
              style: TextStyle(
                fontSize: scale.scale(14),
                fontWeight: selected ? FontWeight.w700 : FontWeight.w600,
                color: selected ? AppColors.primaryBlue : AppColors.textMain,
                height: 1.25,
              ),
            ),
          ),
        ),
      );
    }

    return LayoutBuilder(
      builder: (context, constraints) {
        final narrow = constraints.maxWidth < 360;
        final est = option(
          selected: !showVerified,
          label: UiStrings.estimatedPoints,
          onTap: () => onChanged(false),
        );
        final ver = option(
          selected: showVerified,
          label: UiStrings.verifiedPoints,
          onTap: () => onChanged(true),
        );
        if (narrow) {
          return Column(children: [est, const SizedBox(height: 8), ver]);
        }
        return Row(
          children: [
            Expanded(child: est),
            const SizedBox(width: 10),
            Expanded(child: ver),
          ],
        );
      },
    );
  }
}
