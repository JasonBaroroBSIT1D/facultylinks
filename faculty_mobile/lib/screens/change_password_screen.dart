import 'dart:convert';

import 'package:flutter/material.dart';

import '../repositories/auth_repository.dart';
import '../services/api_client.dart';
import '../theme/app_spacing.dart';
import '../theme/app_theme.dart';
import '../widgets/auth_branding.dart';

class ChangePasswordScreen extends StatefulWidget {
  const ChangePasswordScreen({super.key});

  @override
  State<ChangePasswordScreen> createState() => _ChangePasswordScreenState();
}

class _ChangePasswordScreenState extends State<ChangePasswordScreen> {
  final _password = TextEditingController();
  final _confirm = TextEditingController();
  bool _obscure1 = true;
  bool _obscure2 = true;
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    _password.dispose();
    _confirm.dispose();
    super.dispose();
  }

  String? _validate(String password, String confirm) {
    if (password.isEmpty) return 'New password is required.';
    if (password.length < 8) return 'Password must be at least 8 characters.';
    final hasLetter = RegExp(r'[A-Za-z]').hasMatch(password);
    final hasDigit = RegExp(r'[0-9]').hasMatch(password);
    if (!hasLetter || !hasDigit) return 'Use at least one letter and one number.';
    if (password != confirm) return 'Passwords do not match.';
    return null;
  }

  Future<void> _submit() async {
    final err = _validate(_password.text, _confirm.text);
    if (err != null) {
      setState(() => _error = err);
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    final res = await ApiClient.postJson('/api/auth/change-password', {
      'newPassword': _password.text,
      'confirmPassword': _confirm.text,
    });
    if (!mounted) return;
    if (res.statusCode != 200) {
      final data = jsonDecode(res.body) as Map<String, dynamic>;
      setState(() {
        _loading = false;
        _error = data['error'] as String? ?? 'Could not save password.';
      });
      return;
    }
    final data = jsonDecode(res.body) as Map<String, dynamic>;
    final token = data['token'] as String?;
    if (token != null && token.isNotEmpty) {
      await ApiClient.saveToken(token);
    }
    await AuthRepository.setMustChangePassword(false);
    if (!mounted) return;
    Navigator.pushReplacementNamed(context, '/home');
  }

  Future<void> _signOut() async {
    await AuthRepository.logout();
    if (!mounted) return;
    Navigator.pushNamedAndRemoveUntil(context, '/login', (_) => false);
  }

  @override
  Widget build(BuildContext context) {
    final scale = MediaQuery.textScalerOf(context);
    return Scaffold(
      appBar: AppBar(title: const Text('Set Your New Password')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const AuthBrandingHeader(),
              const SizedBox(height: 16),
              Text(
                'You must choose a new password before continuing to your dashboard.',
                style: TextStyle(fontSize: scale.scale(15), color: AppColors.textMuted, height: 1.4),
              ),
              const SizedBox(height: 20),
              TextField(
                controller: _password,
                obscureText: _obscure1,
                decoration: InputDecoration(
                  labelText: 'New Password',
                  suffixIcon: IconButton(
                    icon: Icon(_obscure1 ? Icons.visibility_outlined : Icons.visibility_off_outlined),
                    onPressed: () => setState(() => _obscure1 = !_obscure1),
                  ),
                ),
              ),
              const SizedBox(height: FlSpacing.md),
              TextField(
                controller: _confirm,
                obscureText: _obscure2,
                decoration: InputDecoration(
                  labelText: 'Confirm New Password',
                  suffixIcon: IconButton(
                    icon: Icon(_obscure2 ? Icons.visibility_outlined : Icons.visibility_off_outlined),
                    onPressed: () => setState(() => _obscure2 = !_obscure2),
                  ),
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'At least 8 characters with one letter and one number.',
                style: TextStyle(fontSize: scale.scale(13), color: AppColors.textMuted),
              ),
              if (_error != null) ...[
                const SizedBox(height: 12),
                Text(_error!, style: const TextStyle(color: Color(0xFFC62828))),
              ],
              const SizedBox(height: 20),
              FilledButton(
                onPressed: _loading ? null : _submit,
                child: Text(_loading ? 'Saving…' : 'Save New Password'),
              ),
              TextButton(onPressed: _loading ? null : _signOut, child: const Text('Sign Out')),
            ],
          ),
        ),
      ),
    );
  }
}
