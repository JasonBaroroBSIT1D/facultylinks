import 'package:flutter/material.dart';

import '../../models/institution_config.dart';
import '../../repositories/mock_repository.dart';
import '../../services/simulation_engine.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_theme.dart';
import '../../widgets/home_kra_grid.dart';
import '../../widgets/home_progress_overview.dart';
import '../../widgets/home_quick_actions.dart';
import '../../widgets/simulation_result_sheet.dart';
import '../preparation_period_screen.dart';
import '../upload_evidence_screen.dart';
import 'assessment_tab.dart';

String _firstName(String fullName) {
  final parts = fullName.trim().split(RegExp(r'\s+'));
  return parts.isNotEmpty ? parts.first : fullName;
}

class HomeTab extends StatelessWidget {
  final MockRepository repo;
  final InstitutionConfig institutionConfig;
  final WhatIfScenario whatIf;
  final VoidCallback onRefresh;
  final VoidCallback onOpenSimulation;
  final VoidCallback onOpenNotifications;

  const HomeTab({
    super.key,
    required this.repo,
    required this.institutionConfig,
    required this.whatIf,
    required this.onRefresh,
    required this.onOpenSimulation,
    required this.onOpenNotifications,
  });

  void _openSimulationModal(BuildContext context) {
    SimulationResultSheet.show(
      context,
      repo: repo,
      institutionConfig: institutionConfig,
      whatIf: whatIf,
      onOpenFullSimulation: onOpenSimulation,
    );
  }

  @override
  Widget build(BuildContext context) {
    final scale = MediaQuery.textScalerOf(context);
    final first = _firstName(repo.profile.name);
    final initials = first.isNotEmpty ? first[0].toUpperCase() : '?';
    final notifCount = repo.notifications.length;

    return RefreshIndicator(
      color: AppColors.primaryBlue,
      onRefresh: () async => onRefresh(),
      child: ListView(
        padding: FlLayout.pagePadding,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              CircleAvatar(
                radius: 20,
                backgroundColor: AppColors.primaryBlue,
                child: Text(
                  initials,
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Hello, $first',
                      style: TextStyle(
                        fontSize: scale.scale(23),
                        fontWeight: FontWeight.w700,
                        color: AppColors.textMain,
                        height: 1.2,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      'Track your progress toward the next rank.',
                      style: TextStyle(
                        fontSize: scale.scale(15),
                        color: AppColors.textMuted,
                        height: 1.35,
                      ),
                    ),
                  ],
                ),
              ),
              IconButton(
                constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
                tooltip: 'Notifications',
                onPressed: onOpenNotifications,
                icon: notifCount > 0
                    ? Badge(
                        label: Text('$notifCount'),
                        child: const Icon(Icons.notifications_outlined),
                      )
                    : const Icon(Icons.notifications_outlined),
              ),
            ],
          ),
          const SizedBox(height: FlLayout.homeSectionGap),
          HomeProgressOverview(
            repo: repo,
            institutionConfig: institutionConfig,
            whatIf: whatIf,
            onOpenSimulationModal: () => _openSimulationModal(context),
            onOpenPreparationDetails: () => Navigator.push(
              context,
              MaterialPageRoute(
                builder: (_) => PreparationPeriodScreen(period: institutionConfig.preparationPeriod),
              ),
            ),
          ),
          const SizedBox(height: FlLayout.homeSectionGap),
          HomeQuickActions(
            onAddDocument: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => UploadEvidenceScreen(repo: repo, onSave: onRefresh)),
            ),
            onOpenAssessment: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => AssessmentTab(repo: repo, onSave: onRefresh)),
            ),
            onViewFeedback: onOpenNotifications,
          ),
          const SizedBox(height: FlLayout.sectionGap),
          HomeKraGrid(
            repo: repo,
            onOpenAssessment: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => AssessmentTab(repo: repo, onSave: onRefresh)),
            ),
          ),
          const SizedBox(height: 20),
        ],
      ),
    );
  }
}
