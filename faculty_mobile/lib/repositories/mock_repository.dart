import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

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
        id: j['id'],
        indicatorId: j['indicatorId'],
        title: j['title'],
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
    this.ocrText = 'SIMULATED OCR — pending upload integration',
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
        indicatorId: j['indicatorId'],
        kraId: j['kraId'],
        fileName: j['fileName'],
        reviewStatus: j['reviewStatus'] ?? 'pending',
        remarks: j['remarks'],
        ocrText: j['ocrText'] ?? '',
        folder: j['folder'],
        academicYear: j['academicYear'],
        semester: j['semester'],
      );
}

class MockRepository {
  static const _key = 'facultylink_mobile_state_v1';

  FacultyProfile profile = FacultyProfile(
    id: 'fac-001',
    name: 'Juan Dela Cruz',
    email: 'faculty@ustp.demo',
    rank: 'Instructor I',
    reviewerName: 'Elena Mendoza',
  );

  List<double?> setRatings = [92, 94, null, null, null, null];
  List<double?> sefRatings = [95, 96, null, null, null, null];
  List<String> academicYears = ['2023-2024', '2024-2025', '2025-2026'];
  List<AssessmentEntry> entries = [];
  List<FacultyDocument> documents = [];
  List<Map<String, String>> notifications = [];

  static Future<MockRepository> load() async {
    final prefs = await SharedPreferences.getInstance();
    final repo = MockRepository();
    final raw = prefs.getString(_key);
    if (raw == null) {
      repo._seedDemo();
      await repo.save();
      return repo;
    }
    final j = jsonDecode(raw) as Map<String, dynamic>;
    final p = j['profile'] as Map<String, dynamic>;
    repo.profile = FacultyProfile(
      id: p['id'],
      name: p['name'],
      email: p['email'],
      rank: p['rank'],
      reviewerName: p['reviewerName'],
      reviewerRole: p['reviewerRole'] ?? 'Assigned Evaluator',
      reviewerAssignmentStatus: p['reviewerAssignmentStatus'] ?? 'Active',
    );
    repo.setRatings = (j['setRatings'] as List).map((e) => e == null ? null : (e as num).toDouble()).toList();
    repo.sefRatings = (j['sefRatings'] as List).map((e) => e == null ? null : (e as num).toDouble()).toList();
    repo.entries = (j['entries'] as List).map((e) => AssessmentEntry.fromJson(e)).toList();
    repo.documents = (j['documents'] as List).map((e) => FacultyDocument.fromJson(e)).toList();
    repo.notifications = (j['notifications'] as List).map((e) => Map<String, String>.from(e as Map)).toList();
    return repo;
  }

  void _seedDemo() {
    entries = [
      AssessmentEntry(
        id: 'e1',
        indicatorId: 'kra-II-A-3',
        title: 'IoT Classroom Monitoring',
        date: '2025-06-01',
        contributionPercent: 100,
        estimatedPoints: 50,
        reviewStatus: 'submitted',
      ),
    ];
    documents = [
      FacultyDocument(
        id: 'd1',
        indicatorId: 'kra-I-A-set',
        kraId: 'kra-I',
        fileName: 'SET_2024-2025_1st.pdf',
        reviewStatus: 'approved',
        folder: 'SET',
        academicYear: '2024-2025',
        semester: '1st Sem',
        ocrText: 'SIMULATED OCR — SET rating 94%',
      ),
      FacultyDocument(
        id: 'd2',
        indicatorId: 'kra-II-A-3',
        kraId: 'kra-II',
        fileName: 'Journal_Article.pdf',
        reviewStatus: 'correction_requested',
        remarks: 'ISSN not legible',
        ocrText: 'SIMULATED OCR — ISSN low confidence',
      ),
    ];
    notifications = [
      {'title': 'Correction requested', 'body': 'Journal article needs ISSN clarification'},
      {'title': 'Document approved', 'body': 'SET evidence approved for 2024-2025 1st Sem'},
    ];
  }

  Future<void> save() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(
      _key,
      jsonEncode({
        'profile': {
          'id': profile.id,
          'name': profile.name,
          'email': profile.email,
          'rank': profile.rank,
          'reviewerName': profile.reviewerName,
          'reviewerRole': profile.reviewerRole,
          'reviewerAssignmentStatus': profile.reviewerAssignmentStatus,
        },
        'setRatings': setRatings,
        'sefRatings': sefRatings,
        'entries': entries.map((e) => e.toJson()).toList(),
        'documents': documents.map((d) => d.toJson()).toList(),
        'notifications': notifications,
      }),
    );
  }

  double estimatedKraWeightedTotal() => SimulationEngine.compute(this).weightedTotal;

  double verifiedKraWeightedTotal() => SimulationEngine.compute(this, verified: true).weightedTotal;

  Future<void> resetEmptyProfile() async {
    profile = FacultyProfile(
      id: 'fac-002',
      name: 'Maria Santos',
      email: 'maria.santos@ustp.demo',
      rank: 'Assistant Professor I',
      reviewerName: 'Elena Mendoza',
    );
    setRatings = List.filled(6, null);
    sefRatings = List.filled(6, null);
    entries = [];
    documents = [];
    notifications = [];
    await save();
  }
}
