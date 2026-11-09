import '../repositories/mock_repository.dart';

/// Readable OCR / processing line without duplicate labels (e.g. "completed · completed").
String documentProcessingSummary(FacultyDocument doc) {
  if (!doc.isSetSefOcr) return '';
  final ocr = _ocrLabel(doc.ocrStatus);
  final proc = _processingLabel(doc.processingStatus);
  if (proc == 'Not started') return 'OCR: $ocr';
  if (ocr.toLowerCase() == proc.toLowerCase()) return 'Processing: $ocr';
  return 'OCR: $ocr · $proc';
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
  if (scoring['incomplete'] == true) {
    return 'Incomplete — ${scoring['incompleteReason'] ?? 'Not enough semester ratings.'}';
  }
  final total = scoring['criterionAPoints'];
  if (total == null) return 'Not available yet';
  return '${(total as num).toStringAsFixed(2)} / 60';
}
