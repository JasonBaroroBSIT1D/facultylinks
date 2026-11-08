import 'package:flutter/material.dart';

import '../core/date_format.dart';
import '../core/evaluation_period_service.dart';
import '../core/simulation_presenter.dart';
import '../core/ui_strings.dart';
import '../models/institution_config.dart';
import '../repositories/mock_repository.dart';
import '../services/simulation_engine.dart';
import '../theme/app_spacing.dart';
import '../theme/app_theme.dart';
import 'assigned_reviewer_card.dart';

/// Combined home card: rank simulation (blue) + preparation + reviewer (white).
class HomeProgressOverview extends StatelessWidget {
  final MockRepository repo;
  final InstitutionConfig institutionConfig;
  final WhatIfScenario whatIf;
  final VoidCallback onOpenSimulationModal;
  final VoidCallback onOpenPreparationDetails;

  const HomeProgressOverview({
    super.key,
    required this.repo,
    required this.institutionConfig,
    required this.whatIf,
    required this.onOpenSimulationModal,
    required this.onOpenPreparationDetails,
  });

  @override
  Widget build(BuildContext context) {
    final period = institutionConfig.preparationPeriod;

    return DecoratedBox(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(FlLayout.cardRadius),
        color: AppColors.cardWhite,
        border: Border.all(color: AppColors.border),
        boxShadow: [
          BoxShadow(
            color: AppColors.navyDeep.withValues(alpha: 0.07),
            blurRadius: 14,
            offset: const Offset(0, 5),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(FlLayout.cardRadius),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: [
            _SimulationUpperSection(
              repo: repo,
              institutionConfig: institutionConfig,
              whatIf: whatIf,
              onViewSimulation: onOpenSimulationModal,
            ),
            const Divider(height: 1, thickness: 1, color: AppColors.border),
            _PreparationOverviewRow(
              period: period,
              onDetails: onOpenPreparationDetails,
            ),
            const Divider(height: 1, thickness: 1, indent: 56, color: AppColors.border),
            _ReviewerOverviewRow(profile: repo.profile),
          ],
        ),
      ),
    );
  }
}

class _SimulationUpperSection extends StatelessWidget {
  final MockRepository repo;
  final InstitutionConfig institutionConfig;
  final WhatIfScenario whatIf;
  final VoidCallback onViewSimulation;

  const _SimulationUpperSection({
    required this.repo,
    required this.institutionConfig,
    required this.whatIf,
    required this.onViewSimulation,
  });

