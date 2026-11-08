import 'package:flutter/material.dart';

import '../core/date_format.dart';
import '../core/evaluation_period_service.dart';
import '../models/institution_config.dart';
import '../theme/app_spacing.dart';
import '../theme/app_theme.dart';

class PreparationPeriodScreen extends StatelessWidget {
  final PreparationPeriod period;

  const PreparationPeriodScreen({super.key, required this.period});

  @override
  Widget build(BuildContext context) {
    final scale = MediaQuery.textScalerOf(context);
    final status = period.evaluationStatus();
    final reviewerLine = EvaluationPeriodService.reviewerScheduleLine(
      reviewerAvailableFrom: period.reviewerAvailableFrom,
    );

    return Scaffold(
      appBar: AppBar(title: const Text('Evaluation Period')),
      body: ListView(
        padding: FlLayout.pagePadding,
        children: [
          FlSurfaceCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Text('Status', style: TextStyle(fontWeight: FontWeight.w600)),
                    const Spacer(),
                    FlTextBadge(status),
                  ],
                ),
                const SizedBox(height: 14),
                _row('Start', formatFacultyDate(period.start), scale),
                _row('End', formatFacultyDate(period.end), scale),
                _row('Reviewer availability', reviewerLine, scale),
              ],
            ),
          ),
          const SizedBox(height: 12),
          FlSurfaceCard(
            child: Text(
              EvaluationPeriodService.facultyClosedHelper,
              style: TextStyle(fontSize: scale.scale(16), height: 1.5, color: AppColors.textMuted),
            ),
          ),
        ],
      ),
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
            child: Text(label, style: TextStyle(fontSize: scale.scale(15), color: AppColors.textMuted)),
          ),
          Expanded(
            child: Text(value, style: TextStyle(fontSize: scale.scale(17), fontWeight: FontWeight.w600)),
          ),
        ],
      ),
    );
  }
}
