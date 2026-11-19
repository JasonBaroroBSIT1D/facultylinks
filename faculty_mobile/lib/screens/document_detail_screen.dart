import 'dart:async';

import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../core/document_status.dart';
import '../repositories/mock_repository.dart';
import '../services/document_api.dart';
import '../services/set_sef_api.dart';
import '../theme/app_theme.dart';
import '../widgets/document_detail_ui.dart';
import '../widgets/set_sef_semester_list.dart';
import 'set_sef_screen.dart';

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
  Map<String, dynamic>? _validation;
  String? _error;
  bool _loading = false;
  bool _openingFile = false;
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
    } else if (_needsValidationPayload(widget.doc)) {
      unawaited(_refreshValidation());
    }
    _reviewPoll = Timer.periodic(const Duration(seconds: 30), (_) => _backgroundStatusRefresh());
  }

  bool _needsValidationPayload(FacultyDocument doc) {
    return doc.ocrStatus.isNotEmpty && doc.ocrStatus != 'none';
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
    } else if (_needsValidationPayload(widget.doc)) {
      await _refreshValidation(silent: true);
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
      _poll ??= Timer.periodic(const Duration(seconds: 4), (_) {
        if (widget.doc.isSetSefOcr) {
          _refreshSetSef(silent: true);
        } else {
          _refreshValidation(silent: true);
        }
      });
    } else {
      _poll?.cancel();
      _poll = null;
    }
  }

  Future<void> _refreshValidation({bool silent = false}) async {
    if (!mounted) return;
    if (!silent) setState(() => _loading = true);
    try {
      final data = await DocumentApi.fetchValidation(widget.doc.id);
      if (!mounted) return;
      final docMap = data['document'] as Map<String, dynamic>?;
      final proc = docMap?['processingStatus'] as String? ?? _liveDoc.processingStatus;
      setState(() {
        _validation = data;
        _error = null;
        _loading = false;
      });
      _schedulePolling(proc);
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        if (!silent) _error = e.toString().replaceFirst('Exception: ', '');
      });
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

  Future<void> _openOriginalFile() async {
    setState(() => _openingFile = true);
    try {
      final url = await DocumentApi.viewUrl(widget.doc.id);
      final uri = Uri.parse(url);
      final ok = await launchUrl(uri, mode: LaunchMode.externalApplication);
      if (!ok && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Could not open this file on your device.')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e.toString().replaceFirst('Exception: ', ''))),
        );
      }
    } finally {
      if (mounted) setState(() => _openingFile = false);
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

  Future<void> _retryGeneralOcr() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      await DocumentApi.retryValidationOcr(widget.doc.id);
      await widget.onRefresh?.call();
      await _refreshValidation(silent: true);
      if (mounted) setState(() => _loading = false);
    } catch (e) {
      if (mounted) {
        setState(() {
          _loading = false;
          _error = e.toString().replaceFirst('Exception: ', '');
        });
      }
    }
  }

  void _openOverallAssessment() {
    final repo = widget.repo;
    if (repo == null) return;
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => SetSefScreen(repo: repo, onSave: widget.onRefresh ?? () async {}),
      ),
    );
  }

  List<Map<String, dynamic>> _findingsForDoc() {
    if (widget.doc.isSetSefOcr) {
      return (_extraction?['validationFindings'] as List<dynamic>?)?.cast<Map<String, dynamic>>() ?? [];
    }
    return (_validation?['validationFindings'] as List<dynamic>?)?.cast<Map<String, dynamic>>() ?? [];
  }

  @override
  Widget build(BuildContext context) {
    final doc = _liveDoc;
    final records = (_extraction?['semesterRecords'] as List<dynamic>?)?.cast<Map<String, dynamic>>() ?? [];
    final verifyCounts = _extraction?['verifyCounts'] as Map<String, dynamic>?;
    final scoring = _extraction?['scoring'] as Map<String, dynamic>?;
    final est = scoring?['estimated'] as Map<String, dynamic>?;
    final ver = scoring?['verified'] as Map<String, dynamic>?;
    final findings = _findingsForDoc();
    final fileLabel = originalFileActionLabel(doc);
    final isImage = fileLabel.contains('image');

    return Scaffold(
      appBar: AppBar(
        title: const Text('Document details'),
        leading: BackButton(onPressed: () => Navigator.maybePop(context)),
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
        children: [
          Text(doc.fileName, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 10),
          DocumentStatusStrip(
            doc: doc,
            semesterRecords: records,
            verifyCounts: verifyCounts,
          ),
          if (doc.isAchievementEvidence)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(
                'Supporting evidence for an achievement (scored on the achievement, not as a standalone document).',
                style: const TextStyle(fontSize: 13, color: AppColors.textMuted, height: 1.35),
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
                    const Text('Achievement', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
                    const SizedBox(height: 6),
                    for (final link in doc.achievementLinks) ...[
                      Text(
                        link.parentAchievementTitle ?? link.linkedAchievementId,
                        style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
                      ),
                      if (link.criterionId != null)
                        Text('Criterion: ${link.criterionId}', style: const TextStyle(fontSize: 13, color: AppColors.textMuted)),
                      const SizedBox(height: 6),
                    ],
                  ],
                ),
              ),
            ),
          ],
          if (doc.createdAt != null)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(
                'Uploaded: ${doc.createdAt!.length >= 10 ? doc.createdAt!.substring(0, 10) : doc.createdAt}',
                style: const TextStyle(fontSize: 14, color: AppColors.textMuted),
              ),
            ),
          if (doc.indicatorId.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text('Category: ${doc.indicatorId}', style: const TextStyle(fontSize: 14, color: AppColors.textMuted)),
            ),
          const SizedBox(height: 14),
          FilledButton.icon(
            onPressed: _openingFile ? null : _openOriginalFile,
            icon: _openingFile
                ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                : Icon(isImage ? Icons.image_outlined : Icons.picture_as_pdf_outlined),
            label: Text(fileLabel),
          ),
          if (doc.filterBucket == 'correction_requested' && !doc.isAchievementEvidence)
            const Padding(
              padding: EdgeInsets.only(top: 10),
              child: Text(
                'Your reviewer requested changes. See Needs attention below.',
                style: TextStyle(fontSize: 14),
              ),
            ),
          const SizedBox(height: 12),
          DocumentProcessingActionsCard(
            doc: doc,
            loading: _loading,
            error: _error,
            isSetSef: doc.isSetSefOcr,
            onRetry: doc.isSetSefOcr ? _retryOcr : _retryGeneralOcr,
            showPollHint: _shouldPoll(doc.processingStatus),
          ),
          if (doc.isSetSefOcr) ...[
            if (est != null || ver != null) ...[
              const SizedBox(height: 12),
              DocumentScoresFromPdfCard(
                estimated: est,
                verified: ver,
                semesterCount: records.length,
              ),
            ],
            if (widget.repo != null) ...[
              const SizedBox(height: 8),
              Align(
                alignment: Alignment.centerLeft,
                child: TextButton(
                  onPressed: _openOverallAssessment,
                  child: const Text('View overall assessment'),
                ),
              ),
            ],
            const SizedBox(height: 12),
            DocumentSemestersSection(
              records: records,
              facultyDisplayName:
                  SetSefSemesterList.facultyNameFromRecords(records) ?? widget.repo?.profile.name,
              processingStatus: doc.processingStatus,
            ),
          ],
          if (findings.isNotEmpty || (doc.remarks != null && doc.remarks!.trim().isNotEmpty)) ...[
            const SizedBox(height: 12),
            DocumentNeedsAttentionSection(
              findings: findings,
              reviewerRemarks: doc.remarks,
            ),
          ],
        ],
      ),
    );
  }
}