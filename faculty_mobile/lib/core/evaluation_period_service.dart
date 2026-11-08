/// Shared evaluation period contract (matches `evaluation-period-service.js` / future API).
class EvaluationPeriodService {
  static const int contractVersion = 1;

  /// JSON field names under `institutionConfig.preparationPeriod` (demo storage key).
  static const fieldStart = 'start';
  static const fieldEnd = 'end';
  static const fieldReviewerAvailableFrom = 'reviewerAvailableFrom';

  static const statusUpcoming = 'Upcoming';
  static const statusOpen = 'Open';
  static const statusClosed = 'Closed';

  static DateTime dateOnly(DateTime d) => DateTime(d.year, d.month, d.day);

  static String computeStatus({
    required DateTime start,
    required DateTime end,
    DateTime? now,
  }) {
    final n = dateOnly(now ?? DateTime.now());
    final s = dateOnly(start);
    final e = dateOnly(end);
    if (n.isBefore(s)) return statusUpcoming;
    if (n.isAfter(e)) return statusClosed;
    return statusOpen;
  }

  static String? validateDates(DateTime start, DateTime end) {
    if (dateOnly(end).isBefore(dateOnly(start))) {
      return 'End date cannot be before the start date.';
    }
    return null;
  }

  static String reviewerScheduleLine({
    required DateTime? reviewerAvailableFrom,
    DateTime? now,
  }) {
    if (reviewerAvailableFrom == null) return 'Not configured';
    final n = now ?? DateTime.now();
    final from = dateOnly(reviewerAvailableFrom);
    final available = !n.isBefore(from);
    if (!available) {
      return 'Reviewer queue opens ${_readable(from)}';
    }
    return 'Reviewers may check documents from ${_readable(from)}';
  }

  static String _readable(DateTime d) =>
      '${_month(d.month)} ${d.day}, ${d.year}';

  static String _month(int m) {
    const names = [
      'January',
      'February',
      'March',
      'April',
      'May',
      'June',
      'July',
      'August',
      'September',
      'October',
      'November',
      'December',
    ];
    return names[m - 1];
  }

  static const facultyClosedHelper =
      'You can still prepare documents and check your estimated points outside this period.';
}
