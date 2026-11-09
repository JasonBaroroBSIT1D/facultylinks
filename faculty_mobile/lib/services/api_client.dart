import 'dart:async';
import 'dart:convert';

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

  /// User-facing message for CORS, offline API, and timeout failures (Flutter web/Android).
  static String describeConnectionError(Object error) {
    if (error is TimeoutException) {
      return 'Connection timed out after ${ApiConfig.requestTimeout.inSeconds}s. '
          'Check that the FacultyLink API is running at ${ApiConfig.baseUrl}.';
    }
    if (error is http.ClientException) {
      final msg = error.message.toLowerCase();
      if (msg.contains('failed to fetch') ||
          msg.contains('xmlhttprequest') ||
          msg.contains('connection refused') ||
          msg.contains('network is unreachable')) {
        return 'Cannot reach the FacultyLink API at ${ApiConfig.baseUrl}. '
            'Verify the backend is running and that your app origin is listed in backend CORS_ORIGINS '
            '(for Flutter web use port 49932 — see faculty_mobile/README.md).';
      }
      return 'Network error while contacting the API. (${error.message})';
    }
    return 'Could not sign in due to a connection problem. Try again.';
  }
}
