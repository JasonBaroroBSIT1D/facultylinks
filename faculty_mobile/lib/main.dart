import 'package:flutter/material.dart';

import 'screens/forgot_password_screen.dart';
import 'screens/login_screen.dart';
import 'screens/splash_screen.dart';
import 'screens/shell_screen.dart';
import 'theme/app_theme.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const FacultyLinkApp());
}

class FacultyLinkApp extends StatelessWidget {
  const FacultyLinkApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'FacultyLink',
      debugShowCheckedModeBanner: false,
      theme: buildFacultyLinkTheme(),
      routes: {
        '/': (_) => const SplashScreen(),
        '/login': (_) => const LoginScreen(),
        '/forgot': (_) => const ForgotPasswordScreen(),
        '/home': (_) => const ShellScreen(),
      },
      initialRoute: '/',
    );
  }
}
