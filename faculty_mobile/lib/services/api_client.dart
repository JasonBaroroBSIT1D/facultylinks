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

  static Future<http.Response> postJson(String path, Map<String, dynamic> body) async {
    return http.post(
      ApiConfig.uri(path),
      headers: await headers(),
      body: jsonEncode(body),
    );
  }

  static Future<http.Response> get(String path) async {
    return http.get(ApiConfig.uri(path), headers: await headers(jsonBody: false));
  }

  static Future<http.Response> putJson(String path, Map<String, dynamic> body) async {
    return http.put(
      ApiConfig.uri(path),
      headers: await headers(),
      body: jsonEncode(body),
    );
  }
}
