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
  RecoveryChannel _channel = RecoveryChannel.email;

  final _email = TextEditingController();
  final _phone = TextEditingController();
  final _code = TextEditingController();
  final _password = TextEditingController();
  final _confirm = TextEditingController();
  final _newPasswordFocus = FocusNode();
  final _confirmPasswordFocus = FocusNode();
  bool _obscure1 = true;
  bool _obscure2 = true;
  String? _error;

  static const _step2Subtitle =
      'If recovery is available through your selected method, a code will be sent.';

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
    _phone.dispose();
    _code.dispose();
    _password.dispose();
    _confirm.dispose();
    _newPasswordFocus.dispose();
    _confirmPasswordFocus.dispose();
    super.dispose();
  }

  void _onChannelChanged(RecoveryChannel? value) {
    if (value == null) return;
    setState(() {
      _channel = value;
      _error = null;
    });
  }

  Future<void> _sendCode() async {
    final err = _channel == RecoveryChannel.email
        ? PasswordRecoveryRepository.validateEmail(_email.text)
        : PasswordRecoveryRepository.validatePhone(_phone.text);
    setState(() => _error = err);
    if (err != null) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      await PasswordRecoveryRepository.requestCode(
        channel: _channel,
        email: _channel == RecoveryChannel.email ? _email.text : null,
        phone: _channel == RecoveryChannel.sms ? _phone.text : null,
      );
      if (!mounted) return;
      setState(() {
        _loading = false;
        _step = 2;
        _code.clear();
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
      final token = await PasswordRecoveryRepository.verifyCode(
        channel: _channel,
        code: _code.text,
        email: _channel == RecoveryChannel.email ? _email.text : null,
        phone: _channel == RecoveryChannel.sms ? _phone.text : null,
      );
      if (!mounted) return;
      FocusManager.instance.primaryFocus?.unfocus();
      setState(() {
        _loading = false;
        _resetToken = token;
        _step = 3;
        _password.clear();
        _confirm.clear();
      });
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted || _step != 3) return;
        _newPasswordFocus.requestFocus();
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

  void _changeDeliveryMethod() {
    setState(() {
      _step = 1;
      _error = null;
      _code.clear();
    });
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
                    ? 'Enter Verification Code'
                    : 'Set Your New Password',
            style: TextStyle(fontSize: scale.scale(22), fontWeight: FontWeight.w700, color: AppColors.navyDeep),
          ),
          const SizedBox(height: 8),
          Text(
            _step == 1
                ? 'Choose how to receive your code, then enter the matching account detail.'
                : _step == 2
                    ? _step2Subtitle
                    : 'Choose a new password for your account.',
            style: TextStyle(fontSize: scale.scale(15), color: AppColors.textMuted, height: 1.4),
          ),
          const SizedBox(height: 18),
          KeyedSubtree(
            key: ValueKey<int>(_step),
            child: _step == 1
                ? _step1Fields()
                : _step == 2
                    ? _step2Fields()
                    : _step3Fields(scale),
          ),
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
                        _sendCode();
                      } else if (_step == 2) {
                        _verifyCode();
                      } else {
                        _savePassword();
                      }
                    },
              child: _loading
                  ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : Text(_step == 1 ? 'Send Code' : _step == 2 ? 'Verify Code' : 'Save New Password'),
            ),
          ),
          if (_step == 1)
            TextButton(onPressed: () => Navigator.pop(context), child: const Text('Back to Sign In'))
          else if (_step == 2)
            TextButton(
              onPressed: _changeDeliveryMethod,
              child: const Text('Change delivery method'),
            ),
        ],
      ),
    );
  }

  Widget _step1Fields() {
    final scale = MediaQuery.textScalerOf(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          'How would you like to receive your code?',
          style: TextStyle(fontSize: scale.scale(15), fontWeight: FontWeight.w600, color: AppColors.navyDeep),
        ),
        const SizedBox(height: 6),
        RadioGroup<RecoveryChannel>(
          groupValue: _channel,
          onChanged: _onChannelChanged,
          child: Column(
            children: [
              RadioListTile<RecoveryChannel>(
                contentPadding: EdgeInsets.zero,
                title: const Text('Email'),
                subtitle: const Text('Code sent to your account email'),
                value: RecoveryChannel.email,
              ),
              RadioListTile<RecoveryChannel>(
                contentPadding: EdgeInsets.zero,
                title: const Text('SMS'),
                subtitle: const Text('Uses the verified mobile number on your account.'),
                value: RecoveryChannel.sms,
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        if (_channel == RecoveryChannel.email)
          TextField(
            key: const ValueKey('recovery_email'),
            controller: _email,
            keyboardType: TextInputType.emailAddress,
            autofillHints: const [AutofillHints.email],
            decoration: const InputDecoration(labelText: 'Email Address', prefixIcon: Icon(Icons.mail_outline)),
          )
        else
          TextField(
            key: const ValueKey('recovery_phone'),
            controller: _phone,
            keyboardType: TextInputType.phone,
            autofillHints: const [AutofillHints.telephoneNumber],
            decoration: const InputDecoration(labelText: 'Mobile Number', prefixIcon: Icon(Icons.phone_outlined)),
          ),
      ],
    );
  }

  Widget _step2Fields() {
    return TextField(
      key: const ValueKey('recovery_otp'),
      controller: _code,
      keyboardType: TextInputType.number,
      inputFormatters: [FilteringTextInputFormatter.digitsOnly],
      maxLength: 6,
      decoration: const InputDecoration(labelText: 'Verification Code', prefixIcon: Icon(Icons.pin_outlined)),
    );
  }

  Widget _step3Fields(TextScaler scale) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        TextField(
          key: const ValueKey('recovery_new_password'),
          focusNode: _newPasswordFocus,
          controller: _password,
          keyboardType: TextInputType.visiblePassword,
          autocorrect: false,
          enableSuggestions: false,
          obscureText: _obscure1,
          autofillHints: const [AutofillHints.newPassword],
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
          key: const ValueKey('recovery_confirm_password'),
          focusNode: _confirmPasswordFocus,
          controller: _confirm,
          keyboardType: TextInputType.visiblePassword,
          autocorrect: false,
          enableSuggestions: false,
          obscureText: _obscure2,
          autofillHints: const [AutofillHints.newPassword],
          textInputAction: TextInputAction.done,
          onSubmitted: (_) => _savePassword(),
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