/// Shared evaluation period contract (matches `evaluation-period-service.js` / API).
class EvaluationPeriodService {
  static const int contractVersion = 1;

  /// JSON field names under `institutionConfig.preparationPeriod` (demo storage key).
  static const fieldStart = 'start';
  static const fieldEnd = 'end';
  static const fieldReviewerAvailableFrom = 'reviewerAvailableFrom';

  static const statusUpcoming = 'Upcoming';
  static const statusOpen = 'Open';
  static const statusClosed = 'Closed';

  static const facultyClosedHelper =
      'Review period closed. You can still prepare and upload your documents.';

  static DateTime dateOnly(DateTime d) => DateTime(d.year, d.month, d.day);

  /// Asia/Manila calendar day (UTC+8, no DST).
  static DateTime manilaCalendarDay([DateTime? when]) {
    final utc = (when ?? DateTime.now()).toUtc();
    final manila = utc.add(const Duration(hours: 8));
    return DateTime(manila.year, manila.month, manila.day);
  }

  static String isoDay(DateTime d) {
    final y = d.year.toString().padLeft(4, '0');
    final m = d.month.toString().padLeft(2, '0');
    final day = d.day.toString().padLeft(2, '0');
    return '$y-$m-$day';
  }

  static String computeStatus({
    required DateTime start,
    required DateTime end,
    DateTime? now,
  }) {
    final today = isoDay(manilaCalendarDay(now));
    final s = isoDay(dateOnly(start));
    final e = isoDay(dateOnly(end));
    if (today.compareTo(s) < 0) return statusUpcoming;
    if (today.compareTo(e) > 0) return statusClosed;
    return statusOpen;
  }

  static String? validateDates(DateTime start, DateTime end) {
    if (dateOnly(end).isBefore(dateOnly(start))) {
      return 'End date cannot be before the start date.';
    }
    return null;
  }

  static ReviewWindow computeReviewerReviewWindow({
    required DateTime start,
    required DateTime end,
    DateTime? reviewerAvailableFrom,
    DateTime? now,
  }) {
    final startIso = isoDay(dateOnly(start));
    final endIso = isoDay(dateOnly(end));
    final ra =
        reviewerAvailableFrom != null ? isoDay(dateOnly(reviewerAvailableFrom)) : '';
    final first = ra.isNotEmpty
        ? (ra.compareTo(startIso) > 0 ? ra : startIso)
        : startIso;
    final today = isoDay(manilaCalendarDay(now));

    if (today.compareTo(first) < 0) {
      final label = _readableIso(first);
      return ReviewWindow(
        allowed: false,
        state: 'upcoming',
        message: 'Review opens $label.',
        opensOn: first,
        endsOn: endIso,
      );
    }
    if (today.compareTo(endIso) > 0) {
      return ReviewWindow(
        allowed: false,
        state: 'closed',
        message: 'Review period has ended.',
        opensOn: first,
        endsOn: endIso,
      );
    }
    return ReviewWindow(
      allowed: true,
      state: 'open',
      message: null,
      opensOn: first,
      endsOn: endIso,
    );
  }

  static ReviewWindow? parseReviewWindow(Map<String, dynamic>? json) {
    if (json == null) return null;
    final allowed = json['allowed'];
    if (allowed is! bool) return null;
    return ReviewWindow(
      allowed: allowed,
      state: json['state'] as String? ?? (allowed ? 'open' : 'closed'),
      message: json['message'] as String?,
      opensOn: json['opensOn'] as String?,
      endsOn: json['endsOn'] as String?,
    );
  }

  static ReviewWindow resolveReviewWindow({
    required DateTime start,
    required DateTime end,
    DateTime? reviewerAvailableFrom,
    ReviewWindow? serverWindow,
    DateTime? now,
  }) {
    if (serverWindow != null && serverWindow.endsOn != null && serverWindow.endsOn!.isNotEmpty) {
      return serverWindow;
    }
    return computeReviewerReviewWindow(
      start: start,
      end: end,
      reviewerAvailableFrom: reviewerAvailableFrom,
      now: now,
    );
  }

  static String reviewerScheduleLine({
    required DateTime start,
    required DateTime end,
    DateTime? reviewerAvailableFrom,
    ReviewWindow? reviewWindow,
    DateTime? now,
  }) {
    final win = resolveReviewWindow(
      start: start,
      end: end,
      reviewerAvailableFrom: reviewerAvailableFrom,
      serverWindow: reviewWindow,
      now: now,
    );
    if (win.state == 'upcoming') {
      return win.message ?? 'Review opens soon.';
    }
    if (win.state == 'closed') {
      return 'Review period closed.';
    }
    if (win.state == 'unconfigured') {
      return 'Not configured';
    }
    final endLabel = win.endsOn != null ? _readableIso(win.endsOn!) : _readable(dateOnly(end));
    return 'Reviewers may submit decisions through $endLabel';
  }

  static bool reviewPeriodClosed({
    required DateTime start,
    required DateTime end,
    DateTime? reviewerAvailableFrom,
    ReviewWindow? reviewWindow,
    DateTime? now,
  }) {
    final win = resolveReviewWindow(
      start: start,
      end: end,
      reviewerAvailableFrom: reviewerAvailableFrom,
      serverWindow: reviewWindow,
      now: now,
    );
    return win.state == 'closed';
  }

  static String _readable(DateTime d) => '${_month(d.month)} ${d.day}, ${d.year}';

  static String _readableIso(String iso) {
    if (iso.length < 10) return iso;
    final d = DateTime.tryParse(iso.substring(0, 10));
    if (d == null) return iso;
    return _readable(d);
  }

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
}

class ReviewWindow {
  final bool allowed;
  final String state;
  final String? message;
  final String? opensOn;
  final String? endsOn;

  const ReviewWindow({
    required this.allowed,
    required this.state,
    this.message,
    this.opensOn,
    this.endsOn,
  });

  factory ReviewWindow.fromJson(Map<String, dynamic> j) => ReviewWindow(
        allowed: j['allowed'] as bool? ?? false,
        state: j['state'] as String? ?? 'closed',
        message: j['message'] as String?,
        opensOn: j['opensOn'] as String?,
        endsOn: j['endsOn'] as String?,
      );
}