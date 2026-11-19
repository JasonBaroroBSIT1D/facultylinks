import 'package:faculty_mobile/core/evaluation_period_service.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  final start = DateTime(2026, 10, 1);
  final end = DateTime(2026, 11, 18);
  final revFrom = DateTime(2026, 10, 15);

  test('review window last day open, next Manila day closed', () {
    final last = EvaluationPeriodService.computeReviewerReviewWindow(
      start: start,
      end: end,
      reviewerAvailableFrom: revFrom,
      now: DateTime.utc(2026, 11, 18, 10),
    );
    expect(last.allowed, isTrue);

    final closed = EvaluationPeriodService.computeReviewerReviewWindow(
      start: start,
      end: end,
      reviewerAvailableFrom: revFrom,
      now: DateTime.utc(2026, 11, 18, 17), // Nov 19 01:00 Manila
    );
    expect(closed.state, 'closed');
    expect(closed.allowed, isFalse);
  });

  test('evaluation status uses Manila calendar', () {
    final periodEnd = DateTime(2026, 3, 20);
    expect(
      EvaluationPeriodService.computeStatus(
        start: DateTime(2026, 3, 10),
        end: periodEnd,
        now: DateTime.utc(2026, 3, 20, 16),
      ),
      EvaluationPeriodService.statusClosed,
    );
  });
}