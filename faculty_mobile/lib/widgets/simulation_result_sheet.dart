import 'package:flutter/material.dart';

import '../core/simulation_presenter.dart';
import '../core/ui_strings.dart';
import '../data/assessment_catalog.dart';
import '../models/institution_config.dart';
import '../repositories/mock_repository.dart';
import '../services/simulation_engine.dart';
import '../theme/app_spacing.dart';
import '../theme/app_theme.dart';

/// Scrollable simulation summary (opened from Home). Calculations unchanged.
class SimulationResultSheet extends StatelessWidget {
  final MockRepository repo;
  final InstitutionConfig institutionConfig;
  final WhatIfScenario whatIf;
  final VoidCallback onOpenFullSimulation;

  const SimulationResultSheet({
    super.key,
    required this.repo,
    required this.institutionConfig,
    required this.whatIf,
    required this.onOpenFullSimulation,
  });

  static Future<void> show(
    BuildContext context, {
    required MockRepository repo,
    required InstitutionConfig institutionConfig,
    required WhatIfScenario whatIf,
    required VoidCallback onOpenFullSimulation,
  }) {
    return showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => SimulationResultSheet(
        repo: repo,
        institutionConfig: institutionConfig,
        whatIf: whatIf,
        onOpenFullSimulation: onOpenFullSimulation,
      ),
    );
  }

  String _kraShort(String kraId) {
    final k = assessmentKras.where((e) => e.id == kraId).firstOrNull;
    return k?.shortDropdownLabel ?? kraId;
  }

  @override
  Widget build(BuildContext context) {
    final est = SimulationEngine.compute(repo, whatIf: whatIf);
    final ver = SimulationEngine.compute(repo, verified: true, whatIf: whatIf);
    final target = SimulationEngine.nextRankOption(institutionConfig, repo.profile.rank);
    final eval = est.usesRankTableWeights
        ? SimulationEngine.evaluateFromSnapshot(est)
        : SimulationEngine.evaluateTarget(
            cfg: institutionConfig,
            targetRank: target,
            weightedTotal: est.weightedTotal,
            scoringAuthoritative: est.scoringAuthoritative,
          );
    final potential = SimulationPresenter.potentialRankLabel(
      eval,
      institutionConfig,
      usesRankTable: est.usesRankTableWeights,
    );
    final readiness = SimulationPresenter.readinessLine(eval, institutionConfig);
    final rulesNote = SimulationPresenter.rankRulesNotice(institutionConfig);
    final scale = MediaQuery.textScalerOf(context);

    return DraggableScrollableSheet(
      initialChildSize: 0.88,
      minChildSize: 0.45,
      maxChildSize: 0.95,
      expand: false,
      builder: (context, scrollController) {
        return Material(
          color: AppColors.bgLight,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
          child: Column(
            children: [
              Container(
                width: double.infinity,
                padding: const EdgeInsets.fromLTRB(18, 14, 8, 14),
                decoration: const BoxDecoration(
                  color: AppColors.primaryBlue,
                  borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.insights_outlined, color: Colors.white),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        'Simulation Result',
                        style: TextStyle(
                          fontSize: scale.scale(22),
                          fontWeight: FontWeight.w700,
                          color: Colors.white,
                        ),
                      ),
                    ),
                    IconButton(
                      onPressed: () => Navigator.pop(context),
                      tooltip: 'Close',
                      color: Colors.white,
                      icon: const Icon(Icons.close),
                    ),
                  ],
                ),
              ),
              Expanded(
                child: ListView(
                  controller: scrollController,
                  padding: FlLayout.pagePadding.copyWith(top: 8),
                  children: [
                    _sectionTitle('1. Your current rank', scale),
                    FlSurfaceCard(
                      child: Text(
                        repo.profile.rank,
                        style: TextStyle(fontSize: scale.scale(20), fontWeight: FontWeight.w700, color: AppColors.textNavy),
                      ),
                    ),
                    const SizedBox(height: FlLayout.sectionGap),
                    _sectionTitle('2. Your points', scale),
                    FlSurfaceCard(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          _labeledValue(UiStrings.estimatedPoints, est.weightedTotal.toStringAsFixed(2), scale, large: true),
                          const SizedBox(height: 12),
                          _labeledValue(UiStrings.verifiedPoints, ver.weightedTotal.toStringAsFixed(2), scale),
                          const SizedBox(height: 8),
                          Text(
                            UiStrings.estimatedPointsHelp,
                            style: TextStyle(fontSize: scale.scale(15), color: AppColors.textMuted, height: 1.4),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: FlLayout.sectionGap),
                    _sectionTitle('3. Your potential rank', scale),
                    FlSurfaceCard(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            potential,
                            style: TextStyle(fontSize: scale.scale(20), fontWeight: FontWeight.w700, color: AppColors.textNavy),
                          ),
                          if (rulesNote != null) ...[
                            const SizedBox(height: 8),
                            Text(rulesNote, style: TextStyle(fontSize: scale.scale(16), color: AppColors.textMuted, height: 1.45)),
                          ] else if (readiness != null) ...[
                            const SizedBox(height: 8),
                            Text(
                              'Readiness: $readiness',
                              style: TextStyle(fontSize: scale.scale(16), color: AppColors.textNavy, height: 1.4),
                            ),
                          ],
                        ],
                      ),
                    ),
                    const SizedBox(height: FlLayout.sectionGap),
                    _sectionTitle('4. Points by KRA', scale),
                    ...est.kras.map(
                      (k) => Padding(
                        padding: const EdgeInsets.only(bottom: 10),
                        child: FlSurfaceCard(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                _kraShort(k.kraId),
                                style: TextStyle(fontSize: scale.scale(17), fontWeight: FontWeight.w700, color: AppColors.textNavy),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                k.name,
                                style: TextStyle(fontSize: scale.scale(15), color: AppColors.textMuted, height: 1.4),
                              ),
                              const SizedBox(height: 10),
                              Text(
                                'Weighted contribution: ${k.weightedContribution.toStringAsFixed(2)}',
                                style: TextStyle(fontSize: scale.scale(16), fontWeight: FontWeight.w600),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                    FlSurfaceCard(
                      child: ExpansionTile(
                        tilePadding: EdgeInsets.zero,
                        title: Text(
                          'How are my points calculated?',
                          style: TextStyle(fontSize: scale.scale(17), fontWeight: FontWeight.w600),
                        ),
                        children: [
                          Text(
                            'Each KRA has a weight. SET and SEF ratings feed Instruction. '
                            'Estimated points are your self-assessment. Reviewer-verified points are checked by your reviewer.',
                            style: TextStyle(fontSize: scale.scale(16), height: 1.5, color: AppColors.textMuted),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: FlLayout.sectionGap),
                    _sectionTitle('5. What you can do next', scale),
                    FlSurfaceCard(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          if (est.pendingEvidence.isNotEmpty)
                            Text('• Finish uploading: ${est.pendingEvidence.first}', style: _body(scale)),
                          if (est.missingRequirements.isNotEmpty)
                            Text('• ${est.missingRequirements.first}', style: _body(scale)),
                          if (est.pendingEvidence.isEmpty && est.missingRequirements.isEmpty)
                            Text('• Keep adding proof and update your assessment.', style: _body(scale)),
                          Text('• Try practice points in the full simulator.', style: _body(scale)),
                        ],
                      ),
                    ),
                    const SizedBox(height: 12),
                    FlYellowButton(
                      label: 'Open full simulation',
                      icon: Icons.insights_outlined,
                      onPressed: () {
                        Navigator.pop(context);
                        onOpenFullSimulation();
                      },
                    ),
                    const SizedBox(height: 8),
                    SizedBox(
                      width: double.infinity,
                      child: OutlinedButton(
                        onPressed: () => Navigator.pop(context),
                        child: const Text('Close'),
                      ),
                    ),
                    Text(
                      UiStrings.simDisclaimer,
                      style: TextStyle(fontSize: scale.scale(14), color: AppColors.textMuted, height: 1.45),
                    ),
                    const SizedBox(height: 24),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  TextStyle _body(TextScaler scale) => TextStyle(fontSize: scale.scale(16), height: 1.45, color: AppColors.textNavy);

  Widget _sectionTitle(String text, TextScaler scale) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Text(
        text,
        style: TextStyle(
          fontSize: scale.scale(18),
          fontWeight: FontWeight.w700,
          color: AppColors.textNavy,
        ),
      ),
    );
  }

  Widget _labeledValue(String label, String value, TextScaler scale, {bool large = false}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: TextStyle(fontSize: scale.scale(15), color: AppColors.textMuted)),
        const SizedBox(height: 4),
        Text(
          value,
          style: TextStyle(
            fontSize: scale.scale(large ? 28 : 20),
            fontWeight: FontWeight.w800,
            color: AppColors.textNavy,
          ),
        ),
      ],
    );
  }
}
