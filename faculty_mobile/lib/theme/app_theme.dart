import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppColors {
  static const primaryBlue = Color(0xFF1456C0);
  static const navyDeep = Color(0xFF102B50);
  static const warmYellow = Color(0xFFFFD447);
  static const bgLight = Color(0xFFF4F7FC);
  static const cardWhite = Color(0xFFFFFFFF);
  static const textMain = Color(0xFF172B4D);
  static const textMuted = Color(0xFF53657D);
  static const border = Color(0xFFDFE7F2);
  static const primarySoft = Color(0xFFE6EEF9);
  static const yellowSoft = Color(0xFFFFF8E1);

  // Legacy aliases used across the app
  static const textNavy = textMain;
  static const navySecondary = navyDeep;
  static const muted = textMuted;
  static const cyan = Color(0xFF51C8EF);
  static const success = Color(0xFF1B7A4E);
}

ThemeData buildFacultyLinkTheme() {
  final base = ThemeData(
    useMaterial3: true,
    colorScheme: ColorScheme.fromSeed(
      seedColor: AppColors.primaryBlue,
      primary: AppColors.primaryBlue,
      secondary: AppColors.warmYellow,
      surface: AppColors.bgLight,
    ),
    scaffoldBackgroundColor: AppColors.bgLight,
  );

  final textTheme = GoogleFonts.interTextTheme(base.textTheme).copyWith(
    headlineSmall: const TextStyle(fontWeight: FontWeight.w700, color: AppColors.textMain, height: 1.25),
    titleLarge: const TextStyle(fontWeight: FontWeight.w700, color: AppColors.textMain, fontSize: 22, height: 1.3),
    titleMedium: const TextStyle(fontWeight: FontWeight.w600, color: AppColors.textMain, fontSize: 20, height: 1.35),
    bodyLarge: const TextStyle(fontSize: 17, color: AppColors.textMain, height: 1.45),
    bodyMedium: const TextStyle(fontSize: 16, color: AppColors.textMain, height: 1.45),
    bodySmall: const TextStyle(fontSize: 15, color: AppColors.textMuted, height: 1.4),
    labelLarge: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: AppColors.textMain),
  );

  return base.copyWith(
    textTheme: textTheme,
    appBarTheme: const AppBarTheme(
      backgroundColor: AppColors.navyDeep,
      foregroundColor: Colors.white,
      elevation: 0,
      titleTextStyle: TextStyle(fontSize: 20, fontWeight: FontWeight.w600, color: Colors.white),
    ),
    cardTheme: CardThemeData(
      elevation: 0,
      color: AppColors.cardWhite,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(20),
        side: const BorderSide(color: AppColors.border),
      ),
      margin: EdgeInsets.zero,
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: AppColors.primaryBlue,
        foregroundColor: Colors.white,
        minimumSize: const Size(48, 48),
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
        textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: AppColors.primaryBlue,
        minimumSize: const Size(48, 48),
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
        textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        side: const BorderSide(color: AppColors.border),
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(
        foregroundColor: AppColors.primaryBlue,
        minimumSize: const Size(48, 48),
        textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: const BorderSide(color: AppColors.border),
      ),
      filled: true,
      fillColor: AppColors.cardWhite,
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
      labelStyle: const TextStyle(fontSize: 16, color: AppColors.textMuted),
      helperStyle: const TextStyle(fontSize: 14, color: AppColors.textMuted, height: 1.4),
    ),
    navigationBarTheme: NavigationBarThemeData(
      height: 72,
      backgroundColor: AppColors.cardWhite,
      elevation: 8,
      shadowColor: AppColors.navyDeep.withValues(alpha: 0.12),
      indicatorColor: AppColors.primarySoft,
      labelTextStyle: WidgetStateProperty.resolveWith((states) {
        final selected = states.contains(WidgetState.selected);
        return TextStyle(
          fontSize: 12,
          fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
          color: selected ? AppColors.primaryBlue : AppColors.navyDeep,
          letterSpacing: 0,
        );
      }),
      iconTheme: WidgetStateProperty.resolveWith((states) {
        final selected = states.contains(WidgetState.selected);
        return IconThemeData(
          color: selected ? AppColors.primaryBlue : AppColors.navyDeep,
          size: 26,
        );
      }),
    ),
    dividerTheme: const DividerThemeData(color: AppColors.border, thickness: 1),
    snackBarTheme: SnackBarThemeData(
      backgroundColor: AppColors.navyDeep,
      contentTextStyle: const TextStyle(fontSize: 16, color: Colors.white),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
    ),
  );
}
