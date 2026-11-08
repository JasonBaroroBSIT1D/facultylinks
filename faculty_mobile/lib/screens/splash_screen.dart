import 'package:flutter/material.dart';

import '../repositories/auth_repository.dart';
import '../theme/app_theme.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  @override
  void initState() {
    super.initState();
    _go();
  }

  Future<void> _go() async {
    await Future.delayed(const Duration(milliseconds: 1200));
    final email = await AuthRepository.currentEmail();
    if (!mounted) return;
    Navigator.pushReplacementNamed(context, email != null ? '/home' : '/login');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.navyDeep,
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text.rich(
              TextSpan(
                children: [
                  const TextSpan(text: 'Faculty', style: TextStyle(color: Colors.white, fontSize: 32, fontWeight: FontWeight.bold)),
                  TextSpan(text: 'Link', style: TextStyle(color: AppColors.cyan, fontSize: 32, fontWeight: FontWeight.bold)),
                ],
              ),
            ),
            const SizedBox(height: 8),
            Text('CONNECT · EVALUATE · ADVANCE.', style: TextStyle(color: AppColors.muted, letterSpacing: 2, fontSize: 11)),
            const SizedBox(height: 32),
            const CircularProgressIndicator(color: AppColors.cyan),
          ],
        ),
      ),
    );
  }
}
