import 'dart:async';

import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../core/document_status.dart';
import '../core/ui_strings.dart';
import '../repositories/mock_repository.dart';
import '../theme/app_spacing.dart';
import '../services/document_api.dart';
import '../services/set_sef_api.dart';
import '../widgets/set_sef_semester_list.dart';

class DocumentDetailScreen extends StatefulWidget {
  final FacultyDocument doc;
  final MockRepository? repo;
  final Future<void> Function()? onRefresh;
  const DocumentDetailScreen({super.key, required this.doc, this.repo, this.onRefresh});

  @override
  State<DocumentDetailScreen> createState() => _DocumentDetailScreenState();
}

class _DocumentDetailScreenState extends State<DocumentDetailScreen> with WidgetsBindingObserver {
  Map<String, dynamic>? _extraction;
  String? _error;
  bool _loading = false;
  bool _openingPdf = false;
  Timer? _poll;
  Timer? _reviewPoll;
  bool _foreground = true;

  FacultyDocument get _liveDoc {
    final live = widget.repo?.documentById(widget.doc.id);
    final base = live ?? widget.doc;
    final fromApi = _extraction?['document'] as Map<String, dynamic>?;
    if (fromApi == null) return base;
    return FacultyDocument.fromJson({...base.toJson(), ...fromApi});
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    if (widget.doc.isSetSefOcr) {
      unawaited(_refreshSetSef());
    }
    _reviewPoll = Timer.periodic(const Duration(seconds: 30), (_) => _backgroundStatusRefresh());
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _poll?.cancel();
    _reviewPoll?.cancel();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    _foreground = state == AppLifecycleState.resumed;
    if (_foreground) {
      unawaited(_backgroundStatusRefresh());
    } else {
      _poll?.cancel();
      _poll = null;
    }
  }

  Future<void> _backgroundStatusRefresh() async {
    if (!mounted || !_foreground) return;
    await widget.onRefresh?.call();
    if (widget.doc.isSetSefOcr) {
      await _refreshSetSef(silent: true);
    } else if (mounted) {
      setState(() {});
    }
  }

  bool _shouldPoll(String processingStatus) {
    return processingStatus == 'queued' || processingStatus == 'processing' || processingStatus == 'pending';
  }

  void _schedulePolling(String processingStatus) {
    if (!_foreground) return;
    if (_shouldPoll(processingStatus)) {
      _poll ??= Timer.periodic(const Duration(seconds: 4), (_) => _refreshSetSef(silent: true));
    } else {
      _poll?.cancel();
      _poll = null;
    }
  }

