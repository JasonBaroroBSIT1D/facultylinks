import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import '../data/assessment_catalog.dart';
import '../services/api_client.dart';
import '../core/achievement_document_link.dart';
import '../services/document_api.dart';
import '../services/faculty_refresh.dart';
import '../services/simulation_engine.dart';

class FacultyProfile {
  String id;
  String name;
  String email;
  String rank;
  String reviewerName;
  String reviewerRole;
  String reviewerAssignmentStatus;
  FacultyProfile({
    required this.id,
    required this.name,
    required this.email,
    required this.rank,
    required this.reviewerName,
    this.reviewerRole = 'Assigned Evaluator',
    this.reviewerAssignmentStatus = 'Active',
  });
}

class AssessmentEntry {
  String id;
  String indicatorId;
  String title;
  String? date;
  String? role;
  int? contributionPercent;
  double estimatedPoints;
  double? verifiedPoints;
  String reviewStatus;
  String? academicYear;
  String? semester;
  double? rating;

  AssessmentEntry({
    required this.id,
    required this.indicatorId,
    required this.title,
    this.date,
    this.role,
    this.contributionPercent,
    this.estimatedPoints = 0,
    this.verifiedPoints,
    this.reviewStatus = 'draft',
    this.academicYear,
    this.semester,
    this.rating,
  });

  Map<String, dynamic> toJson() => {
        'id': id,
        'indicatorId': indicatorId,
        'title': title,
        'date': date,
        'role': role,
        'contributionPercent': contributionPercent,
        'estimatedPoints': estimatedPoints,
        'verifiedPoints': verifiedPoints,
        'reviewStatus': reviewStatus,
        'academicYear': academicYear,
        'semester': semester,
        'rating': rating,
      };

  factory AssessmentEntry.fromJson(Map<String, dynamic> j) => AssessmentEntry(
        id: j['id'].toString(),
        indicatorId: j['indicatorId'],
        title: j['title'] ?? '',
        date: j['date'],
        role: j['role'],
        contributionPercent: j['contributionPercent'],
        estimatedPoints: (j['estimatedPoints'] as num?)?.toDouble() ?? 0,
        verifiedPoints: (j['verifiedPoints'] as num?)?.toDouble(),
        reviewStatus: j['reviewStatus'] ?? 'draft',
        academicYear: j['academicYear'],
        semester: j['semester'],
        rating: (j['rating'] as num?)?.toDouble(),
      );
}

class FacultyDocument {
  String id;
  String indicatorId;
  String kraId;
  String fileName;
  String reviewStatus;
  String? remarks;
  String ocrText;
  String? folder;
  String? academicYear;
  String? semester;
  String? mimeType;
  String? createdAt;
  String ocrStatus;
  String processingStatus;
  String? processingError;
  String? documentKind;
  int? sizeBytes;
  String? displayStatus;
  String? displayStatusLabel;
  String? linkedAchievementId;
  String? criterionId;
  String? parentReviewStatus;
  String? parentSubmissionStatus;
  String? parentAchievementTitle;
  List<AchievementDocumentLink> achievementLinks;

  FacultyDocument({
    required this.id,
    required this.indicatorId,
    required this.kraId,
    required this.fileName,
    this.reviewStatus = 'pending',
    this.remarks,
    this.ocrText = '',
    this.folder,
    this.academicYear,
    this.semester,
    this.mimeType,
    this.createdAt,
    this.ocrStatus = 'pending',
    this.processingStatus = 'none',
    this.processingError,
    this.documentKind,
    this.sizeBytes,
    this.displayStatus,
    this.displayStatusLabel,
    this.linkedAchievementId,
    this.criterionId,
    this.parentReviewStatus,
    this.parentSubmissionStatus,
    this.parentAchievementTitle,
    this.achievementLinks = const [],
  });

  bool get isAchievementEvidence {
    final ind = indicatorId;
    return ind.startsWith('kra-I-B') ||
        ind.startsWith('kra-I-C') ||
        ind.startsWith('kra-II-') ||
        ind.startsWith('kra-III-');
  }

  /// Bucket for My Documents filters (maps achievement display to legacy keys).
  String get filterBucket {
    switch (displayStatus) {
      case 'part_of_approved_achievement':
        return 'approved';
      case 'pending_achievement_review':
        return 'pending';
      case 'achievement_needs_changes':
        return 'correction_requested';
      case 'part_of_rejected_achievement':
        return 'rejected';
      case 'draft_evidence':
        return 'draft';
      default:
        return reviewStatus;
    }
  }

