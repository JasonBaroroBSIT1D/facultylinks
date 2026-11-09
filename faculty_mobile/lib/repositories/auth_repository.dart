import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import '../services/api_client.dart';

class LoginResult {
  final bool success;
  final String? errorMessage;
  final bool mustChangePassword;

  const LoginResult.success({required this.mustChangePassword})
      : success = true,
        errorMessage = null;

  const LoginResult.failure(this.errorMessage)
      : success = false,
        mustChangePassword = false;
}

class AuthRepository {
  static const _sessionKey = 'fl_mobile_session';
  static const _mustChangeKey = 'fl_must_change_password';

  static Future<LoginResult> login(String email, String password) async {
    try {
      final res = await ApiClient.postJson('/api/auth/login', {
        'email': email.trim(),
        'password': password,
      });
      if (res.statusCode != 200) {
        return const LoginResult.failure('Invalid email or password.');
      }
      final data = jsonDecode(res.body) as Map<String, dynamic>;
      final token = data['token'] as String?;
      final mail = (data['email'] as String?)?.trim().toLowerCase() ?? email.trim().toLowerCase();
      final user = data['user'] as Map<String, dynamic>?;
      if (token == null || token.isEmpty) {
        return const LoginResult.failure('Invalid email or password.');
      }
      await ApiClient.saveToken(token);
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_sessionKey, mail);
      final mustChange = user?['mustChangePassword'] == true;
      await prefs.setBool(_mustChangeKey, mustChange);
      return LoginResult.success(mustChangePassword: mustChange);
    } on TimeoutException catch (e) {
      return LoginResult.failure(ApiClient.describeConnectionError(e));
    } on http.ClientException catch (e) {
      return LoginResult.failure(ApiClient.describeConnectionError(e));
    } catch (e) {
      return LoginResult.failure(ApiClient.describeConnectionError(e));
    }
  }

  static Future<bool> mustChangePassword() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_mustChangeKey) ?? false;
  }

  static Future<void> setMustChangePassword(bool value) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_mustChangeKey, value);
  }

  static Future<Map<String, dynamic>?> fetchMe() async {
    final res = await ApiClient.get('/api/auth/me');
    if (res.statusCode != 200) return null;
    final data = jsonDecode(res.body) as Map<String, dynamic>;
    final user = data['user'] as Map<String, dynamic>?;
    if (user != null) {
      await setMustChangePassword(user['mustChangePassword'] == true);
    }
    return user;
  }

  static Future<void> logout() async {
    try {
      await ApiClient.postJson('/api/auth/logout', {});
    } catch (_) {}
    await ApiClient.clearToken();
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_sessionKey);
    await prefs.remove(_mustChangeKey);
  }

  static Future<String?> currentEmail() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_sessionKey);
  }
}