  Future<void> _refreshSetSef({bool silent = false}) async {
    if (!mounted) return;
    if (!silent) setState(() => _loading = true);
    try {
      final data = await SetSefApi.fetchExtraction(widget.doc.id);
      if (!mounted) return;
      final proc = (data['document'] as Map<String, dynamic>?)?['processingStatus'] as String? ?? _liveDoc.processingStatus;
      setState(() {
        _extraction = data;
        _error = null;
        _loading = false;
      });
      _schedulePolling(proc);
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = e.toString().replaceFirst('Exception: ', '');
      });
      _poll?.cancel();
      _poll = null;
    }
  }

  Future<void> _openPdf() async {
    setState(() => _openingPdf = true);
    try {
      final url = await DocumentApi.viewUrl(widget.doc.id);
      final uri = Uri.parse(url);
      final ok = await launchUrl(uri, mode: LaunchMode.externalApplication);
      if (!ok && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Could not open the PDF on this device.')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e.toString().replaceFirst('Exception: ', ''))),
        );
      }
    } finally {
      if (mounted) setState(() => _openingPdf = false);
    }
  }

  Future<void> _retryOcr() async {
    setState(() => _loading = true);
    try {
      await SetSefApi.retryOcr(widget.doc.id);
      await _refreshSetSef(silent: true);
      await widget.onRefresh?.call();
    } catch (e) {
      if (mounted) {
        setState(() {
          _loading = false;
          _error = e.toString().replaceFirst('Exception: ', '');
        });
      }
    }
  }

  static String _formatScoring(Map<String, dynamic>? scoring) {
    if (scoring == null) return 'No processed data yet.';
    if (scoring['calculationUnavailable'] == true) {
      return 'Unavailable — ${scoring['incompleteReason'] ?? 'No eligible ratings.'}';
    }
    final max = (scoring['maxima']?['criterionA'] as num?)?.toDouble() ?? 60.0;
    final maxSlots = scoring['maxSemesterSlots'] ?? scoring['requiredSlots'] ?? 6;
    final setN = scoring['setCount'] ?? 0;
    final sefN = scoring['sefCount'] ?? 0;
    final slots = 'SET: $setN/$maxSlots · SEF: $sefN/$maxSlots';
    var total = scoring['criterionAPoints'] as num?;
    if (total == null) total = scoring['partialSubtotal'] as num?;
    if (total == null) {
      final setPts = scoring['setPoints'];
      final sefPts = scoring['sefPoints'];
      if (setPts != null || sefPts != null) {
        final partial = (setPts as num? ?? 0) + (sefPts as num? ?? 0);
        return 'Partial ${partial.toStringAsFixed(2)} / $max ($slots)';
      }
      return 'No score calculated yet.';
    }
    final note = scoring['incomplete'] == true
        ? ' · ${scoring['coverageNote'] ?? 'Based on available semesters; may change as ratings are added.'}'
        : '';
    final setPts = scoring['setPoints'];
    final sefPts = scoring['sefPoints'];
    return '${total.toStringAsFixed(2)} / $max ($slots)$note'
        ' — SET ${setPts != null ? (setPts as num).toStringAsFixed(2) : '—'}, '
        'SEF ${sefPts != null ? (sefPts as num).toStringAsFixed(2) : '—'}';
  }

  @override
  Widget build(BuildContext context) {
    final doc = _liveDoc;
    final status = doc.displayStatusLabel ?? UiStrings.docStatusLabel(doc.reviewStatus);
    final records = (_extraction?['semesterRecords'] as List<dynamic>?)?.cast<Map<String, dynamic>>() ?? [];
    final findings = (_extraction?['validationFindings'] as List<dynamic>?)?.cast<Map<String, dynamic>>() ?? [];
    final scoring = _extraction?['scoring'] as Map<String, dynamic>?;
    final est = scoring?['estimated'] as Map<String, dynamic>?;
    final ver = scoring?['verified'] as Map<String, dynamic>?;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Document details'),
        leading: BackButton(onPressed: () => Navigator.maybePop(context)),
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text(doc.fileName, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          FlStatusBadge.fromFacultyDocument(doc),
          const SizedBox(height: 6),
          Text('Display status: $status', style: const TextStyle(fontSize: 15, color: Colors.black54)),
          if (doc.isAchievementEvidence)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text(
                'File record: ${UiStrings.docStatusLabel(doc.reviewStatus)} (supporting evidence; scored on the achievement)',
                style: const TextStyle(fontSize: 14, color: Colors.black54),
              ),
            ),
          if (doc.achievementLinks.isNotEmpty) ...[
            const SizedBox(height: 12),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const Text('Achievement', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                    const SizedBox(height: 6),
                    for (final link in doc.achievementLinks) ...[
                      Text(
                        link.parentAchievementTitle ?? link.linkedAchievementId,
                        style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
                      ),
                      if (link.criterionId != null)
                        Text('Criterion: ${link.criterionId}', style: const TextStyle(fontSize: 14, color: Colors.black54)),
                      if (link.achievementRemarks != null && link.achievementRemarks!.trim().isNotEmpty)
                        Padding(
                          padding: const EdgeInsets.only(top: 6),
                          child: Text('Reviewer remarks: ${link.achievementRemarks}', style: const TextStyle(fontSize: 14)),
                        ),
                      const SizedBox(height: 8),
                    ],
                  ],
                ),
              ),
            ),
          ],
          if (doc.createdAt != null)
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Text('Uploaded: ${doc.createdAt!.length >= 10 ? doc.createdAt!.substring(0, 10) : doc.createdAt}', style: const TextStyle(fontSize: 15)),
            ),
          if (doc.indicatorId.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text('Category: ${doc.indicatorId}', style: const TextStyle(fontSize: 15)),
            ),
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: _openingPdf ? null : _openPdf,
            icon: _openingPdf ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(Icons.picture_as_pdf_outlined),
            label: const Text('View original PDF'),
          ),
          if (doc.filterBucket == 'correction_requested' && !doc.isAchievementEvidence)
            const Padding(
              padding: EdgeInsets.only(top: 12),
              child: Text(
                'Your reviewer requested changes. Read their comments below and upload an updated file if needed.',
                style: TextStyle(fontSize: 15),
              ),
            ),
          if (doc.isSetSefOcr) ...[
            const SizedBox(height: 20),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const Text('OCR processing', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                    const SizedBox(height: 8),
                    Text(documentProcessingSummary(doc), style: const TextStyle(fontSize: 15)),
                    if (_shouldPoll(doc.processingStatus))
                      const Padding(
                        padding: EdgeInsets.only(top: 8),
                        child: Row(
                          children: [
                            SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)),
                            SizedBox(width: 10),
                            Expanded(child: Text('Processing your PDF. This screen updates automatically.')),
                          ],
                        ),
                      ),
                    if (doc.processingStatus == 'failed' || doc.ocrStatus == 'failed') ...[
                      if (doc.processingError != null)
                        Padding(
                          padding: const EdgeInsets.only(top: 8),
                          child: Text(doc.processingError!, style: const TextStyle(color: Colors.red)),
                        ),
                      const SizedBox(height: 12),
                      OutlinedButton.icon(
                        onPressed: _loading ? null : _retryOcr,
                        icon: const Icon(Icons.refresh),
                        label: const Text('Retry OCR'),
                      ),
                    ],
                    if (_loading) const Padding(padding: EdgeInsets.only(top: 12), child: LinearProgressIndicator()),
                    if (_error != null)
                      Padding(
                        padding: const EdgeInsets.only(top: 8),
                        child: Text(_error!, style: const TextStyle(color: Colors.red)),
                      ),
                  ],
                ),
              ),
            ),
            if (widget.repo != null &&
                (widget.repo!.criterionAEstimatedLine().isNotEmpty || widget.repo!.criterionAVerifiedLine().isNotEmpty)) ...[
              const SizedBox(height: 12),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Criterion A scoring (faculty total)', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                      const SizedBox(height: 8),
                      if (widget.repo!.criterionAEstimatedLine().isNotEmpty)
                        Text(widget.repo!.criterionAEstimatedLine()),
                      if (widget.repo!.criterionAVerifiedLine().isNotEmpty)
                        Text(widget.repo!.criterionAVerifiedLine()),
                      const SizedBox(height: 6),
                      const Text(
                        'Totals use deduplicated SET/SEF data across your uploads. Per-document extraction appears below.',
                        style: TextStyle(fontSize: 13, color: Colors.black54),
                      ),
                    ],
                  ),
                ),
              ),
            ],
            if (est != null || ver != null) ...[
              const SizedBox(height: 12),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Criterion A scoring (this PDF)', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                      const SizedBox(height: 8),
                      Text('Estimated: ${_formatScoring(est)}'),
                      if (ver != null) Text('Reviewer-verified: ${_formatScoring(ver)}'),
                    ],
                  ),
                ),
              ),
            ],
            const SizedBox(height: 12),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Extracted semesters', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                    const SizedBox(height: 8),
                    if (records.isEmpty)
                      Text(
                        doc.processingStatus == 'completed'
                            ? 'Processing finished but no semester rows were extracted.'
                            : 'No semester records yet.',
                        style: const TextStyle(fontSize: 15),
                      )
                    else
                      SetSefSemesterList(
                        records: records,
                        facultyDisplayName:
                            SetSefSemesterList.facultyNameFromRecords(records) ?? widget.repo?.profile.name,
                      ),
                  ],
                ),
              ),
            ),
            if (findings.isNotEmpty) ...[
              const SizedBox(height: 12),
              const Text('Validation findings', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
              ...findings.map(
                (f) => Padding(
                  padding: const EdgeInsets.only(top: 6),
                  child: Text(
                    '${f['ruleId']}: ${f['explanation'] ?? ''} (${f['outcome'] ?? ''})',
                    style: const TextStyle(fontSize: 14, height: 1.4),
                  ),
                ),
              ),
            ],
          ],
          const SizedBox(height: 16),
          const Text('Reviewer comments', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
          const SizedBox(height: 6),
          Text(
            (doc.remarks != null && doc.remarks!.trim().isNotEmpty) ? doc.remarks! : 'No reviewer comments yet.',
            style: const TextStyle(fontSize: 16, height: 1.5),
          ),
        ],
      ),
    );
  }
}