  bool get countsAsPendingForFaculty {
    if (displayStatus == 'part_of_approved_achievement') return false;
    if (displayStatus == 'part_of_rejected_achievement') return false;
    if (displayStatus == 'draft_evidence') return false;
    if (filterBucket == 'pending' || filterBucket == 'correction_requested') return true;
    return reviewStatus == 'pending' || reviewStatus == 'correction_requested';
  }

  bool get isSetSefOcr {
    const kinds = {'set_sef_unified', 'set_sef_combined', 'set_sef_set_only', 'set_sef_sef_only'};
    const indicators = {
      'kra-I-A-setsef-eval',
      'kra-I-A-setsef-combined',
      'kra-I-A-set-pdf',
      'kra-I-A-sef-pdf',
    };
    return kinds.contains(documentKind) || indicators.contains(indicatorId);
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'indicatorId': indicatorId,
        'kraId': kraId,
        'fileName': fileName,
        'reviewStatus': reviewStatus,
        'remarks': remarks,
        'ocrText': ocrText,
        'folder': folder,
        'academicYear': academicYear,
        'semester': semester,
        'mimeType': mimeType,
        'createdAt': createdAt,
        'ocrStatus': ocrStatus,
        'processingStatus': processingStatus,
        'processingError': processingError,
        'documentKind': documentKind,
        'displayStatus': displayStatus,
        'displayStatusLabel': displayStatusLabel,
        'linkedAchievementId': linkedAchievementId,
        'criterionId': criterionId,
        'parentReviewStatus': parentReviewStatus,
        'parentSubmissionStatus': parentSubmissionStatus,
        'parentAchievementTitle': parentAchievementTitle,
        'achievementLinks': achievementLinks.map((l) => {
              'linkedAchievementId': l.linkedAchievementId,
              'criterionId': l.criterionId,
              'parentSubmissionStatus': l.parentSubmissionStatus,
              'parentReviewStatus': l.parentReviewStatus,
              'parentAchievementTitle': l.parentAchievementTitle,
              'achievementRemarks': l.achievementRemarks,
            }).toList(),
      };

