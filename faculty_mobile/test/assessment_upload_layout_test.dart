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
    await tester.binding.setSurfaceSize(const Size(400, 1200));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(
      MaterialApp(
        home: MediaQuery(
          data: const MediaQueryData(size: Size(400, 1200), textScaler: TextScaler.noScaling),
          child: AssessmentTab(repo: repo, onSave: () async {}),
        ),
      ),
    );
    await tester.pumpAndSettle();

    final kraHeader = find.text('KRA I · Instruction');
    await tester.ensureVisible(kraHeader.last);
    await tester.tap(kraHeader.last, warnIfMissed: false);
    await tester.pumpAndSettle();

    final criterionB = find.text('Criterion B – Instructional Materials Development');
    if (criterionB.evaluate().isNotEmpty) {
      await tester.ensureVisible(criterionB);
      await tester.tap(criterionB, warnIfMissed: false);
      await tester.pumpAndSettle();
    }

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

  testWidgets('File step shows Add files and Scan with Camera for Special Status', (tester) async {
    final repo = await MockRepository.load();
    repo.catalogKras = assessmentKras;
    repo.catalogLoadedFromApi = true;
    await tester.binding.setSurfaceSize(const Size(400, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      MaterialApp(
        home: MediaQuery(
          data: const MediaQueryData(size: Size(400, 900), textScaler: TextScaler.noScaling),
          child: UploadEvidenceScreen(
            repo: repo,
            onSave: () async {},
            initialKraId: 'kra-I',
            initialCriterionId: 'kra-I-A',
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    // Step 0 (preselect Criterion A): pick Special Status, then Continue to file step.
    await tester.ensureVisible(find.text('Special Status'));
    await tester.tap(find.text('Special Status'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Continue'));
    await tester.pumpAndSettle();

    expect(find.text('Add files'), findsOneWidget);
    expect(find.text('Scan with Camera'), findsOneWidget);
    expect(
      find.text('Add your files or scan printed documents. You can attach more than one document.'),
      findsOneWidget,
    );
  });

  testWidgets('SET/SEF file step shows Add files and Scan with Camera', (tester) async {
    final repo = await MockRepository.load();
    repo.catalogKras = assessmentKras;
    repo.catalogLoadedFromApi = true;
    await tester.binding.setSurfaceSize(const Size(400, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      MaterialApp(
        home: MediaQuery(
          data: const MediaQueryData(size: Size(400, 900), textScaler: TextScaler.noScaling),
          child: UploadEvidenceScreen(
            repo: repo,
            onSave: () async {},
            initialKraId: 'kra-I',
            initialCriterionId: 'kra-I-A',
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.ensureVisible(find.text('SET / SEF Evaluation'));
    await tester.tap(find.text('SET / SEF Evaluation'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Continue'));
    await tester.pumpAndSettle();

    expect(find.text('Scan with Camera'), findsOneWidget);
    expect(find.text('Add files'), findsOneWidget);
    expect(find.text('Choose PDF'), findsNothing);
    expect(
      find.text('Add your files or scan printed documents. You can attach more than one document.'),
      findsOneWidget,
    );
    expect(find.textContaining('Photos and other images are not supported'), findsNothing);
  });
}
