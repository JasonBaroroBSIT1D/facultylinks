import 'package:flutter/material.dart';

import '../repositories/auth_repository.dart';
import '../repositories/mock_repository.dart';
import '../theme/app_theme.dart';
class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _email = TextEditingController();
  final _password = TextEditingController();
  bool _obscure = true;
  bool _loading = false;
  String? _error;

  Future<void> _submit() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    final ok = await AuthRepository.login(_email.text, _password.text);
    if (!ok) {
      setState(() {
        _loading = false;
        _error = 'Invalid credentials. See docs/DEMO_ACCOUNTS.md';
      });
      return;
    }
    if (_email.text.contains('maria.santos')) {
      final repo = await MockRepository.load();
      await repo.resetEmptyProfile();
    }
    if (!mounted) return;
    Navigator.pushReplacementNamed(context, '/home');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [AppColors.navyDeep, AppColors.primaryBlue],
          ),
        ),
        child: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(24),
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Text.rich(TextSpan(children: [
                        const TextSpan(text: 'Faculty', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 22)),
                        TextSpan(text: 'Link', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 22, color: Theme.of(context).colorScheme.primary)),
                      ])),
                      const SizedBox(height: 4),
                      const Text('Faculty mobile portal'),
                      const SizedBox(height: 20),
                      TextField(controller: _email, decoration: const InputDecoration(labelText: 'Email')),
                      const SizedBox(height: 12),
                      TextField(
                        controller: _password,
                        obscureText: _obscure,
                        decoration: InputDecoration(
                          labelText: 'Password',
                          suffixIcon: IconButton(
                            icon: Icon(_obscure ? Icons.visibility : Icons.visibility_off),
                            onPressed: () => setState(() => _obscure = !_obscure),
                          ),
                        ),
                      ),
                      if (_error != null) ...[
                        const SizedBox(height: 8),
                        Text(_error!, style: const TextStyle(color: Colors.red)),
                      ],
                      const SizedBox(height: 16),
                      FilledButton(
                        onPressed: _loading ? null : _submit,
                        child: Text(_loading ? 'Signing in…' : 'Sign in'),
                      ),
                      TextButton(onPressed: () => Navigator.pushNamed(context, '/forgot'), child: const Text('Forgot password')),
                      const Text('Demonstration auth — not production security.', style: TextStyle(fontSize: 12, color: Colors.grey)),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
