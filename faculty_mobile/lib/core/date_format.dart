const _months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/// Friendly date for faculty-facing screens (e.g. Jan 15, 2026).
String formatFacultyDate(DateTime d) => '${_months[d.month - 1]} ${d.day}, ${d.year}';