  factory FacultyDocument.fromJson(Map<String, dynamic> j) => FacultyDocument(
        id: j['id'] as String,
        indicatorId: j['indicatorId'] as String? ?? '',
        kraId: j['kraId'] as String? ?? '',
        fileName: j['fileName'] as String? ?? j['filename'] as String? ?? '',
        reviewStatus: j['reviewStatus'] as String? ?? 'pending',
        remarks: (j['remarks'] as String?)?.isNotEmpty == true ? j['remarks'] as String : null,
        ocrText: j['ocrText'] as String? ?? '',
        folder: j['folder'] as String?,
        academicYear: j['academicYear'] as String?,
        semester: j['semester'] as String?,
        mimeType: j['mimeType'] as String?,
        createdAt: j['createdAt'] as String?,
        ocrStatus: j['ocrStatus'] as String? ?? 'pending',
        processingStatus: j['processingStatus'] as String? ?? 'none',
        processingError: (j['processingError'] as String?)?.isNotEmpty == true ? j['processingError'] as String : null,
        documentKind: j['documentKind'] as String?,
        sizeBytes: (j['sizeBytes'] as num?)?.toInt(),
        displayStatus: j['displayStatus'] as String?,
        displayStatusLabel: j['displayStatusLabel'] as String?,
        linkedAchievementId: j['linkedAchievementId'] as String?,
        criterionId: j['criterionId'] as String?,
        parentReviewStatus: j['parentReviewStatus'] as String?,
        parentSubmissionStatus: j['parentSubmissionStatus'] as String?,
        parentAchievementTitle: j['parentAchievementTitle'] as String?,
        achievementLinks: (j['achievementLinks'] as List<dynamic>? ?? [])
            .map((e) => AchievementDocumentLink.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}

class FacultyRefreshResult {
  final bool applied;
  final String? errorMessage;

  const FacultyRefreshResult({required this.applied, this.errorMessage});
}

/// Faculty data loaded from the Flask API (legacy class name retained for screens).
class MockRepository {
  static const _legacyDemoKey = 'facultylink_mobile_state_v1';
  static String? _userScope;

  FacultyProfile profile = FacultyProfile(
    id: '',
    name: '',
    email: '',
    rank: '',
    reviewerName: '',
  );

  List<double?> setRatings = List.filled(6, null);
  List<double?> sefRatings = List.filled(6, null);
  List<String> academicYears = ['2024-2025', '2025-2026'];
  List<AssessmentEntry> entries = [];
  List<FacultyDocument> documents = [];
  List<Map<String, String>> notifications = [];
  String? loadError;
  String? syncError;
  String? configVersionId;

  /// Published scoring catalog from the API (fallback: [assessmentKras]).
  List<KraNode> catalogKras = assessmentKras;

  bool scoresConfigured = false;
  /// True when [catalogKras] was populated from `/api/faculty/config/catalog`.
  bool catalogLoadedFromApi = false;
  Map<String, dynamic>? facultyScoresEstimated;
  Map<String, dynamic>? facultyScoresVerified;
  Map<String, dynamic>? kraWeightsFromApi;
  Map<String, dynamic>? rankSimulationJson;

  Map<String, dynamic>? _criterionAFromScores(bool verified) {
    final mode = verified ? facultyScoresVerified : facultyScoresEstimated;
    final kraI = mode?['byKra']?['kra-I'] as Map<String, dynamic>?;
    return kraI?['criterionA'] as Map<String, dynamic>?;
  }

  String criterionAEstimatedLine() {
    final ca = _criterionAFromScores(false);
    if (ca != null) return formatCriterionALine(ca, prefix: 'Estimated');
    return '';
  }

  String criterionAVerifiedLine() {
    final ca = _criterionAFromScores(true);
    if (ca != null) return formatCriterionALine(ca, prefix: 'Reviewer-verified');
    return '';
  }

  static String formatCriterionALine(Map<String, dynamic>? ca, {String? prefix}) {
    if (ca == null) return prefix != null ? '$prefix: Not available yet' : 'Not available yet';
    final body = _formatCaLineBody(ca);
    if (prefix == null || prefix.isEmpty) return body;
    return '$prefix: $body';
  }

  static String _formatCaLineBody(Map<String, dynamic> ca) {
    final max = (ca['maxima']?['criterionA'] as num?)?.toDouble() ?? 60.0;
    final maxSlots = ca['maxSemesterSlots'] ?? ca['requiredSlots'] ?? 6;
    final setN = ca['setCount'] ?? 0;
    final sefN = ca['sefCount'] ?? 0;
    final slots = 'SET: $setN/$maxSlots · SEF: $sefN/$maxSlots';
    if (ca['calculationUnavailable'] == true) {
      return 'Unavailable — ${ca['incompleteReason'] ?? 'No eligible ratings.'}';
    }
  var pts = ca['criterionAPoints'] as num?;
    if (pts == null) pts = ca['partialSubtotal'] as num?;
    if (pts == null) {
      final sp = ca['setPoints'];
      final sefp = ca['sefPoints'];
      if (sp != null || sefp != null) {
        final partial = (sp as num? ?? 0) + (sefp as num? ?? 0);
        return 'Partial ${partial.toStringAsFixed(2)} / $max ($slots)';
      }
      return 'Not available yet';
    }
    final coverage = ca['incomplete'] == true
        ? ' · ${ca['coverageNote'] ?? 'Based on available semesters; may change as ratings are added.'}'
        : '';
    return '${pts.toStringAsFixed(2)} / $max ($slots)$coverage';
  }

  bool get hasActiveDocumentProcessing => documents.any(
        (d) =>
            d.processingStatus == 'queued' ||
            d.processingStatus == 'processing' ||
            d.processingStatus == 'pending' ||
            d.ocrStatus == 'queued' ||
            d.ocrStatus == 'processing',
      );

  FacultyDocument? documentById(String id) {
    for (final d in documents) {
      if (d.id == id) return d;
    }
    return null;
  }

  static Future<void> clearUserScope() async {
    _userScope = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_legacyDemoKey);
  }

  static Future<MockRepository> load() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_legacyDemoKey);