  @override
  Widget build(BuildContext context) {
    final snapshot = SimulationEngine.compute(repo, whatIf: whatIf);
    final target = SimulationEngine.nextRankOption(institutionConfig, repo.profile.rank);
    final eval = SimulationEngine.evaluateTarget(
      cfg: institutionConfig,
      targetRank: target,
      weightedTotal: snapshot.weightedTotal,
    );
    final potential = SimulationPresenter.potentialRankLabel(eval, institutionConfig);
    final rulesNote = SimulationPresenter.rankRulesNotice(institutionConfig);
    final scale = MediaQuery.textScalerOf(context);
    final width = MediaQuery.sizeOf(context).width;
    final twoCol = width >= 340 && scale.scale(1) <= 1.25;

    final pointsColumn = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          UiStrings.estimatedPoints,
          style: TextStyle(
            color: Colors.white.withValues(alpha: 0.9),
            fontSize: scale.scale(14),
            fontWeight: FontWeight.w500,
          ),
        ),
        const SizedBox(height: 4),
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
        _rankLine('Current rank', repo.profile.rank, scale),
        const SizedBox(height: 8),
        _rankLine('Potential rank', potential, scale),
        if (rulesNote != null) ...[
          const SizedBox(height: 8),
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

    return Stack(
      children: [
        Positioned.fill(
          child: DecoratedBox(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [
                  AppColors.primaryBlue,
                  AppColors.navyDeep,
                ],
              ),
            ),
          ),
        ),
        Positioned(
          right: -8,
          top: -12,
          child: Opacity(
            opacity: 0.14,
            child: CustomPaint(
              size: const Size(88, 88),
              painter: _AcademicMotifPainter(),
            ),
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                children: [
                  Container(
                    width: 36,
                    height: 36,
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.16),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(Icons.school_outlined, color: Colors.white, size: 22),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      'Rank Simulation',
                      style: TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w700,
                        fontSize: scale.scale(18),
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),
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
              const SizedBox(height: 14),
              FlYellowButton(
                label: 'View Simulation',
                onPressed: onViewSimulation,
                compact: true,
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _rankLine(String label, String value, TextScaler scale) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: TextStyle(
            color: Colors.white.withValues(alpha: 0.78),
            fontSize: scale.scale(12),
            fontWeight: FontWeight.w500,
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

class _PreparationOverviewRow extends StatelessWidget {
  final PreparationPeriod period;
  final VoidCallback onDetails;

  const _PreparationOverviewRow({required this.period, required this.onDetails});

  @override
  Widget build(BuildContext context) {
    final scale = MediaQuery.textScalerOf(context);
    final status = period.evaluationStatus();
    final closed = status == EvaluationPeriodService.statusClosed;
    final dateRange = '${formatFacultyDate(period.start)} – ${formatFacultyDate(period.end)}';

    return Material(
      color: AppColors.cardWhite,
      child: InkWell(
        onTap: onDetails,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(14, 12, 8, 12),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              _SoftIconCircle(icon: Icons.calendar_month_outlined),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            'Evaluation Period',
                            style: TextStyle(
                              fontWeight: FontWeight.w700,
                              fontSize: scale.scale(16),
                              color: AppColors.navyDeep,
                            ),
                          ),
                        ),
                        _PreparationStatusLabel(status: status),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text(
                      dateRange,
                      style: TextStyle(
                        fontSize: scale.scale(14),
                        fontWeight: FontWeight.w600,
                        color: AppColors.textMain,
                        height: 1.3,
                      ),
                    ),
                    if (closed) ...[
                      const SizedBox(height: 4),
                      Text(
                        EvaluationPeriodService.facultyClosedHelper,
                        style: TextStyle(
                          fontSize: scale.scale(13),
                          color: AppColors.textMuted,
                          height: 1.35,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              const Icon(Icons.chevron_right, color: AppColors.textMuted, size: 26),
            ],
          ),
        ),
      ),
    );
  }
}

class _ReviewerOverviewRow extends StatelessWidget {
  final FacultyProfile profile;

  const _ReviewerOverviewRow({required this.profile});

  @override
  Widget build(BuildContext context) {
    final scale = MediaQuery.textScalerOf(context);
    final assigned = facultyHasReviewer(profile);
    final name = assigned ? profile.reviewerName : 'No reviewer assigned yet';

    final initials = assigned
        ? profile.reviewerName
            .split(' ')
            .where((p) => p.isNotEmpty)
            .take(2)
            .map((p) => p[0])
            .join()
            .toUpperCase()
        : '?';

    final body = Padding(
      padding: EdgeInsets.fromLTRB(14, 12, assigned ? 8 : 14, 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          if (assigned)
            CircleAvatar(
              radius: 18,
              backgroundColor: AppColors.primarySoft,
              child: Text(
                initials,
                style: const TextStyle(
                  color: AppColors.navyDeep,
                  fontWeight: FontWeight.bold,
                  fontSize: 13,
                ),
              ),
            )
          else
            _SoftIconCircle(icon: Icons.person_outline),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Your Reviewer',
                  style: TextStyle(
                    fontSize: scale.scale(13),
                    fontWeight: FontWeight.w600,
                    color: AppColors.textMuted,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  name,
                  style: TextStyle(
                    fontSize: scale.scale(16),
                    fontWeight: FontWeight.w700,
                    color: AppColors.navyDeep,
                    height: 1.25,
                  ),
                ),
              ],
            ),
          ),
          if (assigned) const Icon(Icons.chevron_right, color: AppColors.textMuted, size: 26),
        ],
      ),
    );

    if (!assigned) {
      return Material(color: AppColors.cardWhite, child: body);
    }

    return Material(
      color: AppColors.cardWhite,
      child: InkWell(
        onTap: () => AssignedReviewerDetailsSheet.show(context, profile),
        child: body,
      ),
    );
  }
}

class _SoftIconCircle extends StatelessWidget {
  final IconData icon;
  const _SoftIconCircle({required this.icon});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 40,
      height: 40,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: AppColors.primarySoft,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Icon(icon, color: AppColors.primaryBlue, size: 22),
    );
  }
}

class _PreparationStatusLabel extends StatelessWidget {
  final String status;
  const _PreparationStatusLabel({required this.status});

  @override
  Widget build(BuildContext context) {
    Color bg;
    switch (status) {
      case 'Open':
        bg = AppColors.primarySoft;
        break;
      case 'Upcoming':
        bg = AppColors.yellowSoft;
        break;
      case 'Closed':
      default:
        bg = AppColors.border.withValues(alpha: 0.35);
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.border),
      ),
      child: Text(
        status,
        style: const TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w700,
          color: AppColors.textMain,
        ),
      ),
    );
  }
}

class _AcademicMotifPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = Colors.white
      ..strokeWidth = 2
      ..style = PaintingStyle.stroke;

    canvas.drawLine(Offset(size.width * 0.2, size.height * 0.85), Offset(size.width * 0.8, size.height * 0.85), paint);
    canvas.drawLine(Offset(size.width * 0.35, size.height * 0.55), Offset(size.width * 0.65, size.height * 0.55), paint);
    canvas.drawArc(
      Rect.fromCenter(center: Offset(size.width * 0.5, size.height * 0.42), width: size.width * 0.5, height: size.height * 0.35),
      3.4,
      2.8,
      false,
      paint,
    );
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
