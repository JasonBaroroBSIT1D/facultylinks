import 'package:flutter/material.dart';

import '../core/ui_strings.dart';
import '../repositories/mock_repository.dart';
import '../theme/app_spacing.dart';
import '../theme/app_theme.dart';

class HomeNextSteps extends StatelessWidget {
  final MockRepository repo;
  final VoidCallback onAddDocument;
  final VoidCallback onOpenAssessment;
  final VoidCallback onOpenNotifications;

  const HomeNextSteps({
    super.key,
    required this.repo,
    required this.onAddDocument,
    required this.onOpenAssessment,
    required this.onOpenNotifications,
  });

  String? _priorityTitle() {
    if (repo.documents.isEmpty) return 'Add your first document';
    final correction = repo.documents.where((d) => d.reviewStatus == 'correction_requested').length;
    if (correction > 0) return 'Review requested changes';
    final pending = repo.documents.where((d) => d.reviewStatus == 'pending').length;
    if (pending > 0) return 'Check review status';
    return null;
  }

  VoidCallback? _priorityAction(VoidCallback onAddDocument, VoidCallback onOpenNotifications) {
    if (repo.documents.isEmpty) return onAddDocument;
    final correction = repo.documents.any((d) => d.reviewStatus == 'correction_requested');
    if (correction) return onOpenNotifications;
    final pending = repo.documents.any((d) => d.reviewStatus == 'pending');
    if (pending) return onOpenNotifications;
    return null;
  }

  @override
  Widget build(BuildContext context) {
    final scale = MediaQuery.textScalerOf(context);
    final priority = _priorityTitle();
    final priorityTap = _priorityAction(onAddDocument, onOpenNotifications);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        FlSectionTitle('What would you like to do?'),
        if (priority != null && priorityTap != null)
          Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: FlSurfaceCard(
              onTap: priorityTap,
              child: Row(
                children: [
                  Icon(Icons.flag_outlined, color: AppColors.primaryBlue),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      priority,
                      style: TextStyle(fontSize: scale.scale(17), fontWeight: FontWeight.w700, color: AppColors.textNavy),
                    ),
                  ),
                  const Icon(Icons.chevron_right, color: AppColors.textMuted),
                ],
              ),
            ),
          ),
        _shortcut(
          context,
          icon: Icons.note_add_outlined,
          label: 'Add Document',
          hint: 'Upload proof for your assessment',
          onTap: onAddDocument,
        ),
        const SizedBox(height: 10),
        _shortcut(
          context,
          icon: Icons.fact_check_outlined,
          label: 'View My Assessment',
          hint: 'Update points for each KRA',
          onTap: onOpenAssessment,
        ),
        const SizedBox(height: 10),
        _shortcut(
          context,
          icon: Icons.feedback_outlined,
          label: 'Check Feedback',
          hint: repo.notifications.isEmpty ? 'No new messages yet' : UiStrings.docStatusLabel('correction_requested'),
          onTap: onOpenNotifications,
        ),
      ],
    );
  }

  Widget _shortcut(
    BuildContext context, {
    required IconData icon,
    required String label,
    required String hint,
    required VoidCallback onTap,
  }) {
    final scale = MediaQuery.textScalerOf(context);
    return FlSurfaceCard(
      onTap: onTap,
      child: Row(
        children: [
          CircleAvatar(
            radius: 24,
            backgroundColor: AppColors.primarySoft,
            child: Icon(icon, color: AppColors.primaryBlue),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: TextStyle(fontSize: scale.scale(17), fontWeight: FontWeight.w700, color: AppColors.textNavy),
                ),
                const SizedBox(height: 2),
                Text(
                  hint,
                  style: TextStyle(fontSize: scale.scale(15), color: AppColors.textMuted, height: 1.35),
                ),
              ],
            ),
          ),
          const Icon(Icons.chevron_right, color: AppColors.textMuted),
        ],
      ),
    );
  }
}
