import 'package:faculty_mobile/repositories/mock_repository.dart';
import 'package:faculty_mobile/screens/set_sef_screen.dart';
import 'package:faculty_mobile/screens/tabs/assessment_tab.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  setUpAll(() {
    TestWidgetsFlutterBinding.ensureInitialized();
    SharedPreferences.setMockInitialValues({});
  });

  MockRepository _repoWithScores() {
    final repo = MockRepository();
    repo.profile.name = 'Faculty User';
    repo.scoresConfigured = true;
    repo.facultyScoresEstimated = {
      'byKra': {
        'kra-I': {
          'criterionA': {
            'criterionAPoints': 57.2,
            'setPoints': 34.32,
            'sefPoints': 22.88,
            'incomplete': false,
          },
        },
      },
    };
    repo.facultyScoresVerified = {
      'byKra': {
        'kra-I': {
          'criterionA': {
            'criterionAPoints': 57.2,
            'setPoints': 34.32,
            'sefPoints': 22.88,
            'incomplete': false,
          },
        },
      },
    };
    repo.academicYears = ['2024-2025', '2025-2026'];
    repo.setRatings = List<double?>.filled(6, null);
    repo.sefRatings = List<double?>.filled(6, null);
    return repo;
  }

  testWidgets('tapping SET & SEF card opens detail without RangeError', (tester) async {
    final repo = _repoWithScores();

    await tester.pumpWidget(
      MaterialApp(
        home: AssessmentTab(repo: repo, onSave: () async {}),
      ),
    );
    await tester.pump();

    await tester.tap(find.text('SET & SEF'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    expect(find.byType(SetSefScreen), findsOneWidget);
    expect(find.text('Criterion A totals'), findsOneWidget);
    expect(tester.takeException(), isNull);

    await tester.pump(const Duration(milliseconds: 400));
    expect(tester.takeException(), isNull);
  });

  testWidgets('SetSefScreen renders with two academic years and six rating slots', (tester) async {
    final repo = _repoWithScores();
    repo.setRatings[4] = 90.0;

    await tester.pumpWidget(
      MaterialApp(
        home: SetSefScreen(repo: repo, onSave: () async {}),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 200));

    expect(find.byType(TabBar), findsNothing);
    expect(tester.takeException(), isNull);
  });
}
