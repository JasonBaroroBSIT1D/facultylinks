import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../repositories/password_recovery_repository.dart';
import '../theme/app_spacing.dart';
import '../theme/app_theme.dart';
import '../widgets/auth_branding.dart';

class ForgotPasswordScreen extends StatefulWidget {
  const ForgotPasswordScreen({super.key});

  @override
  State<ForgotPasswordScreen> createState() => _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends State<ForgotPasswordScreen> {
  int _step = 1;
  bool _loading = false;
  bool _unavailable = false;
  bool _completed = false;
  String _resetToken = '';
  String _neutralMsg = 'If an eligible account exists, a verification code will be sent.';

  final _email = TextEditingController();
  final _code = TextEditingController();
  final _password = TextEditingController();
  final _confirm = TextEditingController();
  bool _obscure1 = true;
  bool _obscure2 = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    PasswordRecoveryRepository.isAvailable().then((ok) {
      if (!mounted) return;
      setState(() => _unavailable = !ok);
    });
  }

  @override
  void dispose() {
    _email.dispose();
    _code.dispose();
    _password.dispose();
    _confirm.dispose();
    super.dispose();
  }

  Future<void> _continueEmail() async {
    final err = PasswordRecoveryRepository.validateEmail(_email.text);
    setState(() => _error = err);
    if (err != null) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final msg = await PasswordRecoveryRepository.requestCode(_email.text);
      if (!mounted) return;
      setState(() {
        _loading = false;
        _step = 2;
        _neutralMsg = msg;
      });
    } catch (ex) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = ex.toString().replaceFirst('Exception: ', '');
      });
    }
  }

  Future<void> _verifyCode() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final token = await PasswordRecoveryRepository.verifyCode(_email.text, _code.text);
      if (!mounted) return;
      setState(() {
        _loading = false;
        _resetToken = token;
        _step = 3;
      });
    } catch (ex) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = ex.toString().replaceFirst('Exception: ', '');
      });
    }
  }

  Future<void> _savePassword() async {
    final err = PasswordRecoveryRepository.validateNewPassword(_password.text, _confirm.text);
    if (err != null) {
      setState(() => _error = err);
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      await PasswordRecoveryRepository.completeReset(_resetToken, _password.text, _confirm.text);
      if (!mounted) return;
      setState(() {
        _loading = false;
        _completed = true;
      });
    } catch (ex) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = ex.toString().replaceFirst('Exception: ', '');
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final scale = MediaQuery.textScalerOf(context);

    return Scaffold(
      resizeToAvoidBottomInset: true,
      appBar: AppBar(
        title: const Text('Password recovery'),
        leading: BackButton(onPressed: () => Navigator.maybePop(context)),
      ),
      body: DecoratedBox(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [AppColors.bgLight, AppColors.cardWhite],
          ),
        ),
        child: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(20),
            child: _unavailable
                ? _unavailableCard(scale)
                : _completed
                    ? _successCard(scale)
                    : _flowCard(scale),
          ),
        ),
      ),
    );
  }

  Widget _unavailableCard(TextScaler scale) {
    return _card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            'Password recovery',
            style: TextStyle(fontSize: scale.scale(22), fontWeight: FontWeight.w700, color: AppColors.navyDeep),
          ),
          const SizedBox(height: 12),
          const Text(
            'Password recovery is currently unavailable. Please contact your institution administrator.',
            style: TextStyle(color: Color(0xFFC62828), fontSize: 15, height: 1.45),
          ),
          const SizedBox(height: 20),
          FilledButton(onPressed: () => Navigator.pop(context), child: const Text('Back to Sign In')),
        ],
      ),
    );
  }

  Widget _successCard(TextScaler scale) {
    return _card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text('Password updated', style: TextStyle(fontSize: scale.scale(22), fontWeight: FontWeight.w700)),
          const SizedBox(height: 12),
          const Text(
            'Your password has been updated. Please sign in.',
            style: TextStyle(color: AppColors.textMuted, height: 1.45),
          ),
          const SizedBox(height: 20),
          FilledButton(onPressed: () => Navigator.pop(context), child: const Text('Back to Sign In')),
        ],
      ),
    );
  }

  Widget _flowCard(TextScaler scale) {
    return _card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const AuthBrandingHeader(onDark: false),
          const SizedBox(height: 12),
          Text('Step $_step of 3', style: TextStyle(fontSize: scale.scale(13), fontWeight: FontWeight.w600, color: AppColors.textMuted)),
          const SizedBox(height: 8),
          Text(
            _step == 1
                ? 'Forgot Password?'
                : _step == 2
                    ? 'Check Your Email'
                    : 'Set Your New Password',
            style: TextStyle(fontSize: scale.scale(22), fontWeight: FontWeight.w700, color: AppColors.navyDeep),
          ),
          const SizedBox(height: 8),
          Text(
            _step == 1
                ? 'Enter your account email to request a verification code.'
                : _step == 2
                    ? _neutralMsg
                    : 'Choose a new password for your account.',
            style: TextStyle(fontSize: scale.scale(15), color: AppColors.textMuted, height: 1.4),
          ),
          const SizedBox(height: 18),
          if (_step == 1) ...[
            TextField(
              controller: _email,
              keyboardType: TextInputType.emailAddress,
              decoration: const InputDecoration(labelText: 'Email Address', prefixIcon: Icon(Icons.mail_outline)),
            ),
          ] else if (_step == 2) ...[
            TextField(
              controller: _code,
              keyboardType: TextInputType.number,
              inputFormatters: [FilteringTextInputFormatter.digitsOnly],
              maxLength: 6,
              decoration: const InputDecoration(labelText: 'Verification Code', prefixIcon: Icon(Icons.pin_outlined)),
            ),
          ] else ...[
            TextField(
              controller: _password,
              obscureText: _obscure1,
              decoration: InputDecoration(
                labelText: 'New Password',
                prefixIcon: const Icon(Icons.lock_outline),
                suffixIcon: IconButton(
                  icon: Icon(_obscure1 ? Icons.visibility_outlined : Icons.visibility_off_outlined),
                  onPressed: () => setState(() => _obscure1 = !_obscure1),
                ),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _confirm,
              obscureText: _obscure2,
              decoration: InputDecoration(
                labelText: 'Confirm New Password',
                prefixIcon: const Icon(Icons.lock_outline),
                suffixIcon: IconButton(
                  icon: Icon(_obscure2 ? Icons.visibility_outlined : Icons.visibility_off_outlined),
                  onPressed: () => setState(() => _obscure2 = !_obscure2),
                ),
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'At least 8 characters with one letter and one number.',
              style: TextStyle(fontSize: scale.scale(14), color: AppColors.textMuted),
            ),
          ],
          if (_error != null) ...[
            const SizedBox(height: 10),
            Text(_error!, style: const TextStyle(color: Color(0xFFC62828), fontSize: 15)),
          ],
          const SizedBox(height: 18),
          SizedBox(
            height: 50,
            child: FilledButton(
              onPressed: _loading
                  ? null
                  : () {
                      if (_step == 1) {
                        _continueEmail();
                      } else if (_step == 2) {
                        _verifyCode();
                      } else {
                        _savePassword();
                      }
                    },
              child: _loading
                  ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : Text(_step == 1 ? 'Send Verification Code' : _step == 2 ? 'Verify Code' : 'Save New Password'),
            ),
          ),
          if (_step == 1)
            TextButton(onPressed: () => Navigator.pop(context), child: const Text('Back to Sign In'))
          else if (_step == 2)
            TextButton(
              onPressed: () => setState(() {
                _step = 1;
                _error = null;
              }),
              child: const Text('Change Email'),
            ),
        ],
      ),
    );
  }

  Widget _card({required Widget child}) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: AppColors.cardWhite,
        borderRadius: BorderRadius.circular(FlLayout.cardRadius),
        border: Border.all(color: AppColors.border),
      ),
      child: Padding(padding: const EdgeInsets.all(22), child: child),
    );
  }
}
