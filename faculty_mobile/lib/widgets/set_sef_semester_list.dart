import 'package:flutter/material.dart';

/// Read-only SET/SEF semester rows for faculty document details (vertical cards).
class SetSefSemesterList extends StatelessWidget {
  final List<Map<String, dynamic>> records;
  final String? facultyDisplayName;
  final bool compactExpandable;

  const SetSefSemesterList({
    super.key,
    required this.records,
    this.facultyDisplayName,
    this.compactExpandable = false,
  });

  static String? facultyNameFromRecords(List<Map<String, dynamic>> records) {
    for (final r in records) {
      final n = r['facultyNameExtracted'];
      if (n is String && n.trim().isNotEmpty) return n.trim();
    }
    return null;
  }

  static String? _ratingText(dynamic value) {
    if (value == null || value == '') return null;
    if (value is num) return value.toStringAsFixed(2);
    final n = num.tryParse(value.toString());
    if (n == null) return null;
    return n.toStringAsFixed(2);
  }

  static String _verifyLabel(String? status) {
    switch (status) {
      case 'verified':
        return 'Verified';
      case 'needs_review':
        return 'Needs review';
      case 'rejected':
        return 'Rejected';
      case 'pending':
        return 'Pending';
      default:
        return status != null && status.isNotEmpty ? status.replaceAll('_', ' ') : 'Pending';
    }
  }

  static String _sourceLine(Map<String, dynamic> r) {
    final pages = <int>{
      ...((r['setSourcePages'] as List<dynamic>?)?.map((e) => (e as num).toInt()) ?? []),
      ...((r['sefSourcePages'] as List<dynamic>?)?.map((e) => (e as num).toInt()) ?? []),
    }.toList()
      ..sort();
    if (pages.isEmpty) return 'Source: Not available';
    if (pages.length == 1) return 'Source: Page ${pages.first}';
    return 'Source: Pages ${pages.join(', ')}';
  }

  static String _semesterTitle(Map<String, dynamic> r) {
    final ay = r['academicYear'];
    final sem = r['semester'];
    final ayStr = ay == null || '$ay'.trim().isEmpty ? '—' : '$ay';
    final semStr = sem == null || '$sem'.trim().isEmpty ? '—' : '$sem';
    return '$ayStr · $semStr';
  }

  @override
  Widget build(BuildContext context) {
    final scale = MediaQuery.textScalerOf(context);
    final titleSize = scale.scale(16);
    final bodySize = scale.scale(15);
    final metaSize = scale.scale(14);
    final faculty = facultyDisplayName ?? facultyNameFromRecords(records);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (faculty != null) ...[
          Text(
            faculty,
            style: TextStyle(fontSize: titleSize, fontWeight: FontWeight.w600, height: 1.35),
          ),
          const SizedBox(height: 12),
        ],
        ...records.map((r) => Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: compactExpandable
                  ? _SemesterExpansionTile(record: r, bodySize: bodySize)
                  : _SemesterCard(
                      record: r,
                      titleSize: titleSize,
                      bodySize: bodySize,
                      metaSize: metaSize,
                    ),
            )),
      ],
    );
  }
}

class _SemesterExpansionTile extends StatelessWidget {
  final Map<String, dynamic> record;
  final double bodySize;

  const _SemesterExpansionTile({required this.record, required this.bodySize});

