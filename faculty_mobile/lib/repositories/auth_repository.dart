import 'package:shared_preferences/shared_preferences.dart';

import 'password_recovery_repository.dart';

class AuthRepository {
  static const _sessionKey = 'fl_mobile_session';

  static const demoUsers = {
    'faculty@ustp.demo': 'Faculty@2026',
    'maria.santos@ustp.demo': 'Faculty@2026',
  };

  static Future<bool> login(String email, String password) async {
    await Future.delayed(const Duration(milliseconds: 500));
    final key = email.trim().toLowerCase();
    final override = await PasswordRecoveryRepository.passwordForLogin(key);
    final pw = override ?? demoUsers[key];
    if (pw == null || pw != password) return false;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_sessionKey, email.trim().toLowerCase());
    return true;
  }

  static Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_sessionKey);
  }

  static Future<String?> currentEmail() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_sessionKey);
  }
}
