import 'package:flutter/material.dart';

import '../data/assessment_catalog.dart';
import '../models/faculty_notification.dart';
import '../repositories/mock_repository.dart';
import '../screens/document_detail_screen.dart';
import '../screens/kra_i_achievement_screen.dart';
import '../services/notification_api.dart';
import 'achievement_api.dart';

Future<void> openFacultyNotification(
  BuildContext context, {
  required FacultyNotification note,
  required MockRepository repo,
  required Future<void> Function() onRefresh,
}) async {
  if (!note.navigable) {
    if (!context.mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('This message has no linked record. Check your documents or assessment tab.')),
    );
    return;
  }
  try {
    await NotificationApi.markRead(note.id);
    repo.markNotificationReadLocal(note.id);
  } catch (_) {
    /* mark-read best effort */
  }

  if (note.targetType == 'document') {
    final id = note.targetDocumentPublicId;
    if (id == null) return;
    var doc = repo.documentById(id);
    if (doc == null) {
      await onRefresh();
      doc = repo.documentById(id);
    }
    if (!context.mounted) return;
    if (doc == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('That document is no longer available or you no longer have access.')),
      );
      return;
    }
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => DocumentDetailScreen(doc: doc!, repo: repo, onRefresh: onRefresh),
      ),
    );
    return;
  }

  if (note.targetType == 'achievement') {
    final achId = note.targetAchievementId;
    if (achId == null) return;
    Map<String, dynamic>? ach;
    try {
      ach = await AchievementApi.getOne(achId);
    } catch (_) {
      ach = null;
    }
    if (!context.mounted) return;
    if (ach == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('That achievement is no longer available.')),
      );
      return;
    }
    final kraId = note.kraId ?? ach['kraId']?.toString() ?? '';
    final criterionId = note.criterionId ?? ach['criterionId']?.toString() ?? '';
    final indicatorId = note.indicatorId ?? ach['indicatorId']?.toString() ?? '';
    final kra = repo.catalogKras.where((k) => k.id == kraId).firstOrNull;
    CriterionNode? criterion = kra?.criteria.where((c) => c.id == criterionId).firstOrNull;
    criterion ??= kra?.criteria
        .where((c) => c.indicators.any((i) => i.id == indicatorId))
        .firstOrNull;
    final indicator = criterion?.indicators.where((i) => i.id == indicatorId).firstOrNull;
    if (kra == null || criterion == null || indicator == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Could not resolve assessment context for this achievement.')),
      );
      return;
    }
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => KraIAchievementScreen(
          repo: repo,
          kraId: kra.id,
          criterion: criterion!,
          indicator: indicator,
          initialAchievementId: achId,
          onSave: onRefresh,
        ),
      ),
    );
  }
}