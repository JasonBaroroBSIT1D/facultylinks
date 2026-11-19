import '../repositories/mock_repository.dart';

/// Faculty-facing document **reading** status (OCR / processing — not reviewer approval).
String documentReadingStatusLabel(FacultyDocument doc) {
  if (doc.processingStatus == 'failed' || doc.ocrStatus == 'failed') {
    return 'Failed';
  }
  if (_readingInProgress(doc)) {
    return 'Processing';
  }
  if (doc.processingStatus == 'completed' ||
      doc.ocrStatus == 'completed' ||
      doc.ocrStatus == 'review_required') {
    return 'Completed';
  }
  if (doc.ocrStatus.isEmpty || doc.ocrStatus == 'none') {
    if (doc.processingStatus.isEmpty || doc.processingStatus == 'none') {
      return '—';
    }
  }
  return 'Processing';
}

bool _readingInProgress(FacultyDocument doc) {
  const active = {'queued', 'processing', 'pending'};
  return active.contains(doc.processingStatus) || active.contains(doc.ocrStatus);
}

/// Faculty-facing **reviewer** status for the document record (not OCR success).
String documentReviewerStatusLabel(
  FacultyDocument doc, {
  List<Map<String, dynamic>> semesterRecords = const [],
  Map<String, dynamic>? verifyCounts,
}) {
  if (doc.displayStatusLabel != null && doc.isAchievementEvidence) {
    return doc.displayStatusLabel!;
  }
  switch (doc.reviewStatus) {
    case 'correction_requested':
      return 'Needs changes';
    case 'correction_prepared':
      return 'Ready to resubmit';
    case 'replaced':
      return 'Superseded';
    case 'rejected':
      return 'Not accepted';
    case 'approved':
      if (doc.isSetSefOcr) {
        return _setSefVerificationLabel(semesterRecords, verifyCounts);
      }
      return 'Verified';
    case 'pending':
    default:
      if (doc.isSetSefOcr) {
        return _setSefVerificationLabel(semesterRecords, verifyCounts);
      }
      return 'Awaiting review';
  }
}

String _setSefVerificationLabel(
  List<Map<String, dynamic>> records,
  Map<String, dynamic>? verifyCounts,
) {
  if (records.isEmpty) {
    return 'Awaiting review';
  }

  var totalSlots = 0;
  var verifiedSlots = 0;
  for (final r in records) {
    final hasSet = r['setRatingExtracted'] != null;
    final hasSef = r['sefRatingExtracted'] != null;
    if (hasSet) {
      totalSlots++;
      if (r['setVerificationStatus'] == 'verified' && r['setRatingConfirmed'] != null) {
        verifiedSlots++;
      }
    }
    if (hasSef) {
      totalSlots++;
      if (r['sefVerificationStatus'] == 'verified' && r['sefRatingConfirmed'] != null) {
        verifiedSlots++;
      }
    }
  }

  if (totalSlots == 0) return 'Awaiting review';
  if (verifiedSlots == 0) return 'Awaiting review';
  if (verifiedSlots >= totalSlots) return 'Verified';
  return 'Partially verified';
}

/// Short helper when extraction is still running.
String documentProcessingFacultyMessage(FacultyDocument doc) {
  switch (documentReadingStatusLabel(doc)) {
    case 'Failed':
      return 'We could not read text from this file. Try a clearer scan or PDF.';
    case 'Processing':
      return 'Document text is still being processed.';
    case 'Completed':
      if (doc.ocrStatus == 'review_required') {
        return 'Text was read successfully and is ready for reviewer checks.';
      }
      return 'Text extraction completed.';
    default:
      return '';
  }
}

/// @deprecated Prefer [documentReadingStatusLabel] + [documentReviewerStatusLabel].
String documentProcessingSummary(FacultyDocument doc) {
  final reading = documentReadingStatusLabel(doc);
  final reviewer = documentReviewerStatusLabel(doc);
  if (reading == '—') return 'Reviewer status: $reviewer';
  return 'Document reading: $reading · Reviewer status: $reviewer';
}

String originalFileActionLabel(FacultyDocument doc) {
  final mime = (doc.mimeType ?? '').toLowerCase();
  final name = doc.fileName.toLowerCase();
  if (mime.startsWith('image/') ||
      name.endsWith('.jpg') ||
      name.endsWith('.jpeg') ||
      name.endsWith('.png') ||
      name.endsWith('.webp')) {
    return 'View original image';
  }
  return 'View original PDF';
}

/// Compact Criterion A score for document header (this PDF only).
String formatDocumentCriterionAScore(
  Map<String, dynamic>? scoring, {
  required bool verifiedBucket,
}) {
  if (scoring == null) {
    return verifiedBucket ? 'Not yet verified' : '—';
  }
  if (scoring['calculationUnavailable'] == true) {
    return verifiedBucket ? 'Not yet verified' : 'Not available yet';
  }
  final max = (scoring['maxima']?['criterionA'] as num?)?.toDouble() ?? 60.0;
  var total = scoring['criterionAPoints'] as num?;
  final partialOnly = total == null;
  total ??= scoring['partialSubtotal'] as num?;
  if (total == null) {
    return verifiedBucket ? 'Not yet verified' : '—';
  }
  final incomplete = scoring['incomplete'] == true;
  final base = '${total.toStringAsFixed(2)} / ${max.toStringAsFixed(0)}';
  if (verifiedBucket && (partialOnly || incomplete)) {
    return '$base (partial)';
  }
  return base;
}

/// Detailed lines for collapsed “View calculation”.
List<String> criterionACalculationDetailLines(Map<String, dynamic>? scoring) {
  if (scoring == null) return const ['No processed data yet.'];
  if (scoring['calculationUnavailable'] == true) {
    return [scoring['incompleteReason']?.toString() ?? 'No eligible ratings for calculation.'];
  }
  final lines = <String>[];
  final setN = scoring['setCount'] ?? 0;
  final sefN = scoring['sefCount'] ?? 0;
  lines.add('SET ratings used: $setN · SEF ratings used: $sefN');
  final avail = scoring['availabilitySummary'] as String?;
  if (avail != null && avail.isNotEmpty) lines.add(avail);
  final formula = scoring['formula'] as Map<String, dynamic>?;
  if (formula != null) {
    if (formula['set'] != null) lines.add('SET: ${formula['set']}');
    if (formula['sef'] != null) lines.add('SEF: ${formula['sef']}');
    if (formula['criterionA'] != null) lines.add('Criterion A: ${formula['criterionA']}');
    if (formula['policy'] != null) lines.add('Policy: ${formula['policy']}');
  }
  final setPts = scoring['setPoints'];
  final sefPts = scoring['sefPoints'];
  if (setPts != null || sefPts != null) {
    lines.add(
      'Contributions — SET: ${setPts != null ? (setPts as num).toStringAsFixed(2) : '—'}, '
      'SEF: ${sefPts != null ? (sefPts as num).toStringAsFixed(2) : '—'}',
    );
  }
  if (scoring['incomplete'] == true) {
    final reason = scoring['incompleteReason'] ?? scoring['coverageNote'];
    if (reason != null) lines.add(reason.toString());
  }
  return lines;
}

bool validationFindingIsActionable(Map<String, dynamic> finding) {
  final outcome = (finding['outcome'] ?? '').toString().toLowerCase();
  return outcome == 'fail' || outcome == 'review';
}

String validationFindingFacultyText(Map<String, dynamic> finding) {
  final text = (finding['explanation'] ?? '').toString().trim();
  return text.isNotEmpty ? text : 'Please review this item with your evaluator.';
}