    final repo = MockRepository();
    final result = await repo.refreshFromApi(scopes: FacultyRefreshScopes.all, expectedGeneration: 1);
    if (!result.applied && result.errorMessage != null) {
      repo.loadError = result.errorMessage;
    }
    if (repo.profile.email.isNotEmpty) {
      _userScope = repo.profile.email;
    }
    return repo;
  }

  Future<FacultyRefreshResult> refreshFromApi({
    required Set<FacultyRefreshScope> scopes,
    required int expectedGeneration,
  }) async {
    final errors = <String>[];
    var appliedAny = false;
    final scopeEmail = _userScope;

    try {
      if (scopes.contains(FacultyRefreshScope.profile)) {
        final ok = await _fetchProfile();
        if (ok == _FetchOutcome.applied) appliedAny = true;
        if (ok == _FetchOutcome.failed) errors.add('Profile');
      }
      if (scopes.contains(FacultyRefreshScope.assessment)) {
        final ok = await _fetchAssessment();
        if (ok == _FetchOutcome.applied) appliedAny = true;
        if (ok == _FetchOutcome.failed) errors.add('Assessment');
      }
      if (scopes.contains(FacultyRefreshScope.catalog)) {
        final ok = await _fetchCatalog();
        if (ok == _FetchOutcome.applied) appliedAny = true;
        if (ok == _FetchOutcome.failed) errors.add('Configuration');
      }
      if (scopes.contains(FacultyRefreshScope.scores)) {
        final ok = await _fetchScores();
        if (ok == _FetchOutcome.applied) appliedAny = true;
        if (ok == _FetchOutcome.failed) errors.add('Scores');
      }
      if (scopes.contains(FacultyRefreshScope.documents)) {
        final ok = await _fetchDocuments();
        if (ok == _FetchOutcome.applied) appliedAny = true;
        if (ok == _FetchOutcome.failed) errors.add('Documents');
      }
      if (scopes.contains(FacultyRefreshScope.notifications)) {
        final ok = await _fetchNotifications();
        if (ok == _FetchOutcome.applied) appliedAny = true;
        if (ok == _FetchOutcome.failed) errors.add('Notifications');
      }

      if (scopeEmail != null && _userScope != null && scopeEmail != _userScope) {
        return const FacultyRefreshResult(applied: false);
      }

      if (errors.isEmpty) {
        syncError = null;
        return FacultyRefreshResult(applied: appliedAny);
      }
      if (appliedAny) {
        return FacultyRefreshResult(
          applied: true,
          errorMessage: 'Some data could not be refreshed (${errors.join(', ')}).',
        );
      }
      return FacultyRefreshResult(
        applied: false,
        errorMessage: 'Could not refresh (${errors.join(', ')}). Showing last saved data.',
      );
    } catch (e) {
      return FacultyRefreshResult(
        applied: false,
        errorMessage: e.toString().replaceFirst('Exception: ', ''),
      );
    }
  }

  Future<_FetchOutcome> _fetchProfile() async {
    final meRes = await ApiClient.get('/api/faculty/me');
    if (meRes.statusCode != 200) return _FetchOutcome.failed;
    final me = jsonDecode(meRes.body) as Map<String, dynamic>;
    final p = me['profile'] as Map<String, dynamic>;
    final nextEmail = (p['email'] as String?) ?? '';
    if (_userScope != null && nextEmail.isNotEmpty && _userScope != nextEmail) {
      return _FetchOutcome.failed;
    }
    profile = FacultyProfile(
      id: p['id'],
      name: p['name'],
      email: nextEmail,
      rank: p['rank'] ?? '',
      reviewerName: p['reviewerName'] ?? '',
      reviewerRole: p['reviewerRole'] ?? 'Assigned Evaluator',
      reviewerAssignmentStatus: p['reviewerAssignmentStatus'] ?? 'Unassigned',
    );
    if (nextEmail.isNotEmpty) _userScope = nextEmail;
    return _FetchOutcome.applied;
  }

  Future<_FetchOutcome> _fetchAssessment() async {
    final assessRes = await ApiClient.get('/api/faculty/assessment');
    if (assessRes.statusCode != 200) return _FetchOutcome.failed;
    final data = jsonDecode(assessRes.body) as Map<String, dynamic>;
    final assessment = data['assessment'] as Map<String, dynamic>? ?? {};
    configVersionId = assessment['configVersionId'] as String?;
    final setSef = assessment['setSef'] as Map<String, dynamic>? ?? {};
    setRatings = (setSef['SET'] as List<dynamic>? ?? []).map((e) => e == null ? null : (e as num).toDouble()).toList();
    sefRatings = (setSef['SEF'] as List<dynamic>? ?? []).map((e) => e == null ? null : (e as num).toDouble()).toList();
    if (setRatings.length < 6) {
      setRatings = [...setRatings, ...List.filled(6 - setRatings.length, null)];
    }
    if (sefRatings.length < 6) {
      sefRatings = [...sefRatings, ...List.filled(6 - sefRatings.length, null)];
    }
    final rawEntries = assessment['entries'] as Map<String, dynamic>? ?? {};
    final nextEntries = <AssessmentEntry>[];
    rawEntries.forEach((_, list) {
      for (final e in (list as List<dynamic>)) {
        nextEntries.add(AssessmentEntry.fromJson(e as Map<String, dynamic>));
      }
    });
    entries = nextEntries;
    return _FetchOutcome.applied;
  }

  Future<_FetchOutcome> _fetchCatalog() async {
    final catRes = await ApiClient.get('/api/faculty/config/catalog');
    if (catRes.statusCode != 200) return _FetchOutcome.failed;
    final catData = jsonDecode(catRes.body) as Map<String, dynamic>;
    final catalog = catData['catalog'];
    if (catalog is Map<String, dynamic> && (catalog['kras'] as List?)?.isNotEmpty == true) {
      catalogKras = parsePublishedCatalog(catalog);
      catalogLoadedFromApi = true;
    } else {
      catalogLoadedFromApi = false;
    }
    final weights = catData['kraWeights'];
    if (weights is Map<String, dynamic>) {
      kraWeightsFromApi = weights;
    }
    return _FetchOutcome.applied;
  }

  Future<_FetchOutcome> _fetchScores() async {
    final scoresRes = await ApiClient.get('/api/faculty/scores');
    if (scoresRes.statusCode != 200) return _FetchOutcome.failed;
    final scoresData = jsonDecode(scoresRes.body) as Map<String, dynamic>;
    configVersionId ??= scoresData['configVersionId'] as String?;
    final configured = scoresData['configured'] == true;
    final scores = scoresData['scores'] as Map<String, dynamic>?;
    if (configured && scores != null) {
      scoresConfigured = true;
      facultyScoresEstimated = scores['estimated'] as Map<String, dynamic>?;
      facultyScoresVerified = scores['verified'] as Map<String, dynamic>?;
      rankSimulationJson = scoresData['rankSimulation'] as Map<String, dynamic>?;
    } else if (!configured) {
      scoresConfigured = false;
      rankSimulationJson = null;
    }
    return _FetchOutcome.applied;
  }

  Future<_FetchOutcome> _fetchDocuments() async {
    try {
      final docList = await DocumentApi.listMine();
      documents = docList.map(FacultyDocument.fromJson).toList();
      return _FetchOutcome.applied;
    } catch (_) {
      return _FetchOutcome.failed;
    }
  }

  Future<_FetchOutcome> _fetchNotifications() async {
    final nRes = await ApiClient.get('/api/faculty/notifications');
    if (nRes.statusCode != 200) return _FetchOutcome.failed;
    final nData = jsonDecode(nRes.body) as Map<String, dynamic>;
    final list = (nData['notifications'] as List<dynamic>? ?? [])
        .map((n) => {
              'title': (n['title'] ?? '').toString(),
              'body': (n['body'] ?? '').toString(),
            })
        .toList();
    notifications = list.isNotEmpty || notifications.isEmpty ? list : notifications;
    return _FetchOutcome.applied;
  }

  Future<void> save() async {
    final byIndicator = <String, List<Map<String, dynamic>>>{};
    for (final e in entries) {
      byIndicator.putIfAbsent(e.indicatorId, () => []).add(e.toJson());
    }
    final assessment = {
      'setSef': {'SET': setRatings, 'SEF': sefRatings},
      'entries': byIndicator,
    };
    await ApiClient.putJson('/api/faculty/assessment', {'assessment': assessment});
  }

  double estimatedKraWeightedTotal() => SimulationEngine.compute(this).weightedTotal;

  double verifiedKraWeightedTotal() => SimulationEngine.compute(this, verified: true).weightedTotal;
}

enum _FetchOutcome { applied, failed }
