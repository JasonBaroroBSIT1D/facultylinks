class FacultyNotification {
  final String id;
  final String title;
  final String body;
  final bool read;
  final String? at;
  final String? atManila;
  final String? eventType;
  final String? targetType;
  final String? targetDocumentPublicId;
  final String? targetAchievementId;
  final String? actorName;
  final String? documentFileName;
  final String? achievementTitle;
  final String? kraId;
  final String? criterionId;
  final String? indicatorId;
  final String? indicatorLabel;
  final bool navigable;

  const FacultyNotification({
    required this.id,
    required this.title,
    required this.body,
    this.read = false,
    this.at,
    this.atManila,
    this.eventType,
    this.targetType,
    this.targetDocumentPublicId,
    this.targetAchievementId,
    this.actorName,
    this.documentFileName,
    this.achievementTitle,
    this.kraId,
    this.criterionId,
    this.indicatorId,
    this.indicatorLabel,
    this.navigable = false,
  });

  factory FacultyNotification.fromJson(Map<String, dynamic> j) {
    return FacultyNotification(
      id: (j['id'] ?? '').toString(),
      title: (j['title'] ?? '').toString(),
      body: (j['body'] ?? '').toString(),
      read: j['read'] == true,
      at: j['at']?.toString(),
      atManila: j['atManila']?.toString(),
      eventType: j['eventType']?.toString(),
      targetType: j['targetType']?.toString(),
      targetDocumentPublicId: j['targetDocumentPublicId']?.toString(),
      targetAchievementId: j['targetAchievementId']?.toString(),
      actorName: j['actorName']?.toString(),
      documentFileName: j['documentFileName']?.toString(),
      achievementTitle: j['achievementTitle']?.toString(),
      kraId: j['kraId']?.toString(),
      criterionId: j['criterionId']?.toString(),
      indicatorId: j['indicatorId']?.toString(),
      indicatorLabel: j['indicatorLabel']?.toString(),
      navigable: j['navigable'] == true,
    );
  }

  String get subtitleLine {
    final parts = <String>[];
    if (documentFileName != null && documentFileName!.isNotEmpty) {
      parts.add(documentFileName!);
    } else if (achievementTitle != null && achievementTitle!.isNotEmpty) {
      parts.add(achievementTitle!);
    }
    if (indicatorLabel != null && indicatorLabel!.isNotEmpty) {
      parts.add(indicatorLabel!);
    } else if (indicatorId != null && indicatorId!.isNotEmpty) {
      parts.add(indicatorId!);
    }
    return parts.join(' · ');
  }
}