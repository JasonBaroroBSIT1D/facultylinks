import 'package:flutter_test/flutter_test.dart';

import 'package:faculty_mobile/repositories/mock_repository.dart';

void main() {
  test('fromJson maps achievement display without overwriting reviewStatus', () {
    final doc = FacultyDocument.fromJson({
      'id': 'doc-uuid-1',
      'indicatorId': 'kra-I-B-1-1',
      'kraId': 'kra-I',
      'fileName': 'textbook.pdf',
      'reviewStatus': 'pending',
      'displayStatus': 'part_of_approved_achievement',
      'displayStatusLabel': 'Part of approved achievement',
      'linkedAchievementId': 'ach-1',
      'criterionId': 'kra-I-B',
      'parentReviewStatus': 'approved',
      'parentSubmissionStatus': 'submitted',
      'achievementLinks': [
        {
          'linkedAchievementId': 'ach-1',
          'criterionId': 'kra-I-B',
          'parentReviewStatus': 'approved',
          'parentSubmissionStatus': 'submitted',
          'parentAchievementTitle': 'Textbook',
          'achievementRemarks': 'Well documented.',
        }
      ],
    });
    expect(doc.reviewStatus, 'pending');
    expect(doc.displayStatusLabel, 'Part of approved achievement');
    expect(doc.filterBucket, 'approved');
    expect(doc.countsAsPendingForFaculty, false);
  });

  test('criterion A keeps document review status bucket', () {
    final doc = FacultyDocument.fromJson({
      'id': 'set-1',
      'indicatorId': 'kra-I-A-setsef-eval',
      'kraId': 'kra-I',
      'fileName': 'eval.pdf',
      'reviewStatus': 'pending',
    });
    expect(doc.displayStatus, isNull);
    expect(doc.filterBucket, 'pending');
  });
}
