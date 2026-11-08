import 'dart:convert';

import '../services/api_client.dart';

class PasswordRecoveryRepository {
  static Future<bool> isAvailable() async => true;

  static String? validateEmail(String email) {
    final em = email.trim();
    if (em.isEmpty) return 'Email address is required.';
    if (!em.contains('@') || !em.contains('.')) return 'Enter a valid email address.';
    return null;
  }

  static Future<String> requestCode(String email) async {
    final res = await ApiClient.postJson('/api/auth/password-recovery/request', {'email': email.trim()});
    final data = jsonDecode(res.body) as Map<String, dynamic>;
    if (res.statusCode != 200) {
      throw Exception(data['error'] as String? ?? 'Could not send verification code.');
    }
    return data['message'] as String? ?? 'If an eligible account exists, a verification code will be sent.';
  }

  static Future<String> verifyCode(String email, String code) async {
    final res = await ApiClient.postJson('/api/auth/password-recovery/verify', {
      'email': email.trim(),
      'code': code.trim(),
    });
    final data = jsonDecode(res.body) as Map<String, dynamic>;
    if (res.statusCode != 200) {
      throw Exception(data['error'] as String? ?? 'Invalid or expired verification code.');
    }
    final token = data['resetToken'] as String?;
    if (token == null || token.isEmpty) {
      throw Exception('Invalid or expired verification code.');
    }
    return token;
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

  static Future<void> completeReset(String resetToken, String password, String confirm) async {
    final res = await ApiClient.postJson('/api/auth/password-recovery/complete', {
      'resetToken': resetToken,
      'newPassword': password,
      'confirmPassword': confirm,
    });
    final data = jsonDecode(res.body) as Map<String, dynamic>;
    if (res.statusCode != 200) {
      throw Exception(data['error'] as String? ?? 'Could not update password.');
    }
  }
}
