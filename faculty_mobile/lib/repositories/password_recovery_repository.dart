import 'dart:convert';

import '../services/api_client.dart';

enum RecoveryChannel { email, sms }

class PasswordRecoveryRepository {
  static Future<bool> isAvailable() async => true;

  static String? validateEmail(String email) {
    final em = email.trim();
    if (em.isEmpty) return 'Email address is required.';
    if (!em.contains('@') || !em.contains('.')) return 'Enter a valid email address.';
    return null;
  }

  static String? validatePhone(String phone) {
    final compact = phone.replaceAll(RegExp(r'[\s\-()]'), '');
    if (compact.isEmpty) return 'Mobile number is required.';
    final local = RegExp(r'^09\d{9}$');
    final intl = RegExp(r'^\+639\d{9}$');
    if (!local.hasMatch(compact) && !intl.hasMatch(compact)) {
      return 'Enter a valid Philippine mobile number (09XXXXXXXXX or +639XXXXXXXXX).';
    }
    return null;
  }

  static Future<String> requestCode({
    required RecoveryChannel channel,
    String? email,
    String? phone,
  }) async {
    final body = <String, dynamic>{
      'channel': channel == RecoveryChannel.sms ? 'sms' : 'email',
    };
    if (channel == RecoveryChannel.email) {
      body['email'] = (email ?? '').trim();
    } else {
      body['phone'] = (phone ?? '').trim();
    }
    final res = await ApiClient.postJson('/api/auth/password-recovery/request', body);
    final data = jsonDecode(res.body) as Map<String, dynamic>;
    if (res.statusCode != 200) {
      throw Exception(data['error'] as String? ?? 'Could not send verification code.');
    }
    return data['message'] as String? ?? 'If an eligible account exists, a verification code will be sent.';
  }

  static Future<String> verifyCode({
    required RecoveryChannel channel,
    required String code,
    String? email,
    String? phone,
  }) async {
    final body = <String, dynamic>{
      'channel': channel == RecoveryChannel.sms ? 'sms' : 'email',
      'code': code.trim(),
    };
    if (channel == RecoveryChannel.email) {
      body['email'] = (email ?? '').trim();
    } else {
      body['phone'] = (phone ?? '').trim();
    }
    final res = await ApiClient.postJson('/api/auth/password-recovery/verify', body);
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