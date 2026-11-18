import '../repositories/mock_repository.dart';

/// Readable OCR / processing line without duplicate labels (e.g. "completed · completed").
String documentProcessingSummary(FacultyDocument doc) {
  final ocrRaw = doc.ocrStatus;
  final procRaw = doc.processingStatus;
  if ((ocrRaw.isEmpty || ocrRaw == 'none') && (procRaw.isEmpty || procRaw == 'none')) {
    return '';
  }
  final ocr = _ocrLabel(ocrRaw);
  final proc = _processingLabel(procRaw);
  if (proc == 'Not started') return 'OCR: $ocr';
  if (ocr.toLowerCase() == proc.toLowerCase()) return 'Processing: $ocr';
  return 'OCR: $ocr · $proc';
}

/// Faculty-facing status without raw engine errors.
String documentProcessingFacultyMessage(FacultyDocument doc) {
  switch (doc.ocrStatus) {
    case 'failed':
      return 'We could not read text from this file. Try a clearer scan or PDF.';
    case 'review_required':
      return 'Text was extracted for reviewer checks.';
    case 'completed':
      return 'Text extraction completed.';
    case 'pending':
    case 'processing':
    case 'queued':
      return 'Document text is still being processed.';
    default:
      return documentProcessingSummary(doc);
  }
}

String _ocrLabel(String? s) {
  switch (s) {
    case 'queued':
      return 'Queued';
    case 'processing':
      return 'Processing';
    case 'completed':
      return 'Completed';
    case 'failed':
      return 'Failed';
    case 'review_required':
      return 'Needs review';
    case 'pending':
      return 'Pending';
    default:
      return s?.isNotEmpty == true ? s! : '—';
  }
}

String _processingLabel(String? s) {
  if (s == null || s.isEmpty || s == 'none') return 'Not started';
  return s[0].toUpperCase() + s.substring(1);
}

String formatCriterionAScoring(Map<String, dynamic>? scoring) {
  if (scoring == null) return 'Not available yet';
  if (scoring['calculationUnavailable'] == true) {
    return 'Unavailable — ${scoring['incompleteReason'] ?? 'No eligible ratings.'}';
  }
  final setN = scoring['setCount'] ?? 0;
  final sefN = scoring['sefCount'] ?? 0;
  final slots = (scoring['availabilitySummary'] as String?) ??
      'SET: $setN ratings available · SEF: $sefN ratings available';
  final total = scoring['criterionAPoints'] ?? scoring['partialSubtotal'];
  if (total == null) return 'Not available yet ($slots)';
  final note = scoring['incomplete'] == true ? ' · coverage incomplete' : '';
  return '${(total as num).toStringAsFixed(2)} / 60 ($slots)$note';
}
