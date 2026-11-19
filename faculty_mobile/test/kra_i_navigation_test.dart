import 'package:faculty_mobile/data/assessment_catalog.dart';
import 'package:faculty_mobile/repositories/mock_repository.dart';
import 'package:faculty_mobile/screens/kra_i_achievement_screen.dart';
import 'package:faculty_mobile/screens/tabs/assessment_tab.dart';
import 'package:faculty_mobile/screens/upload_evidence_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

MockRepository _repoWithPublishedCatalog() {
  final repo = MockRepository();
  repo.catalogKras = assessmentKras;
  repo.catalogLoadedFromApi = true;
  return repo;
}

void main() {
  setUpAll(() {
    TestWidgetsFlutterBinding.ensureInitialized();
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('Add Document: KRA I offers A B C not only SET/SEF', (tester) async {
    final repo = _repoWithPublishedCatalog();
    await tester.pumpWidget(
      MaterialApp(
        home: UploadEvidenceScreen(repo: repo, onSave: () async {}),
      ),
    );
    await tester.pump();

    final kraDrop = find.byType(DropdownButtonFormField<KraNode>);
    expect(kraDrop, findsOneWidget);
    await tester.tap(kraDrop);
    await tester.pumpAndSettle();
    await tester.tap(find.text('KRA I · Instruction').last);
    await tester.pumpAndSettle();

    await tester.tap(find.widgetWithText(FilledButton, 'Continue').first);
    await tester.pumpAndSettle();

    expect(find.text('B. Instructional Materials Development'), findsOneWidget);
    expect(find.text('C. Research Advising and Mentorship'), findsOneWidget);
    expect(find.text('A. Teaching Effectiveness'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Add Document: KRA I B opens achievement flow', (tester) async {
    final repo = _repoWithPublishedCatalog();
    await tester.binding.setSurfaceSize(const Size(800, 1200));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(
      MaterialApp(
        home: UploadEvidenceScreen(repo: repo, onSave: () async {}),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byType(DropdownButtonFormField<KraNode>));
    await tester.pumpAndSettle();
    await tester.tap(find.text('KRA I · Instruction').last);
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilledButton, 'Continue').first);
    await tester.pumpAndSettle();

    await tester.ensureVisible(find.text('B. Instructional Materials Development'));
    await tester.tap(find.text('B. Instructional Materials Development'));
    await tester.pumpAndSettle();

    await tester.tap(find.byType(DropdownButtonFormField<IndicatorNode>));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Sole Author Textbook').last);
    await tester.pumpAndSettle();

    await tester.tap(find.widgetWithText(FilledButton, 'Open achievement').first);
    await tester.pumpAndSettle();

    expect(find.byType(KraIAchievementScreen), findsOneWidget);
    final screen = tester.widget<KraIAchievementScreen>(find.byType(KraIAchievementScreen));
    expect(screen.kraId, 'kra-I');
    expect(screen.indicator?.id, 'kra-I-B-1-1');
  });

  testWidgets('Upload SET/SEF shortcut still preselects Criterion A', (tester) async {
    final repo = _repoWithPublishedCatalog();
    await tester.pumpWidget(
      MaterialApp(
        home: UploadEvidenceScreen(
          repo: repo,
          onSave: () async {},
          initialKraId: 'kra-I',
          initialCriterionId: 'kra-I-A',
        ),
      ),
    );
    await tester.pump();

    expect(find.text('What are you uploading?'), findsOneWidget);
    expect(find.text('B. Instructional Materials Development'), findsNothing);
  });

  testWidgets('My Assessment exposes B/C when catalog loaded', (tester) async {
    final repo = _repoWithPublishedCatalog();
    await tester.pumpWidget(
      MaterialApp(home: AssessmentTab(repo: repo, onSave: () async {})),
    );
    await tester.pump();

    final kraHeader = find.byKey(const ValueKey('kra-expand-kra-I'));
    await tester.ensureVisible(kraHeader);
    await tester.tap(kraHeader);
    await tester.pump(const Duration(milliseconds: 400));
    final criterionB = find.text('Criterion B – Instructional Materials Development');
    await tester.ensureVisible(criterionB);
    expect(criterionB, findsOneWidget);
    expect(find.textContaining('Criterion C'), findsWidgets);
  });
}
