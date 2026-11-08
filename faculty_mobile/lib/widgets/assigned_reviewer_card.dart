import 'package:flutter/material.dart';

import '../repositories/mock_repository.dart';
import '../theme/app_spacing.dart';
import '../theme/app_theme.dart';

bool facultyHasReviewer(FacultyProfile profile) {
  final name = profile.reviewerName.trim();
  if (name.isEmpty || name == '—') return false;
  final status = profile.reviewerAssignmentStatus.toLowerCase();
  return status != 'unassigned' && status != 'none';
}

void showAssignedReviewerDetails(BuildContext context, FacultyProfile profile) {
  AssignedReviewerDetailsSheet.show(context, profile);
}

class AssignedReviewerDetailsSheet {
  static void show(BuildContext context, FacultyProfile profile) {
    if (!facultyHasReviewer(profile)) return;
    final scale = MediaQuery.textScalerOf(context);

    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      backgroundColor: AppColors.cardWhite,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => Padding(
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Your Reviewer',
              style: TextStyle(fontSize: scale.scale(20), fontWeight: FontWeight.w700, color: AppColors.navyDeep),
            ),
            const SizedBox(height: 16),
            AssignedReviewerCard(profile: profile),
          ],
        ),
      ),
    );
  }
}

class AssignedReviewerCard extends StatelessWidget {
  final FacultyProfile profile;

  const AssignedReviewerCard({super.key, required this.profile});

  @override
  Widget build(BuildContext context) {
    final scale = MediaQuery.textScalerOf(context);
    final assigned = facultyHasReviewer(profile);

    if (!assigned) {
      return FlSurfaceCard(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Your Reviewer',
              style: TextStyle(fontSize: scale.scale(13), fontWeight: FontWeight.w600, color: AppColors.textMuted),
            ),
            const SizedBox(height: 6),
            Text(
              'No reviewer assigned yet.',
              style: TextStyle(fontSize: scale.scale(16), fontWeight: FontWeight.w700, color: AppColors.textMain),
            ),
            const SizedBox(height: 4),
            Text(
              'Your institution administrator can assign a reviewer.',
              style: TextStyle(fontSize: scale.scale(14), color: AppColors.textMuted, height: 1.4),
            ),
          ],
        ),
      );
    }

    final initials = profile.reviewerName
        .split(' ')
        .where((p) => p.isNotEmpty)
        .take(2)
        .map((p) => p[0])
        .join()
        .toUpperCase();

    return FlSurfaceCard(
      padding: const EdgeInsets.all(14),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
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
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Your Reviewer',
                  style: TextStyle(fontSize: scale.scale(13), fontWeight: FontWeight.w600, color: AppColors.textMuted),
                ),
                const SizedBox(height: 2),
                Text(
                  profile.reviewerName,
                  style: TextStyle(fontSize: scale.scale(17), fontWeight: FontWeight.w700, color: AppColors.textMain),
                ),
                if (profile.reviewerRole.trim().isNotEmpty) ...[
                  const SizedBox(height: 2),
                  Text(
                    profile.reviewerRole,
                    style: TextStyle(fontSize: scale.scale(14), color: AppColors.textMuted, height: 1.35),
                  ),
                ],
                const SizedBox(height: 6),
                FlTextBadge(profile.reviewerAssignmentStatus, compact: true),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
