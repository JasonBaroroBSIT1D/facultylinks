/// Backend API base — override with `--dart-define=FACULTYLINK_API_BASE=https://...`
class ApiConfig {
  static const String baseUrl = String.fromEnvironment(
    'FACULTYLINK_API_BASE',
    defaultValue: 'http://127.0.0.1:5000',
  );

  static Uri uri(String path) {
    final normalized = path.startsWith('/') ? path : '/$path';
    return Uri.parse('$baseUrl$normalized');
  }
}
