import 'package:flutter/material.dart';

import '../theme/app_spacing.dart';
import '../theme/app_theme.dart';

class HomeQuickActions extends StatelessWidget {
  final VoidCallback onAddDocument;
  final VoidCallback onOpenAssessment;
  final VoidCallback onViewFeedback;

  const HomeQuickActions({
    super.key,
    required this.onAddDocument,
    required this.onOpenAssessment,
    required this.onViewFeedback,
  });

  @override
  Widget build(BuildContext context) {
    final scale = MediaQuery.textScalerOf(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const FlHomeSectionLabel('Quick actions'),
        LayoutBuilder(
          builder: (context, c) {
            final stack = c.maxWidth < 340 || scale.scale(1) > 1.15;
            final items = [
              _ActionTile(
                icon: Icons.note_add_outlined,
                color: AppColors.primaryBlue,
                label: 'Add Document',
                onTap: onAddDocument,
                scale: scale,
              ),
              _ActionTile(
                icon: Icons.fact_check_outlined,
                color: const Color(0xFF2D8C6E),
                label: 'My Assessment',
                onTap: onOpenAssessment,
                scale: scale,
              ),
              _ActionTile(
                icon: Icons.chat_bubble_outline,
                color: const Color(0xFFC97A16),
                label: 'View Feedback',
                onTap: onViewFeedback,
                scale: scale,
              ),
            ];
            if (stack) {
              return Column(
                children: items
                    .map((w) => Padding(padding: const EdgeInsets.only(bottom: 8), child: w))
                    .toList(),
              );
            }
            return Row(
              children: [
                for (var i = 0; i < items.length; i++)
                  Expanded(
                    child: Padding(
                      padding: EdgeInsets.only(right: i < items.length - 1 ? 8 : 0),
                      child: items[i],
                    ),
                  ),
              ],
            );
          },
        ),
      ],
    );
  }
}

class _ActionTile extends StatelessWidget {
  final IconData icon;
  final Color color;
  final String label;
  final VoidCallback onTap;
  final TextScaler scale;

  const _ActionTile({
    required this.icon,
    required this.color,
    required this.label,
    required this.onTap,
    required this.scale,
  });

  @override
  Widget build(BuildContext context) {
    return FlSurfaceCard(
      onTap: onTap,
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 10),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(icon, color: color, size: 22),
          ),
          const SizedBox(height: 6),
          Text(
            label,
            textAlign: TextAlign.center,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              fontSize: scale.scale(14),
              fontWeight: FontWeight.w600,
              color: AppColors.textMain,
              height: 1.2,
            ),
          ),
        ],
      ),
    );
  }
}
