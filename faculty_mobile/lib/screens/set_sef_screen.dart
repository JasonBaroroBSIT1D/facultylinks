import 'dart:async';

import 'package:flutter/material.dart';

import '../repositories/mock_repository.dart';
import '../services/set_sef_api.dart';
import '../theme/app_spacing.dart';
import '../theme/app_theme.dart';
import '../widgets/set_sef_semester_list.dart';
import 'document_detail_screen.dart';

/// Read-only Criterion A — SET/SEF summary (My Assessment → SET & SEF).
class SetSefScreen extends StatefulWidget {
  final MockRepository repo;
  final Future<void> Function() onSave;
  const SetSefScreen({super.key, required this.repo, required this.onSave});

  @override
  State<SetSefScreen> createState() => _SetSefScreenState();
}

class _SetSefScreenState extends State<SetSefScreen> {
  bool _loading = true;
  String? _loadError;
  Map<String, dynamic>? _criterionA;

  @override
  void initState() {
    super.initState();
    unawaited(_loadCriterionA());
  }

  Future<void> _loadCriterionA() async {
    setState(() {
      _loading = true;
      _loadError = null;
    });
    try {
      final data = await SetSefApi.fetchCriterionA();
      if (!mounted) return;
      setState(() {
        _criterionA = data;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loadError = e.toString().replaceFirst('Exception: ', '');
        _loading = false;
      });
    }
  }

  static String _formatScoringBlock(Map<String, dynamic>? scoring, String label) {
    return MockRepository.formatCriterionALine(scoring, prefix: label);
  }

  List<Map<String, dynamic>> _mergedSemesterRecords() {
    final merged = (_criterionA?['mergedSemesters'] as List<dynamic>?) ?? [];
    return merged.map((e) => Map<String, dynamic>.from(e as Map)).toList();
  }

  List<FacultyDocument> _setSefDocuments() {
    final fromRepo = widget.repo.documents.where((d) => d.isSetSefOcr).toList();
    if (fromRepo.isNotEmpty) return fromRepo;
    final apiDocs = (_criterionA?['documents'] as List<dynamic>?) ?? [];
    return apiDocs.map((j) => FacultyDocument.fromJson(Map<String, dynamic>.from(j as Map))).toList();
  }

  Widget _legacyManualSection() {
    final years = widget.repo.academicYears;
    const semesters = ['1st Sem', '2nd Sem'];
    final slots = <({String label, double? set, double? sef})>[];
    for (var i = 0; i < 6; i++) {
      final yearIdx = i ~/ semesters.length;
      if (yearIdx >= years.length) break;
      final set = i < widget.repo.setRatings.length ? widget.repo.setRatings[i] : null;
      final sef = i < widget.repo.sefRatings.length ? widget.repo.sefRatings[i] : null;
      if (set == null && sef == null) continue;
      slots.add((
        label: '${years[yearIdx]} · ${semesters[i % semesters.length]}',
        set: set,
        sef: sef,
      ));
    }
    if (slots.isEmpty) return const SizedBox.shrink();
    return FlSurfaceCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Manual ratings (legacy)', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
          const SizedBox(height: 6),
          const Text(
            'These entries are from an older form. Your official SET/SEF scores come from uploaded PDFs above.',
            style: TextStyle(fontSize: 14, color: AppColors.textMuted, height: 1.4),
          ),
          const SizedBox(height: 10),
          ...slots.map(
            (s) => Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Text(
                '${s.label} — SET: ${s.set?.toStringAsFixed(2) ?? 'Not available'} · SEF: ${s.sef?.toStringAsFixed(2) ?? 'Not available'}',
                style: const TextStyle(fontSize: 15, height: 1.35),
              ),
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final scoring = _criterionA?['scoring'] as Map<String, dynamic>?;
    final est = scoring?['estimated'] as Map<String, dynamic>?;
    final ver = scoring?['verified'] as Map<String, dynamic>?;
    final merged = _mergedSemesterRecords();
    final docs = _setSefDocuments();
    final repoEst = widget.repo.criterionAEstimatedLine();
    final repoVer = widget.repo.criterionAVerifiedLine();

    return Scaffold(
      appBar: AppBar(
        title: const Text('SET & SEF · Criterion A'),
      ),
      body: RefreshIndicator(
        color: AppColors.primaryBlue,
        onRefresh: _loadCriterionA,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: FlLayout.pagePadding,
          children: [
            const Text(
              'Teaching effectiveness from your SET and SEF evaluation PDFs. This view is read-only; your reviewer verifies semester ratings.',
              style: TextStyle(fontSize: 15, color: AppColors.textMuted, height: 1.45),
            ),
            const SizedBox(height: 14),
            FlSurfaceCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Criterion A totals', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700)),
                  const SizedBox(height: 8),
                  if (_loading) const LinearProgressIndicator(minHeight: 3),
                  if (_loadError != null)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: Text(_loadError!, style: const TextStyle(color: Color(0xFFC62828), fontSize: 14)),
                    ),
                  if (est != null)
                    Text(_formatScoringBlock(est, 'Estimated'), style: const TextStyle(fontSize: 15, height: 1.4))
                  else if (repoEst.isNotEmpty)
                    Text(repoEst, style: const TextStyle(fontSize: 15, height: 1.4))
                  else
                    const Text('Estimated: Not available yet', style: TextStyle(fontSize: 15)),
                  const SizedBox(height: 6),
                  if (ver != null)
                    Text(_formatScoringBlock(ver, 'Reviewer-verified'), style: const TextStyle(fontSize: 15, height: 1.4))
                  else if (repoVer.isNotEmpty)
                    Text(repoVer, style: const TextStyle(fontSize: 15, height: 1.4))
                  else
                    const Text('Reviewer-verified: Not available yet', style: TextStyle(fontSize: 15)),
                ],
              ),
            ),
            const SizedBox(height: 12),
            if (merged.isNotEmpty) ...[
              const Text('Semester records (faculty total)', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700)),
              const SizedBox(height: 8),
              SetSefSemesterList(
                records: merged,
                facultyDisplayName: SetSefSemesterList.facultyNameFromRecords(merged) ?? widget.repo.profile.name,
              ),
            ] else if (!_loading)
              FlSurfaceCard(
                child: Text(
                  (_criterionA?['message'] as String?) ?? 'No merged semester records yet. Upload a SET/SEF PDF from My Assessment.',
                  style: const TextStyle(fontSize: 15, height: 1.4),
                ),
              ),
            const SizedBox(height: 12),
            const Text('Supporting documents', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700)),
            const SizedBox(height: 8),
            if (docs.isEmpty)
              const Text('No SET/SEF uploads yet.', style: TextStyle(fontSize: 15, color: AppColors.textMuted))
            else
              ...docs.map(
                (d) => Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: FlSurfaceCard(
                    onTap: () => Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (_) => DocumentDetailScreen(doc: d, repo: widget.repo, onRefresh: widget.onSave),
                      ),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.picture_as_pdf_outlined, color: AppColors.primaryBlue),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(d.fileName, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 16)),
                              Text(
                                'Review: ${d.reviewStatus.replaceAll('_', ' ')} · ${d.processingStatus}',
                                style: const TextStyle(fontSize: 14, color: AppColors.textMuted),
                              ),
                            ],
                          ),
                        ),
                        const Icon(Icons.chevron_right, color: AppColors.textMuted),
                      ],
                    ),
                  ),
                ),
              ),
            const SizedBox(height: 12),
            _legacyManualSection(),
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }
}
