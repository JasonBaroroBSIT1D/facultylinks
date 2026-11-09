import 'package:flutter/material.dart';

import '../core/simulation_presenter.dart';
import '../core/ui_strings.dart';
import '../models/institution_config.dart';
import '../repositories/mock_repository.dart';
import '../services/simulation_engine.dart';
import '../theme/app_spacing.dart';
import '../theme/app_theme.dart';

class SimulationSummaryCard extends StatelessWidget {
  final MockRepository repo;
  final InstitutionConfig institutionConfig;
  final WhatIfScenario whatIf;
  final VoidCallback onTap;

  SimulationSummaryCard({
    super.key,
    required this.repo,
    required this.institutionConfig,
    this.whatIf = WhatIfScenario.empty,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final snapshot = SimulationEngine.compute(repo, whatIf: whatIf);
    final target = SimulationEngine.nextRankOption(institutionConfig, repo.profile.rank);
    final eval = snapshot.usesRankTableWeights
        ? SimulationEngine.evaluateFromSnapshot(snapshot)
        : SimulationEngine.evaluateTarget(
            cfg: institutionConfig,
            targetRank: target,
            weightedTotal: snapshot.weightedTotal,
            scoringAuthoritative: snapshot.scoringAuthoritative,
          );
    final potential = SimulationPresenter.potentialRankLabel(
      eval,
      institutionConfig,
      usesRankTable: snapshot.usesRankTableWeights,
    );
    final rulesNote = SimulationPresenter.rankRulesNotice(institutionConfig);
    final scale = MediaQuery.textScalerOf(context);
    final width = MediaQuery.sizeOf(context).width;
    final twoCol = width >= 320 && scale.scale(1) <= 1.2;

    final pointsColumn = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          UiStrings.estimatedPoints,
          style: TextStyle(
            color: Colors.white.withValues(alpha: 0.88),
            fontSize: scale.scale(14),
          ),
        ),
        const SizedBox(height: 2),
        Text(
          snapshot.weightedTotal.toStringAsFixed(2),
          style: TextStyle(
            color: Colors.white,
            fontWeight: FontWeight.w800,
            fontSize: scale.scale(30),
            height: 1.1,
          ),
        ),
      ],
    );

    final rankColumn = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _miniRank('Current rank', repo.profile.rank, scale),
        const SizedBox(height: 8),
        _miniRank(
          'Potential rank',
          potential == 'Not available yet' ? 'Not available yet' : potential,
          scale,
        ),
        if (rulesNote != null) ...[
          const SizedBox(height: 6),
          Text(
            rulesNote,
            style: TextStyle(
              color: Colors.white.withValues(alpha: 0.92),
              fontSize: scale.scale(13),
              height: 1.35,
            ),
          ),
        ],
      ],
    );

    return Semantics(
      label: 'Rank simulation summary',
      child: DecoratedBox(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(18),
          color: AppColors.primaryBlue,
          boxShadow: [
            BoxShadow(
              color: AppColors.navyDeep.withValues(alpha: 0.14),
              blurRadius: 10,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                'Rank Simulation',
                style: TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.w700,
                  fontSize: scale.scale(18),
                ),
              ),
              const SizedBox(height: 12),
              if (twoCol)
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(flex: 5, child: pointsColumn),
                    const SizedBox(width: 12),
                    Expanded(flex: 6, child: rankColumn),
                  ],
                )
              else ...[
                pointsColumn,
                const SizedBox(height: 12),
                rankColumn,
              ],
              const SizedBox(height: 12),
              FlYellowButton(
                label: 'View Simulation',
                onPressed: onTap,
                compact: true,
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _miniRank(String label, String value, TextScaler scale) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: TextStyle(
            color: Colors.white.withValues(alpha: 0.78),
            fontSize: scale.scale(12),
          ),
        ),
        Text(
          value,
          style: TextStyle(
            color: Colors.white,
            fontWeight: FontWeight.w600,
            fontSize: scale.scale(15),
            height: 1.25,
          ),
        ),
      ],
    );
  }
}
