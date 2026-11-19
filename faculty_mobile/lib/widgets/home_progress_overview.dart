import 'package:flutter/material.dart';

import '../core/simulation_presenter.dart';
import '../core/ui_strings.dart';
import '../models/institution_config.dart';
import '../repositories/mock_repository.dart';
import '../services/simulation_engine.dart';
import '../theme/app_spacing.dart';
import '../theme/app_theme.dart';

/// Combined home card: assessment outlook (blue) + evaluation & reviewer tile (white).
class HomeProgressOverview extends StatelessWidget {
  final MockRepository repo;
  final InstitutionConfig institutionConfig;
  final VoidCallback onOpenEvaluationDetails;
  /// Kept for older call sites; outlook opens via Home “My Assessment”.
  final VoidCallback? onOpenSimulationModal;

  const HomeProgressOverview({
    super.key,
    required this.repo,
    required this.institutionConfig,
    required this.onOpenEvaluationDetails,
    this.onOpenSimulationModal,
  });

  @override
  Widget build(BuildContext context) {
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
            ),
            const Divider(height: 1, thickness: 1, color: AppColors.border),
            _EvaluationDetailsTile(onOpen: onOpenEvaluationDetails),
          ],
        ),
      ),
    );
  }
}

class _SimulationUpperSection extends StatelessWidget {
  final MockRepository repo;
  final InstitutionConfig institutionConfig;

  const _SimulationUpperSection({
    required this.repo,
    required this.institutionConfig,
  });

  @override
  Widget build(BuildContext context) {
    final snapshot = SimulationEngine.compute(repo);
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
                      'Assessment outlook',
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
              const SizedBox(height: 6),
              Text(
                'Open My Assessment for full scores and rank details.',
                style: TextStyle(
                  color: Colors.white.withValues(alpha: 0.85),
                  fontSize: scale.scale(13),
                  height: 1.35,
                ),
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

class _EvaluationDetailsTile extends StatefulWidget {
  final VoidCallback onOpen;

  const _EvaluationDetailsTile({required this.onOpen});

  @override
  State<_EvaluationDetailsTile> createState() => _EvaluationDetailsTileState();
}

class _EvaluationDetailsTileState extends State<_EvaluationDetailsTile> {
  bool _opening = false;

  Future<void> _handleTap() async {
    if (_opening) return;
    setState(() => _opening = true);
    try {
      widget.onOpen();
      // Allow the push animation to start before accepting another tap.
      await Future<void>.delayed(const Duration(milliseconds: 400));
    } finally {
      if (mounted) setState(() => _opening = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final scale = MediaQuery.textScalerOf(context);

    return Material(
      color: AppColors.cardWhite,
      child: InkWell(
        onTap: _opening ? null : _handleTap,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(14, 12, 10, 12),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Container(
                width: 40,
                height: 40,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: AppColors.primarySoft,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(Icons.calendar_month_outlined, color: AppColors.primaryBlue, size: scale.scale(22)),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Evaluation & reviewer details',
                      softWrap: true,
                      style: TextStyle(
                        fontWeight: FontWeight.w700,
                        fontSize: scale.scale(15),
                        color: AppColors.navyDeep,
                        height: 1.25,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      'View your schedule and assigned reviewer',
                      softWrap: true,
                      style: TextStyle(
                        fontSize: scale.scale(13),
                        color: AppColors.textMuted,
                        height: 1.35,
                      ),
                    ),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right, color: AppColors.textMuted, size: 22),
            ],
          ),
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
