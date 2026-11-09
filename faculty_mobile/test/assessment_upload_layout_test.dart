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

  for (final width in [320.0, 360.0]) {
    testWidgets('Upload evidence stepper fits ${width.toInt()}px width', (tester) async {
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

      expect(find.text('Add proof for your assessment'), findsOneWidget);
      expect(find.byType(DropdownButtonFormField<KraNode>), findsOneWidget);
      expect(tester.takeException(), isNull);

      final overflow = find.byWidgetPredicate(
        (w) => w.runtimeType.toString().contains('OverflowIndicator'),
      );
      expect(overflow, findsNothing);
    });
  }

  test('KRA short dropdown labels match spec', () {
    expect(assessmentKras[0].shortDropdownLabel, 'KRA I · Instruction');
    expect(assessmentKras[1].shortDropdownLabel, 'KRA II · Research');
    expect(assessmentKras[2].shortDropdownLabel, 'KRA III · Extension');
    expect(assessmentKras[3].shortDropdownLabel, 'KRA IV · Professional Development');
  });
}
