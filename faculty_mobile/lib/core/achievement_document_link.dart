class AchievementDocumentLink {
  final String linkedAchievementId;
  final String? criterionId;
  final String? parentSubmissionStatus;
  final String? parentReviewStatus;
  final String? parentAchievementTitle;
  final String? achievementRemarks;

  const AchievementDocumentLink({
    required this.linkedAchievementId,
    this.criterionId,
    this.parentSubmissionStatus,
    this.parentReviewStatus,
    this.parentAchievementTitle,
    this.achievementRemarks,
  });

  factory AchievementDocumentLink.fromJson(Map<String, dynamic> j) => AchievementDocumentLink(
        linkedAchievementId: (j['linkedAchievementId'] ?? '').toString(),
        criterionId: j['criterionId'] as String?,
        parentSubmissionStatus: j['parentSubmissionStatus'] as String?,
        parentReviewStatus: j['parentReviewStatus'] as String?,
        parentAchievementTitle: j['parentAchievementTitle'] as String?,
        achievementRemarks: j['achievementRemarks'] as String?,
      );
}
