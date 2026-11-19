import 'package:flutter_test/flutter_test.dart';

import 'package:faculty_mobile/core/document_status.dart';
import 'package:faculty_mobile/repositories/mock_repository.dart';

void main() {
  test('reading status maps processing separately from reviewer', () {
    final doc = FacultyDocument(
      id: '1',
      indicatorId: 'kra-I-A-setsef-eval',
      kraId: 'kra-I',
      fileName: 'a.pdf',
      ocrStatus: 'review_required',
      processingStatus: 'completed',
      documentKind: 'set_sef_unified',
    );
    expect(documentReadingStatusLabel(doc), 'Completed');
    expect(documentReviewerStatusLabel(doc), 'Awaiting review');
  });

  test('KRA I 58.92 score formatting', () {
    final scoring = {
      'criterionAPoints': 58.92,
      'maxima': {'criterionA': 60},
      'incomplete': false,
    };
    expect(formatDocumentCriterionAScore(scoring, verifiedBucket: false), '58.92 / 60');
  });

  test('partial verified shows partial label', () {
    final scoring = {
      'partialSubtotal': 45.0,
      'maxima': {'criterionA': 60},
      'incomplete': true,
    };
    expect(formatDocumentCriterionAScore(scoring, verifiedBucket: true), '45.00 / 60 (partial)');
    expect(formatDocumentCriterionAScore(scoring, verifiedBucket: false), '45.00 / 60');
  });

  test('SET and SEF counts differ in calculation detail', () {
    final scoring = {
      'setCount': 2,
      'sefCount': 1,
      'availabilitySummary': 'SET: 2 · SEF: 1',
    };
    final lines = criterionACalculationDetailLines(scoring);
    expect(lines.first, contains('SET ratings used: 2'));
    expect(lines.first, contains('SEF ratings used: 1'));
  });
}