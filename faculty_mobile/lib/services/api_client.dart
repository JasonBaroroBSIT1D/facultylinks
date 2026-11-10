import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart' show kDebugMode, debugPrint;
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import '../core/api_config.dart';

class ApiClient {
  static const _tokenKey = 'fl_api_token';

  static Future<void> saveToken(String token) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_tokenKey, token);
  }

  static Future<String?> token() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_tokenKey);
  }

  static Future<void> clearToken() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_tokenKey);
  }

  static Future<Map<String, String>> headers({bool jsonBody = true}) async {
    final h = <String, String>{
      'X-Client-Type': 'faculty_mobile',
      if (jsonBody) 'Content-Type': 'application/json',
    };
    final t = await token();
    if (t != null && t.isNotEmpty) {
      h['Authorization'] = 'Bearer $t';
    }
    return h;
  }

  static Future<http.Response> postJson(
    String path,
    Map<String, dynamic> body, {
    Duration timeout = ApiConfig.requestTimeout,
  }) async {
    return http
        .post(
          ApiConfig.uri(path),
          headers: await headers(),
          body: jsonEncode(body),
        )
        .timeout(timeout);
  }

  static Future<http.Response> get(
    String path, {
    Duration timeout = ApiConfig.requestTimeout,
  }) async {
    return http.get(ApiConfig.uri(path), headers: await headers(jsonBody: false)).timeout(timeout);
  }

  static Future<http.Response> putJson(
    String path,
    Map<String, dynamic> body, {
    Duration timeout = ApiConfig.requestTimeout,
  }) async {
    return http
        .put(
          ApiConfig.uri(path),
          headers: await headers(),
          body: jsonEncode(body),
        )
        .timeout(timeout);
  }

  /// Shown on login and other flows when the API cannot be reached.
  static const String userConnectionMessage =
      'Cannot connect to the server. Check your connection and try again.';

  /// True when the HTTP transport failed before a response (not wrong password / 4xx).
  static bool isConnectionFailure(Object error) {
    if (error is TimeoutException) return true;
    if (error is http.ClientException) return true;
    final name = error.runtimeType.toString();
    return name.contains('SocketException') || name.contains('HandshakeException');
  }

  static void logConnectionDiagnostics(Object error, {String? context}) {
    if (!kDebugMode) return;
    final resolved = ApiConfig.resolve();
    final category = error.runtimeType.toString();
    final buffer = StringBuffer(
      '[FacultyLink API] ${context ?? 'request'} failed\n'
      'category=$category\n'
      'resolved baseUrl=${resolved.url} source=${resolved.source}\n'
      'error=$error',
    );
    if (error is TimeoutException) {
      buffer.write('\nHint: API timeout — is Flask listening on 0.0.0.0:5000 and reachable on Wi‑Fi?');
    }
    if (error is http.ClientException) {
      final msg = error.message.toLowerCase();
      if (msg.contains('failed to fetch') || msg.contains('xmlhttprequest')) {
        buffer.write(
          '\nHint (Flutter web only): add your web dev origin to backend CORS_ORIGINS.',
        );
      }
      if (msg.contains('connection refused') || msg.contains('network is unreachable')) {
        buffer.write(
          '\nHint (physical Android): rebuild with '
          '--dart-define-from-file=config/dart_defines.local.json',
        );
      }
      if (msg.contains('no route to host') || msg.contains('host is unreachable')) {
        buffer.write(
          '\nHint: Phone cannot reach the PC on Wi‑Fi — use the same LAN (not mobile data), '
          'open http://<PC-IP>:5000/api/health in the phone browser, disable AP isolation, '
          'or use USB: adb reverse tcp:5000 tcp:5000 then FACULTYLINK_API_BASE=http://127.0.0.1:5000',
        );
      }
    }
    debugPrint(buffer.toString());
  }
}
