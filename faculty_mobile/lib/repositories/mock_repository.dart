import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import '../services/api_client.dart';
import '../services/document_api.dart';
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
  });

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
      };

  factory FacultyDocument.fromJson(Map<String, dynamic> j) => FacultyDocument(
        id: j['id'],
        indicatorId: j['indicatorId'] ?? '',
        kraId: j['kraId'] ?? '',
        fileName: j['fileName'] ?? j['filename'] ?? '',
        reviewStatus: j['reviewStatus'] ?? 'pending',
        remarks: j['remarks'],
        ocrText: j['ocrText'] ?? '',
        folder: j['folder'],
        academicYear: j['academicYear'],
        semester: j['semester'],
      );
}

/// Faculty data loaded from the Flask API (legacy class name retained for screens).
class MockRepository {
  static const _legacyDemoKey = 'facultylink_mobile_state_v1';

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

  static Future<MockRepository> load() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_legacyDemoKey);

    final repo = MockRepository();
    try {
      final meRes = await ApiClient.get('/api/faculty/me');
      if (meRes.statusCode != 200) {
        throw Exception('Could not load profile.');
      }
      final me = jsonDecode(meRes.body) as Map<String, dynamic>;
      final p = me['profile'] as Map<String, dynamic>;
      repo.profile = FacultyProfile(
        id: p['id'],
        name: p['name'],
        email: p['email'],
        rank: p['rank'] ?? '',
        reviewerName: p['reviewerName'] ?? '',
        reviewerRole: p['reviewerRole'] ?? 'Assigned Evaluator',
        reviewerAssignmentStatus: p['reviewerAssignmentStatus'] ?? 'Unassigned',
      );

      final assessRes = await ApiClient.get('/api/faculty/assessment');
      if (assessRes.statusCode == 200) {
        final data = jsonDecode(assessRes.body) as Map<String, dynamic>;
        final assessment = data['assessment'] as Map<String, dynamic>? ?? {};
        final setSef = assessment['setSef'] as Map<String, dynamic>? ?? {};
        repo.setRatings = (setSef['SET'] as List<dynamic>? ?? [])
            .map((e) => e == null ? null : (e as num).toDouble())
            .toList();
        repo.sefRatings = (setSef['SEF'] as List<dynamic>? ?? [])
            .map((e) => e == null ? null : (e as num).toDouble())
            .toList();
        if (repo.setRatings.length < 6) {
          repo.setRatings = [...repo.setRatings, ...List.filled(6 - repo.setRatings.length, null)];
        }
        if (repo.sefRatings.length < 6) {
          repo.sefRatings = [...repo.sefRatings, ...List.filled(6 - repo.sefRatings.length, null)];
        }
        final rawEntries = assessment['entries'] as Map<String, dynamic>? ?? {};
        repo.entries = [];
        rawEntries.forEach((_, list) {
          for (final e in (list as List<dynamic>)) {
            repo.entries.add(AssessmentEntry.fromJson(e as Map<String, dynamic>));
          }
        });
      }

      final docList = await DocumentApi.listMine();
      repo.documents = docList.map(FacultyDocument.fromJson).toList();

      final nRes = await ApiClient.get('/api/faculty/notifications');
      if (nRes.statusCode == 200) {
        final nData = jsonDecode(nRes.body) as Map<String, dynamic>;
        repo.notifications = (nData['notifications'] as List<dynamic>? ?? [])
            .map((n) => {
                  'title': (n['title'] ?? '').toString(),
                  'body': (n['body'] ?? '').toString(),
                })
            .toList();
      }
    } catch (e) {
      repo.loadError = e.toString();
    }
    return repo;
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
