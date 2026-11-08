import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import '../services/api_client.dart';

class AuthRepository {
  static const _sessionKey = 'fl_mobile_session';

  static Future<bool> login(String email, String password) async {
    final res = await ApiClient.postJson('/api/auth/login', {
      'email': email.trim(),
      'password': password,
    });
    if (res.statusCode != 200) {
      return false;
    }
    final data = jsonDecode(res.body) as Map<String, dynamic>;
    final token = data['token'] as String?;
    final mail = (data['email'] as String?)?.trim().toLowerCase() ?? email.trim().toLowerCase();
    if (token == null || token.isEmpty) {
      return false;
    }
    await ApiClient.saveToken(token);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_sessionKey, mail);
    return true;
  }

  static Future<void> logout() async {
    try {
      await ApiClient.postJson('/api/auth/logout', {});
    } catch (_) {}
    await ApiClient.clearToken();
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_sessionKey);
  }

  static Future<String?> currentEmail() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_sessionKey);
  }
}
