import 'package:flutter/material.dart';

import '../repositories/auth_repository.dart';
import '../theme/app_spacing.dart';
import '../theme/app_theme.dart';
import '../widgets/auth_branding.dart';

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

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final em = _email.text.trim();
    if (em.isEmpty || _password.text.isEmpty) {
      setState(() => _error = 'Email address and password are required.');
      return;
    }
    if (!em.contains('@')) {
      setState(() => _error = 'Enter a valid email address.');
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    final ok = await AuthRepository.login(_email.text, _password.text);
    if (!ok) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = 'Invalid email or password.';
      });
      return;
    }
    if (!mounted) return;
    Navigator.pushReplacementNamed(context, '/home');
  }

  @override
  Widget build(BuildContext context) {
    final scale = MediaQuery.textScalerOf(context);

    return Scaffold(
      resizeToAvoidBottomInset: true,
      body: DecoratedBox(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [AppColors.navyDeep, AppColors.primaryBlue],
          ),
        ),
        child: SafeArea(
          child: LayoutBuilder(
            builder: (context, constraints) {
              return SingleChildScrollView(
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
                child: ConstrainedBox(
                  constraints: BoxConstraints(minHeight: constraints.maxHeight - 32),
                  child: Column(
                    children: [
                      const SizedBox(height: 4),
                      const AuthBrandingHeader(onDark: true),
                      const SizedBox(height: 16),
                      DecoratedBox(
                        decoration: BoxDecoration(
                          color: AppColors.cardWhite,
                          borderRadius: BorderRadius.circular(FlLayout.cardRadius),
                          border: Border.all(color: AppColors.border),
                          boxShadow: [
                            BoxShadow(
                              color: AppColors.navyDeep.withValues(alpha: 0.1),
                              blurRadius: 16,
                              offset: const Offset(0, 6),
                            ),
                          ],
                        ),
                        child: Padding(
                          padding: const EdgeInsets.all(22),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              Text(
                                'Welcome back.',
                                style: TextStyle(
                                  fontSize: scale.scale(24),
                                  fontWeight: FontWeight.w700,
                                  color: AppColors.navyDeep,
                                ),
                              ),
                              const SizedBox(height: 6),
                              Text(
                                'Sign in to your FacultyLink account.',
                                style: TextStyle(fontSize: scale.scale(16), color: AppColors.textMuted, height: 1.4),
                              ),
                              const SizedBox(height: 20),
                              TextField(
                                controller: _email,
                                keyboardType: TextInputType.emailAddress,
                                autofillHints: const [AutofillHints.email],
                                textInputAction: TextInputAction.next,
                                decoration: const InputDecoration(
                                  labelText: 'Email Address',
                                  prefixIcon: Icon(Icons.mail_outline),
                                ),
                              ),
                              const SizedBox(height: 12),
                              TextField(
                                controller: _password,
                                obscureText: _obscure,
                                autofillHints: const [AutofillHints.password],
                                textInputAction: TextInputAction.done,
                                onSubmitted: (_) => _loading ? null : _submit(),
                                decoration: InputDecoration(
                                  labelText: 'Password',
                                  prefixIcon: const Icon(Icons.lock_outline),
                                  suffixIcon: IconButton(
                                    tooltip: _obscure ? 'Show password' : 'Hide password',
                                    icon: Icon(_obscure ? Icons.visibility_outlined : Icons.visibility_off_outlined),
                                    onPressed: () => setState(() => _obscure = !_obscure),
                                  ),
                                ),
                              ),
                              if (_error != null) ...[
                                const SizedBox(height: 10),
                                Text(_error!, style: const TextStyle(color: Color(0xFFC62828), fontSize: 15)),
                              ],
                              const SizedBox(height: 18),
                              SizedBox(
                                height: 50,
                                child: FilledButton(
                                  onPressed: _loading ? null : _submit,
                                  child: _loading
                                      ? const SizedBox(
                                          width: 22,
                                          height: 22,
                                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                                        )
                                      : const Text('Sign In'),
                                ),
                              ),
                              const SizedBox(height: 8),
                              Align(
                                alignment: Alignment.centerLeft,
                                child: TextButton(
                                  onPressed: () => Navigator.pushNamed(context, '/forgot'),
                                  child: const Text('Forgot Password?'),
                                ),
                              ),
                              const Divider(height: 28),
                              TextButton(
                                onPressed: () => showInstitutionAdminContact(context),
                                child: const Text('Contact Institution Admin'),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              );
            },
          ),
        ),
      ),
    );
  }
}
