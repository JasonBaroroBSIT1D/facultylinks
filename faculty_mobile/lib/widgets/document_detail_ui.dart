import 'package:flutter/material.dart';

import '../core/document_status.dart';
import '../repositories/mock_repository.dart';
import '../theme/app_theme.dart';
import 'set_sef_semester_list.dart';

class DocumentStatusStrip extends StatelessWidget {
  final FacultyDocument doc;
  final List<Map<String, dynamic>> semesterRecords;
  final Map<String, dynamic>? verifyCounts;

  const DocumentStatusStrip({
    super.key,
    required this.doc,
    this.semesterRecords = const [],
    this.verifyCounts,
  });

  @override
  Widget build(BuildContext context) {
    final reading = documentReadingStatusLabel(doc);
    final reviewer = documentReviewerStatusLabel(
      doc,
      semesterRecords: semesterRecords,
      verifyCounts: verifyCounts,
    );
    return Card(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
        child: Column(
          children: [
            _StatusRow(label: 'Document reading', value: reading),
            const SizedBox(height: 8),
            _StatusRow(label: 'Reviewer status', value: reviewer),
          ],
        ),
      ),
    );
  }
}

class _StatusRow extends StatelessWidget {
  final String label;
  final String value;

  const _StatusRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          flex: 2,
          child: Text(label, style: const TextStyle(fontSize: 14, color: AppColors.textMuted)),
        ),
        Expanded(
          flex: 3,
          child: Text(
            value,
            textAlign: TextAlign.end,
            style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: AppColors.textMain),
          ),
        ),
      ],
    );
  }
}

class DocumentScoresFromPdfCard extends StatelessWidget {
  final Map<String, dynamic>? estimated;
  final Map<String, dynamic>? verified;
  final int semesterCount;

  const DocumentScoresFromPdfCard({
    super.key,
    required this.estimated,
    required this.verified,
    required this.semesterCount,
  });