  @override
  Widget build(BuildContext context) {
    final setExt = SetSefSemesterList._ratingText(record['setRatingExtracted']);
    final setConf = SetSefSemesterList._ratingText(record['setRatingConfirmed']);
    final sefExt = SetSefSemesterList._ratingText(record['sefRatingExtracted']);
    final sefConf = SetSefSemesterList._ratingText(record['sefRatingConfirmed']);
    final setShow = setConf ?? setExt ?? '—';
    final sefShow = sefConf ?? sefExt ?? '—';
    final setStatus = SetSefSemesterList._verifyLabel(record['setVerificationStatus'] as String?);
    final sefStatus = SetSefSemesterList._verifyLabel(record['sefVerificationStatus'] as String?);

    return Material(
      color: const Color(0xFFF8FAFC),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
        side: const BorderSide(color: Color(0xFFE2E8F0)),
      ),
      child: Theme(
        data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
        child: ExpansionTile(
          tilePadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 0),
          childrenPadding: const EdgeInsets.fromLTRB(12, 0, 12, 10),
          title: Text(
            SetSefSemesterList._semesterTitle(record),
            style: TextStyle(fontSize: bodySize, fontWeight: FontWeight.w700),
          ),
          subtitle: Text(
            'SET $setShow ($setStatus) · SEF $sefShow ($sefStatus)',
            style: TextStyle(fontSize: bodySize * 0.9, color: Colors.black54, height: 1.3),
          ),
          children: [
            Wrap(
              spacing: 16,
              runSpacing: 6,
              children: [
                _RatingBlock(label: 'SET', confirmed: setConf, extracted: setExt, fontSize: bodySize),
                _RatingBlock(label: 'SEF', confirmed: sefConf, extracted: sefExt, fontSize: bodySize),
              ],
            ),
            const SizedBox(height: 6),
            Text(
              'SET ${SetSefSemesterList._verifyLabel(record['setVerificationStatus'] as String?)} · '
              'SEF ${SetSefSemesterList._verifyLabel(record['sefVerificationStatus'] as String?)}',
              style: TextStyle(fontSize: bodySize, fontWeight: FontWeight.w500),
            ),
            const SizedBox(height: 4),
            Text(
              SetSefSemesterList._sourceLine(record),
              style: TextStyle(fontSize: bodySize * 0.93, color: Colors.black54),
            ),
          ],
        ),
      ),
    );
  }
}

class _SemesterCard extends StatelessWidget {
  final Map<String, dynamic> record;
  final double titleSize;
  final double bodySize;
  final double metaSize;

  const _SemesterCard({
    required this.record,
    required this.titleSize,
    required this.bodySize,
    required this.metaSize,
  });

  @override
  Widget build(BuildContext context) {
    final setExt = SetSefSemesterList._ratingText(record['setRatingExtracted']);
    final setConf = SetSefSemesterList._ratingText(record['setRatingConfirmed']);
    final sefExt = SetSefSemesterList._ratingText(record['sefRatingExtracted']);
    final sefConf = SetSefSemesterList._ratingText(record['sefRatingConfirmed']);

    return Material(
      color: const Color(0xFFF8FAFC),
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: Color(0xFFE2E8F0)),
      ),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              SetSefSemesterList._semesterTitle(record),
              style: TextStyle(fontSize: titleSize, fontWeight: FontWeight.w700, height: 1.3),
            ),
            const SizedBox(height: 10),
            Wrap(
              spacing: 20,
              runSpacing: 8,
              crossAxisAlignment: WrapCrossAlignment.start,
              children: [
                _RatingBlock(label: 'SET', confirmed: setConf, extracted: setExt, fontSize: bodySize),
                _RatingBlock(label: 'SEF', confirmed: sefConf, extracted: sefExt, fontSize: bodySize),
              ],
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 16,
              runSpacing: 6,
              children: [
                Text(
                  'SET: ${SetSefSemesterList._verifyLabel(record['setVerificationStatus'] as String?)}',
                  style: TextStyle(fontSize: bodySize, fontWeight: FontWeight.w500, height: 1.35),
                ),
                Text(
                  'SEF: ${SetSefSemesterList._verifyLabel(record['sefVerificationStatus'] as String?)}',
                  style: TextStyle(fontSize: bodySize, fontWeight: FontWeight.w500, height: 1.35),
                ),
              ],
            ),
            const SizedBox(height: 6),
            Text(
              SetSefSemesterList._sourceLine(record),
              style: TextStyle(fontSize: metaSize, color: Colors.black54, height: 1.35),
            ),
          ],
        ),
      ),
    );
  }
}

class _RatingBlock extends StatelessWidget {
  final String label;
  final String? confirmed;
  final String? extracted;
  final double fontSize;

  const _RatingBlock({
    required this.label,
    required this.confirmed,
    required this.extracted,
    required this.fontSize,
  });

  @override
  Widget build(BuildContext context) {
    final primary = confirmed ?? extracted;
    final differs = confirmed != null && extracted != null && confirmed != extracted;

    if (primary == null) {
      return Text(
        '$label: Not available',
        style: TextStyle(fontSize: fontSize, height: 1.35),
      );
    }

    if (differs) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            '$label: $confirmed',
            style: TextStyle(fontSize: fontSize, fontWeight: FontWeight.w600, height: 1.35),
          ),
          Text(
            'Extracted: $extracted',
            style: TextStyle(fontSize: fontSize * 0.93, color: Colors.black54, height: 1.35),
          ),
        ],
      );
    }

    return Text(
      '$label: $primary',
      style: TextStyle(fontSize: fontSize, fontWeight: FontWeight.w600, height: 1.35),
    );
  }
}
