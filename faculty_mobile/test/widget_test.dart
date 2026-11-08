import 'package:faculty_mobile/main.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  setUpAll(() {
    TestWidgetsFlutterBinding.ensureInitialized();
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('App smoke test', (tester) async {
    await tester.pumpWidget(const FacultyLinkApp());
    expect(find.byType(Image), findsWidgets);
    await tester.pump(const Duration(milliseconds: 900));
    await tester.pumpAndSettle();
    expect(find.text('Welcome back.'), findsOneWidget);
  });
}
