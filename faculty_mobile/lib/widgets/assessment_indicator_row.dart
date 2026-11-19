import 'package:flutter/material.dart';

import '../data/assessment_catalog.dart';
import '../theme/app_theme.dart';

/// Shared navigable row used for assessment actions and indicators.
///
/// Matches Criterion A’s blue-leading / bold-title / chevron treatment so every
/// criterion across KRA I–IV looks consistent.
class AssessmentIndicatorRow extends StatelessWidget {
  final IconData icon;
  final String title;
  final String? supportingText;
  final VoidCallback onTap;
  final bool showDividerBelow;

  const AssessmentIndicatorRow({
    super.key,
    required this.icon,
    required this.title,
    this.supportingText,
    required this.onTap,
    this.showDividerBelow = false,
  });

  /// Indicator row with optional configured maximum points.
  factory AssessmentIndicatorRow.forIndicator({
    Key? key,
    required IndicatorNode indicator,
    required String kraId,
    required VoidCallback onTap,
    bool showDividerBelow = false,
  }) {
    final max = indicator.maxPoints;
    final supporting = max != null
        ? 'Maximum: ${_formatPoints(max)} ${_pointsWord(max)}'
        : null;
    return AssessmentIndicatorRow(
      key: key,
      icon: assessmentIndicatorIcon(indicator, kraId: kraId),
      title: indicator.name,
      supportingText: supporting,
      onTap: onTap,
      showDividerBelow: showDividerBelow,
    );
  }

  static String _formatPoints(double value) {
    if (value == value.roundToDouble()) return value.toInt().toString();
    return value.toStringAsFixed(2);
  }

  static String _pointsWord(double value) => value == 1 ? 'point' : 'points';

  @override
  Widget build(BuildContext context) {
    final scale = MediaQuery.textScalerOf(context);
    final titleSize = scale.scale(15).clamp(14.0, 18.0);
    final supportSize = scale.scale(13).clamp(12.0, 16.0);
    final iconBox = scale.scale(36).clamp(32.0, 40.0);
    final iconSize = scale.scale(20).clamp(18.0, 22.0);

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Material(
          color: Colors.transparent,
          child: InkWell(
            onTap: onTap,
            child: ConstrainedBox(
              constraints: const BoxConstraints(minHeight: 52),
              child: Padding(
                padding: const EdgeInsets.fromLTRB(12, 8, 8, 8),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    Container(
                      width: iconBox,
                      height: iconBox,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        color: AppColors.primarySoft,
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Icon(icon, color: AppColors.primaryBlue, size: iconSize),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            title,
                            softWrap: true,
                            style: TextStyle(
                              fontSize: titleSize,
                              fontWeight: FontWeight.w600,
                              color: AppColors.textMain,
                              height: 1.3,
                            ),
                          ),
                          if (supportingText != null && supportingText!.trim().isNotEmpty) ...[
                            const SizedBox(height: 2),
                            Text(
                              supportingText!,
                              softWrap: true,
                              style: TextStyle(
                                fontSize: supportSize,
                                fontWeight: FontWeight.w400,
                                color: AppColors.textMuted,
                                height: 1.35,
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                    const SizedBox(width: 4),
                    Icon(
                      Icons.chevron_right,
                      color: AppColors.textMuted,
                      size: scale.scale(22).clamp(20.0, 26.0),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
        if (showDividerBelow)
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 12),
            child: Divider(height: 1, thickness: 1, color: AppColors.border),
          ),
      ],
    );
  }
}

/// Picks a compact, relevant Material icon for an assessment indicator.
IconData assessmentIndicatorIcon(IndicatorNode indicator, {required String kraId}) {
  final name = indicator.name.toLowerCase();
  final type = (indicator.type ?? '').toLowerCase();

  if (type.contains('set_sef') || name == 'set' || name == 'sef' || name.contains('set & sef')) {
    return Icons.school_outlined;
  }
  if (name.contains('membership') || name.contains('prior academic')) {
    return Icons.card_membership_outlined;
  }
  if (name.contains('conference') || name.contains('presentation')) {
    return Icons.event_outlined;
  }
  if (name.contains('textbook') ||
      name.contains('academic book') ||
      name.contains('monograph') ||
      name.contains('manual') ||
      name.contains('module')) {
    return Icons.menu_book_outlined;
  }
  if (name.contains('chapter') || name.contains('article') || name.contains('journal')) {
    return Icons.article_outlined;
  }
  if (name.contains('multimedia') || name.contains('software')) {
    return Icons.devices_outlined;
  }
  if (name.contains('patent')) {
    return Icons.workspace_premium_outlined;
  }
  if (name.contains('cited') || name.contains('citation')) {
    return Icons.format_quote_outlined;
  }
  if (name.contains('translation') || name.contains('policy') || name.contains('product')) {
    return Icons.transform_outlined;
  }
  if (name.contains('musical') || name.contains('novel') || name.contains('poetry')) {
    return Icons.palette_outlined;
  }
  if (name.contains('mentorship') || name.contains('adviser') || name.contains('panel')) {
    return Icons.groups_outlined;
  }
  if (name.contains('program') || name.contains('designation')) {
    return Icons.badge_outlined;
  }
  if (name.contains('linkage') || name.contains('extension') || name.contains('client')) {
    return Icons.handshake_outlined;
  }
  if (name.contains('training') || name.contains('seminar') || name.contains('conference')) {
    return Icons.event_outlined;
  }
  if (name.contains('award') || name.contains('recognition')) {
    return Icons.emoji_events_outlined;
  }

  switch (kraId) {
    case 'kra-II':
      return Icons.science_outlined;
    case 'kra-III':
      return Icons.public_outlined;
    case 'kra-IV':
      return Icons.military_tech_outlined;
    default:
      return Icons.description_outlined;
  }
}
