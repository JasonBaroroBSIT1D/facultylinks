import 'package:flutter/material.dart';

import '../core/date_format.dart';
import '../core/evaluation_period_service.dart';
import '../models/institution_config.dart';
import '../theme/app_spacing.dart';
import '../theme/app_theme.dart';

class PreparationPeriodCard extends StatelessWidget {
  final PreparationPeriod period;
  final VoidCallback onDetails;

  const PreparationPeriodCard({super.key, required this.period, required this.onDetails});

  String _reviewerLine() => EvaluationPeriodService.reviewerScheduleLine(
        reviewerAvailableFrom: period.reviewerAvailableFrom,
      );

  @override
  Widget build(BuildContext context) {
    final status = period.evaluationStatus();
    final scale = MediaQuery.textScalerOf(context);
    final closed = status == EvaluationPeriodService.statusClosed;

    return FlSurfaceCard(
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(Icons.calendar_month_outlined, color: AppColors.primaryBlue, size: 22),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  'Evaluation Period',
                  style: TextStyle(
                    fontWeight: FontWeight.w700,
                    fontSize: scale.scale(17),
                    color: AppColors.textMain,
                  ),
                ),
              ),
              FlTextBadge(status, compact: true),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            '${formatFacultyDate(period.start)} – ${formatFacultyDate(period.end)}',
            style: TextStyle(fontSize: scale.scale(15), fontWeight: FontWeight.w600, color: AppColors.textMain),
          ),
          const SizedBox(height: 8),
          Text(
            _reviewerLine(),
            style: TextStyle(fontSize: scale.scale(14), color: AppColors.textMuted, height: 1.4),
          ),
          if (closed) ...[
            const SizedBox(height: 6),
            Text(
              EvaluationPeriodService.facultyClosedHelper,
              style: TextStyle(fontSize: scale.scale(14), color: AppColors.textMuted, height: 1.4),
            ),
          ],
          const SizedBox(height: 4),
          Align(
            alignment: Alignment.centerLeft,
            child: TextButton.icon(
              style: TextButton.styleFrom(
                minimumSize: const Size(48, 40),
                padding: const EdgeInsets.symmetric(horizontal: 4),
              ),
              onPressed: onDetails,
              icon: const Icon(Icons.event_note_outlined, size: 20),
              label: const Text('View Schedule'),
            ),
          ),
        ],
      ),
    );
  }

}
