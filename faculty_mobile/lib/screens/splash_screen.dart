import 'package:flutter/material.dart';

import '../repositories/auth_repository.dart';
import '../theme/app_theme.dart';
import '../widgets/fl_logo.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  static const _minDisplay = Duration(milliseconds: 900);

  @override
  void initState() {
    super.initState();
    _bootstrap();
  }

  Future<void> _bootstrap() async {
    String? email;
    var mustChange = false;
    await Future.wait<void>([
      AuthRepository.currentEmail().then((v) => email = v),
      AuthRepository.mustChangePassword().then((v) => mustChange = v),
      Future.delayed(_minDisplay),
    ]);
    if (email != null) {
      final me = await AuthRepository.fetchMe();
      if (me != null) {
        mustChange = me['mustChangePassword'] == true;
      }
    }
    if (!mounted) return;
    final route = email == null
        ? '/login'
        : (mustChange ? '/change-password' : '/home');
    Navigator.pushReplacementNamed(context, route);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgLight,
      body: SafeArea(
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const FlLogoFull(width: 200),
              const SizedBox(height: 40),
              const SizedBox(
                width: 28,
                height: 28,
                child: CircularProgressIndicator(
                  strokeWidth: 2.5,
                  color: AppColors.primaryBlue,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
