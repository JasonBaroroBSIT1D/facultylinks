import '../data/assessment_catalog.dart';
import '../models/rank_simulation.dart';
import '../repositories/mock_repository.dart';
import '../services/simulation_engine.dart';

/// Attention item kinds derived from saved documents / achievements / score notes.
enum AssessmentAttentionKind {
  needsChanges,
  pendingReview,
  processingFailed,
  incompleteRequirement,
}

class AssessmentAttentionItem {
  final AssessmentAttentionKind kind;
  final String title;
  final String detail;
  final String? documentId;
  final String? achievementId;
  final String? kraId;
  final String? criterionId;
  final String? indicatorId;

  const AssessmentAttentionItem({
    required this.kind,
    required this.title,
    required this.detail,
    this.documentId,
    this.achievementId,
    this.kraId,
    this.criterionId,
    this.indicatorId,
  });
}

/// Read-only overview built from persisted scores + achievements (no new formulas).
class AssessmentOverviewModel {
  final SimulationSnapshot estimated;
  final SimulationSnapshot? verified;
  final bool verifiedAvailable;
  final bool scoresWeighted;
  final List<Map<String, dynamic>> achievements;
  final String? achievementsError;
  final bool achievementsLoading;

  const AssessmentOverviewModel({
    required this.estimated,
    required this.verified,
    required this.verifiedAvailable,
    required this.scoresWeighted,
    required this.achievements,
    this.achievementsError,
    this.achievementsLoading = false,
  });

  static bool detectVerifiedAvailable(MockRepository repo, List<Map<String, dynamic>> achievements) {
    if (repo.rankSimulationJson != null) {
      final sim = FacultyRankSimulation.fromJson(repo.rankSimulationJson);
      return sim.verified.configured;
    }
    if (!repo.scoresConfigured || repo.facultyScoresVerified == null) return false;

    for (final a in achievements) {
      if (a['reviewerVerifiedPoints'] != null) return true;
    }
    final ca = repo.facultyScoresVerified?['byKra']?['kra-I']?['criterionA'] as Map<String, dynamic>?;
    if (ca != null &&
        ca['calculationUnavailable'] != true &&
        (ca['criterionAPoints'] != null || ca['partialSubtotal'] != null)) {
      return true;
    }
    if (repo.documents.any((d) => d.filterBucket == 'approved')) return true;
    return false;
  }

  static AssessmentOverviewModel fromRepo(
    MockRepository repo, {
    required List<Map<String, dynamic>> achievements,
    String? achievementsError,
    bool achievementsLoading = false,
  }) {
    final est = SimulationEngine.compute(repo);
    final verifiedAvailable = detectVerifiedAvailable(repo, achievements);
    final ver = verifiedAvailable ? SimulationEngine.compute(repo, verified: true) : null;
    return AssessmentOverviewModel(
      estimated: est,
      verified: ver,
      verifiedAvailable: verifiedAvailable,
      scoresWeighted: est.usesRankTableWeights || repo.scoresConfigured,
      achievements: achievements,
      achievementsError: achievementsError,
      achievementsLoading: achievementsLoading,
    );
  }

  KraBreakdownLine? kraLine(String kraId, {required bool verified}) {
    final snap = verified ? this.verified : estimated;
    if (snap == null) return null;
    return snap.kras.where((k) => k.kraId == kraId).firstOrNull;
  }

  int achievementCountForKra(String kraId) {
    final ids = <String>{};
    for (final a in achievements) {
      final id = a['id']?.toString();
      if (id == null || id.isEmpty) continue;
      final aKra = a['kraId']?.toString() ??
          tryKraIdFromIndicator(
            a['indicatorId']?.toString() ?? '',
            criterionId: a['criterionId']?.toString(),
          );
      if (aKra == kraId) ids.add(id);
    }
    return ids.length;
  }

  List<Map<String, dynamic>> achievementsForIndicator(String indicatorId) {
    return achievements.where((a) => a['indicatorId']?.toString() == indicatorId).toList();
  }

