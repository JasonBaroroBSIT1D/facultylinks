import 'package:flutter/foundation.dart' show debugPrint, kDebugMode, kIsWeb;

/// Backend API base.
///
/// Override at build/run time:
/// - Full URL: `--dart-define=FACULTYLINK_API_BASE=http://192.168.1.10:5000`
/// - LAN host only (port 5000 default):
///   `--dart-define=FACULTYLINK_DEV_LAN_HOST=192.168.1.10`
/// - Optional port: `--dart-define=FACULTYLINK_DEV_LAN_PORT=5000`
///
/// Flutter **web** defaults to `http://127.0.0.1:5000` when unset (use with `--web-port`).
/// **Android/iOS** on a physical device must set one of the defines above — `127.0.0.1`
/// is the device itself, not your development PC.
class ApiConfig {
  static const String _apiBaseOverride = String.fromEnvironment(
    'FACULTYLINK_API_BASE',
    defaultValue: '',
  );

  /// PC LAN IP (no scheme), e.g. `192.168.1.23` — used when [_apiBaseOverride] is empty.
  static const String _devLanHost = String.fromEnvironment(
    'FACULTYLINK_DEV_LAN_HOST',
    defaultValue: '',
  );

  static const int _devLanPort = int.fromEnvironment(
    'FACULTYLINK_DEV_LAN_PORT',
    defaultValue: 5000,
  );

  /// With `adb reverse tcp:5000 tcp:5000`, the phone’s 127.0.0.1:5000 reaches the PC API.
  static const bool _adbReverse = bool.fromEnvironment(
    'FACULTYLINK_ADB_REVERSE',
    defaultValue: false,
  );

  static String get baseUrl => resolve().url;

  static ApiBaseResolution resolve() {
    if (_adbReverse && !kIsWeb) {
      return const ApiBaseResolution(
        url: 'http://127.0.0.1:5000',
        source: 'FACULTYLINK_ADB_REVERSE',
      );
    }
    final full = _apiBaseOverride.trim();
    if (full.isNotEmpty) {
      return ApiBaseResolution(
        url: _stripTrailingSlash(full),
        source: 'FACULTYLINK_API_BASE',
      );
    }
    if (kIsWeb) {
      return const ApiBaseResolution(
        url: 'http://127.0.0.1:5000',
        source: 'default_web_loopback',
      );
    }
    final host = _devLanHost.trim();
    if (host.isNotEmpty) {
      return ApiBaseResolution(
        url: 'http://$host:$_devLanPort',
        source: 'FACULTYLINK_DEV_LAN_HOST',
      );
    }
    return const ApiBaseResolution(
      url: 'http://127.0.0.1:5000',
      source: 'default_mobile_loopback',
    );
  }

  /// Logs resolved base URL and compile-time source (no secrets).
  static void logResolvedBase() {
    if (!kDebugMode) return;
    final r = resolve();
    debugPrint('[FacultyLink API] resolved baseUrl=${r.url} source=${r.source}');
    if (!kIsWeb && r.source == 'default_mobile_loopback') {
      debugPrint(
        '[FacultyLink API] WARNING: 127.0.0.1 on a physical device is the phone itself. '
        'Rebuild with --dart-define-from-file=config/dart_defines.local.json '
        'or --dart-define=FACULTYLINK_API_BASE=http://<PC-LAN-IP>:5000',
      );
    }
  }

  /// Default HTTP timeout for auth and API calls.
  static const Duration requestTimeout = Duration(seconds: 25);

  static Uri uri(String path) {
    final normalized = path.startsWith('/') ? path : '/$path';
    return Uri.parse('$baseUrl$normalized');
  }

  static String _stripTrailingSlash(String url) {
    return url.endsWith('/') ? url.substring(0, url.length - 1) : url;
  }
}

class ApiBaseResolution {
  final String url;
  final String source;

  const ApiBaseResolution({required this.url, required this.source});
}
