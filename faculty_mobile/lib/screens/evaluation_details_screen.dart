import 'package:flutter/material.dart';

import '../core/date_format.dart';
import '../core/evaluation_period_service.dart';
import '../models/institution_config.dart';
import '../repositories/mock_repository.dart';
import '../theme/app_spacing.dart';
import '../theme/app_theme.dart';
import '../widgets/assigned_reviewer_card.dart';

/// Single faculty-facing page for evaluation schedule + assigned reviewer.
class EvaluationDetailsScreen extends StatelessWidget {
  static const routeName = '/evaluation-details';

  final PreparationPeriod period;
  final FacultyProfile profile;

  const EvaluationDetailsScreen({
    super.key,
    required this.period,
    required this.profile,
  });

  String _safeDate(DateTime? d) {
    if (d == null) return 'Not set';
    try {
      return formatFacultyDate(d);
    } catch (_) {
      return 'Not set';
    }
  }

  @override
  Widget build(BuildContext context) {
    final scale = MediaQuery.textScalerOf(context);
    final status = period.evaluationStatus();
    final reviewerLine = EvaluationPeriodService.reviewerScheduleLine(
      reviewerAvailableFrom: period.reviewerAvailableFrom,
    );
    final assigned = facultyHasReviewer(profile);

    return Scaffold(
      appBar: AppBar(title: const Text('Evaluation & reviewer')),
      body: ListView(
        padding: FlLayout.pagePadding,
        children: [
          FlSurfaceCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        'Evaluation schedule',
                        style: TextStyle(
                          fontSize: scale.scale(17),
                          fontWeight: FontWeight.w700,
                          color: AppColors.navyDeep,
                        ),
                      ),
                    ),
                    FlTextBadge(status),
                  ],
                ),
                const SizedBox(height: 14),
                _row('Start', _safeDate(period.start), scale),
                _row('End', _safeDate(period.end), scale),
                _row('Reviewer availability', reviewerLine, scale),
              ],
            ),
          ),
          const SizedBox(height: 12),
          FlSurfaceCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Assigned reviewer',
                  style: TextStyle(
                    fontSize: scale.scale(17),
                    fontWeight: FontWeight.w700,
                    color: AppColors.navyDeep,
                  ),
                ),
                const SizedBox(height: 12),
                if (!assigned) ...[
                  Text(
                    'No reviewer assigned yet',
                    style: TextStyle(
                      fontSize: scale.scale(16),
                      fontWeight: FontWeight.w700,
                      color: AppColors.textMain,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Your institution administrator can assign a reviewer.',
                    style: TextStyle(
                      fontSize: scale.scale(14),
                      color: AppColors.textMuted,
                      height: 1.4,
                    ),
                  ),
                ] else ...[
                  _reviewerIdentity(scale),
                  if (profile.reviewerRole.trim().isNotEmpty) ...[
                    const SizedBox(height: 10),
                    _row('Role', profile.reviewerRole.trim(), scale),
                  ],
                  if (profile.reviewerAssignmentStatus.trim().isNotEmpty) ...[
                    const SizedBox(height: 4),
                    _row('Assignment', profile.reviewerAssignmentStatus.trim(), scale),
                  ],
                ],
              ],
            ),
          ),
          const SizedBox(height: 12),
          FlSurfaceCard(
            child: Text(
              EvaluationPeriodService.facultyClosedHelper,
              style: TextStyle(
                fontSize: scale.scale(15),
                height: 1.45,
                color: AppColors.textMuted,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _reviewerIdentity(TextScaler scale) {
    final initials = profile.reviewerName
        .split(' ')
        .where((p) => p.isNotEmpty)
        .take(2)
        .map((p) => p[0])
        .join()
        .toUpperCase();

    return Row(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        CircleAvatar(
          radius: 22,
          backgroundColor: AppColors.navyDeep,
          child: Text(
            initials,
            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 15),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Text(
            profile.reviewerName.trim(),
            softWrap: true,
            style: TextStyle(
              fontSize: scale.scale(17),
              fontWeight: FontWeight.w700,
              color: AppColors.textMain,
              height: 1.3,
            ),
          ),
        ),
      ],
    );
  }

  Widget _row(String label, String value, TextScaler scale) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 140,
            child: Text(
              label,
              style: TextStyle(fontSize: scale.scale(15), color: AppColors.textMuted),
            ),
          ),
          Expanded(
            child: Text(
              value,
              softWrap: true,
              style: TextStyle(fontSize: scale.scale(16), fontWeight: FontWeight.w600, height: 1.35),
            ),
          ),
        ],
      ),
    );
  }
}