  List<AssessmentAttentionItem> attentionItems(MockRepository repo) {
    final items = <AssessmentAttentionItem>[];
    final seen = <String>{};

    void add(AssessmentAttentionItem item) {
      final key = '${item.kind.name}|${item.documentId}|${item.achievementId}|${item.title}|${item.detail}';
      if (seen.add(key)) items.add(item);
    }

    for (final d in repo.documents) {
      if (d.filterBucket == 'correction_requested' || d.displayStatus == 'achievement_needs_changes') {
        add(AssessmentAttentionItem(
          kind: AssessmentAttentionKind.needsChanges,
          title: d.displayStatusLabel ?? 'Changes requested',
          detail: (d.remarks?.trim().isNotEmpty == true)
              ? d.remarks!.trim()
              : d.fileName,
          documentId: d.id,
          achievementId: d.linkedAchievementId,
          kraId: d.kraId,
          criterionId: d.criterionId,
          indicatorId: d.indicatorId,
        ));
      } else if (d.ocrStatus == 'failed' || d.processingStatus == 'failed') {
        add(AssessmentAttentionItem(
          kind: AssessmentAttentionKind.processingFailed,
          title: 'Document processing failed',
          detail: d.fileName,
          documentId: d.id,
          kraId: d.kraId,
          criterionId: d.criterionId,
          indicatorId: d.indicatorId,
        ));
      } else if (d.countsAsPendingForFaculty) {
        add(AssessmentAttentionItem(
          kind: AssessmentAttentionKind.pendingReview,
          title: 'Pending review',
          detail: d.fileName,
          documentId: d.id,
          achievementId: d.linkedAchievementId,
          kraId: d.kraId,
          criterionId: d.criterionId,
          indicatorId: d.indicatorId,
        ));
      }
    }

    for (final a in achievements) {
      final rev = a['reviewStatus']?.toString() ?? '';
      final sub = a['submissionStatus']?.toString() ?? '';
      final id = a['id']?.toString();
      final title = a['title']?.toString() ?? 'Achievement';
      final remarks = a['reviewRemarks']?.toString().trim();
      if (rev == 'correction_requested') {
        add(AssessmentAttentionItem(
          kind: AssessmentAttentionKind.needsChanges,
          title: 'Achievement needs changes',
          detail: (remarks != null && remarks.isNotEmpty) ? '$title — $remarks' : title,
          achievementId: id,
          kraId: a['kraId']?.toString(),
          criterionId: a['criterionId']?.toString(),
          indicatorId: a['indicatorId']?.toString(),
        ));
      } else if (sub == 'submitted' && (rev.isEmpty || rev == 'pending' || rev == 'in_review')) {
        add(AssessmentAttentionItem(
          kind: AssessmentAttentionKind.pendingReview,
          title: 'Achievement pending review',
          detail: title,
          achievementId: id,
          kraId: a['kraId']?.toString(),
          criterionId: a['criterionId']?.toString(),
          indicatorId: a['indicatorId']?.toString(),
        ));
      }
    }

    // Only surface incomplete flags from the scoring service — not empty indicators.
    for (final line in estimated.kras) {
      if (line.rawIncomplete && line.incompleteReason != null && line.incompleteReason!.trim().isNotEmpty) {
        add(AssessmentAttentionItem(
          kind: AssessmentAttentionKind.incompleteRequirement,
          title: '${_kraShort(line.kraId)} needs attention',
          detail: line.incompleteReason!.trim(),
          kraId: line.kraId,
        ));
      }
    }

    for (final note in estimated.missingRequirements) {
      final t = note.trim();
      if (t.isEmpty) continue;
      final lower = t.toLowerCase();
      if (lower.contains('faculty self-assessment (estimated)')) continue;
      if (lower.contains('preparation only')) continue;
      if (lower.contains('what-if')) continue;
      // Keep explicit incomplete / policy notes from scoring service only.
      if (lower.contains('incomplete') ||
          lower.contains('required') ||
          lower.contains('provisional') ||
          lower.contains('unresolved') ||
          lower.contains('coverage')) {
        add(AssessmentAttentionItem(
          kind: AssessmentAttentionKind.incompleteRequirement,
          title: 'Assessment requirement',
          detail: t,
        ));
      }
    }

    return items;
  }

  static String _kraShort(String kraId) {
    switch (kraId) {
      case 'kra-I':
        return 'KRA I';
      case 'kra-II':
        return 'KRA II';
      case 'kra-III':
        return 'KRA III';
      case 'kra-IV':
        return 'KRA IV';
      default:
        return kraId;
    }
  }

  static String kraCode(String kraId) {
    switch (kraId) {
      case 'kra-I':
        return 'KRA I';
      case 'kra-II':
        return 'KRA II';
      case 'kra-III':
        return 'KRA III';
      case 'kra-IV':
        return 'KRA IV';
      default:
        return kraId;
    }
  }

  static String kraArea(String kraId) {
    switch (kraId) {
      case 'kra-I':
        return 'Instruction';
      case 'kra-II':
        return 'Research';
      case 'kra-III':
        return 'Extension';
      case 'kra-IV':
        return 'Professional Development';
      default:
        return kraId;
    }
  }

  /// Expandable details header — keep distinct from the compact summary cards.
  static String kraTitle(String kraId) => '${kraCode(kraId)} · ${kraArea(kraId)}';
}

String achievementStatusLabel(Map<String, dynamic> a) {
  final sub = (a['submissionStatus'] ?? '').toString();
  final rev = (a['reviewStatus'] ?? '').toString();
  if (sub == 'submitted' && rev == 'correction_requested') return 'Needs changes';
  if (rev == 'approved' || rev == 'verified') return 'Verified';
  if (rev == 'rejected') return 'Not accepted';
  if (sub == 'submitted') return 'Pending review';
  return 'Draft';
}
