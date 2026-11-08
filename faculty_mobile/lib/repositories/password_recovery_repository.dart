import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

/// Local frontend recovery adapter (verification code documented in DEMO_ACCOUNTS.md).
class PasswordRecoveryRepository {
  static const _overridesKey = 'fl_password_overrides';
  static const _verificationCode = '123456';

  static const recognizedEmails = {
    'faculty@ustp.demo',
    'maria.santos@ustp.demo',
  };

  static Future<bool> isAvailable() async => true;

  static String? validateEmail(String email) {
    final em = email.trim();
    if (em.isEmpty) return 'Email address is required.';
    if (!em.contains('@') || !em.contains('.')) return 'Enter a valid email address.';
    if (!recognizedEmails.contains(em.toLowerCase())) {
      return 'No matching account was found. Contact your institution administrator.';
    }
    return null;
  }

  static String? verifyCode(String code) {
    final c = code.trim();
    if (c.isEmpty) return 'Verification code is required.';
    if (c != _verificationCode) return 'The code you entered is not valid.';
    return null;
  }

  static String? validateNewPassword(String password, String confirm) {
    if (password.isEmpty) return 'New password is required.';
    if (password.length < 8) return 'Password must be at least 8 characters.';
    final hasLetter = RegExp(r'[A-Za-z]').hasMatch(password);
    final hasDigit = RegExp(r'[0-9]').hasMatch(password);
    if (!hasLetter || !hasDigit) return 'Use at least one letter and one number.';
    if (password != confirm) return 'Passwords do not match.';
    return null;
  }

  static Future<bool> savePassword(String email, String password) async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_overridesKey);
    final map = raw != null ? (jsonDecode(raw) as Map<String, dynamic>) : <String, dynamic>{};
    map[email.trim().toLowerCase()] = password;
    await prefs.setString(_overridesKey, jsonEncode(map));
    return true;
  }

  static Future<String?> passwordForLogin(String email) async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_overridesKey);
    if (raw != null) {
      final map = jsonDecode(raw) as Map<String, dynamic>;
      final override = map[email.trim().toLowerCase()];
      if (override is String) return override;
    }
    return null;
  }
}