  @override
  Widget build(BuildContext context) {
    if (estimated == null && verified == null) return const SizedBox.shrink();

    return Card(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(14, 12, 14, 8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text(
              'Scores from this document',
              style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16, color: AppColors.textMain),
            ),
            const SizedBox(height: 10),
            _ScoreRow(
              label: 'Estimated',
              value: formatDocumentCriterionAScore(estimated, verifiedBucket: false),
            ),
            const SizedBox(height: 6),
            _ScoreRow(
              label: 'Reviewer-verified',
              value: formatDocumentCriterionAScore(verified, verifiedBucket: true),
            ),
            const SizedBox(height: 6),
            _ScoreRow(label: 'Semesters in this document', value: '$semesterCount'),
            const SizedBox(height: 4),
            Theme(
              data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
              child: ExpansionTile(
                tilePadding: EdgeInsets.zero,
                childrenPadding: const EdgeInsets.only(bottom: 8),
                title: const Text(
                  'View calculation',
                  style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: AppColors.primaryBlue),
                ),
                children: [
                  if (estimated != null) ...[
                    const Align(
                      alignment: Alignment.centerLeft,
                      child: Text('Estimated', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
                    ),
                    ...criterionACalculationDetailLines(estimated).map(
                      (line) => Padding(
                        padding: const EdgeInsets.only(top: 4),
                        child: Text(line, style: const TextStyle(fontSize: 13, height: 1.35, color: AppColors.textMuted)),
                      ),
                    ),
                    const SizedBox(height: 8),
                  ],
                  if (verified != null) ...[
                    const Align(
                      alignment: Alignment.centerLeft,
                      child: Text('Reviewer-verified', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
                    ),
                    ...criterionACalculationDetailLines(verified).map(
                      (line) => Padding(
                        padding: const EdgeInsets.only(top: 4),
                        child: Text(line, style: const TextStyle(fontSize: 13, height: 1.35, color: AppColors.textMuted)),
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ScoreRow extends StatelessWidget {
  final String label;
  final String value;

  const _ScoreRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Text(label, style: const TextStyle(fontSize: 14, color: AppColors.textMuted)),
        ),
        Text(
          value,
          style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
        ),
      ],
    );
  }
}

class DocumentNeedsAttentionSection extends StatelessWidget {
  final List<Map<String, dynamic>> findings;
  final String? reviewerRemarks;

  const DocumentNeedsAttentionSection({
    super.key,
    required this.findings,
    this.reviewerRemarks,
  });

  @override
  Widget build(BuildContext context) {
    final actionable = findings.where(validationFindingIsActionable).toList();
    final remarks = (reviewerRemarks ?? '').trim();
    final technical = findings.where((f) => !validationFindingIsActionable(f)).toList();

    if (actionable.isEmpty && remarks.isEmpty && technical.isEmpty) {
      return const SizedBox.shrink();
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text(
              'Needs attention',
              style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16, color: AppColors.textMain),
            ),
            if (remarks.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text(remarks, style: const TextStyle(fontSize: 14, height: 1.4)),
            ],
            ...actionable.map(
              (f) => Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('• ', style: TextStyle(fontSize: 14)),
                    Expanded(
                      child: Text(
                        validationFindingFacultyText(f),
                        style: const TextStyle(fontSize: 14, height: 1.35),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            if (technical.isNotEmpty)
              Theme(
                data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
                child: ExpansionTile(
                  tilePadding: EdgeInsets.zero,
                  title: const Text(
                    'Technical details',
                    style: TextStyle(fontSize: 13, color: AppColors.textMuted),
                  ),
                  children: technical
                      .map(
                        (f) => Padding(
                          padding: const EdgeInsets.only(bottom: 6),
                          child: Text(
                            '${f['ruleId'] ?? 'note'}: ${validationFindingFacultyText(f)}',
                            style: const TextStyle(fontSize: 12, height: 1.3, color: AppColors.textMuted),
                          ),
                        ),
                      )
                      .toList(),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class DocumentProcessingActionsCard extends StatelessWidget {
  final FacultyDocument doc;
  final bool loading;
  final String? error;
  final bool isSetSef;
  final VoidCallback? onRetry;
  final bool showPollHint;

  const DocumentProcessingActionsCard({
    super.key,
    required this.doc,
    required this.loading,
    this.error,
    required this.isSetSef,
    this.onRetry,
    this.showPollHint = false,
  });

  bool get _shouldShow {
    final reading = documentReadingStatusLabel(doc);
    return reading == 'Processing' || reading == 'Failed' || (error != null && error!.isNotEmpty);
  }

  @override
  Widget build(BuildContext context) {
    if (!_shouldShow && !loading) return const SizedBox.shrink();

    final msg = documentProcessingFacultyMessage(doc);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (msg.isNotEmpty) Text(msg, style: const TextStyle(fontSize: 14, height: 1.35)),
            if (showPollHint)
              const Padding(
                padding: EdgeInsets.only(top: 8),
                child: Row(
                  children: [
                    SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)),
                    SizedBox(width: 10),
                    Expanded(child: Text('Updating automatically…', style: TextStyle(fontSize: 13))),
                  ],
                ),
              ),
            if (documentReadingStatusLabel(doc) == 'Failed' && onRetry != null) ...[
              const SizedBox(height: 10),
              OutlinedButton.icon(
                onPressed: loading ? null : onRetry,
                icon: const Icon(Icons.refresh, size: 20),
                label: Text(isSetSef ? 'Retry OCR' : 'Retry text check'),
              ),
            ],
            if (loading) const Padding(padding: EdgeInsets.only(top: 10), child: LinearProgressIndicator()),
            if (error != null && error!.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(error!, style: const TextStyle(color: AppColors.redText, fontSize: 13)),
              ),
          ],
        ),
      ),
    );
  }
}

class DocumentSemestersSection extends StatelessWidget {
  final List<Map<String, dynamic>> records;
  final String? facultyDisplayName;
  final String processingStatus;

  const DocumentSemestersSection({
    super.key,
    required this.records,
    this.facultyDisplayName,
    required this.processingStatus,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text(
              'Semesters in this document',
              style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16),
            ),
            const SizedBox(height: 8),
            if (records.isEmpty)
              Text(
                processingStatus == 'completed'
                    ? 'Processing finished but no semester rows were extracted.'
                    : 'No semester records yet.',
                style: const TextStyle(fontSize: 14, color: AppColors.textMuted),
              )
            else
              SetSefSemesterList(
                records: records,
                facultyDisplayName: facultyDisplayName,
                compactExpandable: true,
              ),
          ],
        ),
      ),
    );
  }
}