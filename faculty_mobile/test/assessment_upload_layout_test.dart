import 'package:faculty_mobile/data/assessment_catalog.dart';
import 'package:faculty_mobile/repositories/mock_repository.dart';
import 'package:faculty_mobile/screens/tabs/assessment_tab.dart';
import 'package:faculty_mobile/screens/upload_evidence_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  setUpAll(() {
    TestWidgetsFlutterBinding.ensureInitialized();
    SharedPreferences.setMockInitialValues({});
  });
  testWidgets('Assessment tab expands KRAs without Material error', (tester) async {
    final repo = await MockRepository.load();
    repo.catalogKras = assessmentKras;
    repo.catalogLoadedFromApi = true;
    await tester.pumpWidget(
      MaterialApp(
        home: AssessmentTab(repo: repo, onSave: () async {}),
      ),
    );
    await tester.pump();

    await tester.tap(find.text('KRA I · Instruction'));
    await tester.pump(const Duration(milliseconds: 400));

    await tester.ensureVisible(find.text('Criterion B – Instructional Materials Development'));
    await tester.tap(find.text('Criterion B – Instructional Materials Development'), warnIfMissed: false);
    await tester.pump(const Duration(milliseconds: 400));

    expect(find.byType(ListTile), findsWidgets);
    expect(tester.takeException(), isNull);
  });

  for (final width in [320.0, 360.0, 412.0]) {
    testWidgets('Upload evidence scroll owner fits ${width.toInt()}px width', (tester) async {
      final repo = await MockRepository.load();
      repo.catalogKras = assessmentKras;
      repo.catalogLoadedFromApi = true;
      await tester.binding.setSurfaceSize(Size(width, 740));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await tester.pumpWidget(
        MaterialApp(
          home: MediaQuery(
            data: MediaQueryData(size: Size(width, 740), textScaler: TextScaler.noScaling),
            child: UploadEvidenceScreen(repo: repo, onSave: () async {}),
          ),
        ),
      );
      await tester.pump();

      expect(find.textContaining('Step 1 of'), findsOneWidget);
      expect(find.byType(DropdownButtonFormField<KraNode>), findsOneWidget);
      expect(find.byType(Stepper), findsNothing);
      expect(find.byType(SingleChildScrollView), findsWidgets);
      expect(tester.takeException(), isNull);

      final overflow = find.byWidgetPredicate(
        (w) => w.runtimeType.toString().contains('OverflowIndicator'),
      );
      expect(overflow, findsNothing);
    });
  }

  testWidgets('Step 2 criterion cards scroll and keep selection on Back', (tester) async {
    final repo = await MockRepository.load();
    repo.catalogKras = assessmentKras;
    repo.catalogLoadedFromApi = true;
    await tester.binding.setSurfaceSize(const Size(360, 640));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      MaterialApp(
        home: MediaQuery(
          data: const MediaQueryData(size: Size(360, 640)),
          child: UploadEvidenceScreen(repo: repo, onSave: () async {}),
        ),
      ),
    );
    await tester.pump();

    // Select KRA IV (4 criterion cards) then Continue to Step 2.
    await tester.tap(find.byType(DropdownButtonFormField<KraNode>));
    await tester.pumpAndSettle();
    await tester.tap(find.text('KRA IV · Professional Development').last);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Continue'));
    await tester.pumpAndSettle();

    expect(find.textContaining('Step 2 of'), findsOneWidget);
    expect(find.text('D. Newly appointed faculty'), findsOneWidget);

    await tester.ensureVisible(find.text('D. Newly appointed faculty'));
    await tester.tap(find.text('D. Newly appointed faculty'));
    await tester.pumpAndSettle();

    // Scroll to bottom controls and go Back — selection must remain.
    await tester.ensureVisible(find.text('Back'));
    await tester.tap(find.text('Back'));
    await tester.pumpAndSettle();
    expect(find.textContaining('Step 1 of'), findsOneWidget);

    await tester.tap(find.text('Continue'));
    await tester.pumpAndSettle();
    expect(find.text('D. Newly appointed faculty'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  test('KRA short dropdown labels match spec', () {
    expect(assessmentKras[0].shortDropdownLabel, 'KRA I · Instruction');
    expect(assessmentKras[1].shortDropdownLabel, 'KRA II · Research');
    expect(assessmentKras[2].shortDropdownLabel, 'KRA III · Extension');
    expect(assessmentKras[3].shortDropdownLabel, 'KRA IV · Professional Development');
  });
}
