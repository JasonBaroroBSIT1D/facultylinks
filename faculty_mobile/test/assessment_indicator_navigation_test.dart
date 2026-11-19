import 'package:faculty_mobile/data/assessment_catalog.dart';
import 'package:faculty_mobile/repositories/mock_repository.dart';
import 'package:faculty_mobile/screens/kra_i_achievement_screen.dart';
import 'package:faculty_mobile/screens/tabs/assessment_tab.dart';
import 'package:faculty_mobile/screens/upload_evidence_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

MockRepository _repo() {
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

  testWidgets('KRA I Criterion B Sole Author Textbook opens achievement with context', (tester) async {
    await tester.binding.setSurfaceSize(const Size(400, 1600));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      MaterialApp(
        home: AssessmentTab(
          repo: _repo(),
          onSave: () async {},
          selectedKraId: 'kra-I',
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('Criterion B – Instructional Materials Development'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Sole Author Textbook'));
    await tester.pumpAndSettle();

    expect(find.byType(KraIAchievementScreen), findsOneWidget);
    expect(find.text('Sole Author Textbook'), findsWidgets);
    expect(find.text('KRA (Key Result Area)'), findsNothing);
  });

  testWidgets('KRA II Academic Book opens achievement without KRA I defaults', (tester) async {
    await tester.binding.setSurfaceSize(const Size(400, 1600));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      MaterialApp(
        home: AssessmentTab(
          repo: _repo(),
          onSave: () async {},
          selectedKraId: 'kra-II',
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.textContaining('Criterion A – Research'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Academic Book'));
    await tester.pumpAndSettle();

    final screen = tester.widget<KraIAchievementScreen>(find.byType(KraIAchievementScreen));
    expect(screen.kraId, 'kra-II');
    expect(screen.indicator?.id, 'kra-II-A-1');
    expect(screen.criterion.id, 'kra-II-A');
    expect(find.text('Upload SET / SEF evaluation'), findsNothing);
  });

  testWidgets('Add Document with locked indicator opens achievement directly', (tester) async {
    final repo = _repo();
    final criterion = repo.catalogKras
        .firstWhere((k) => k.id == 'kra-I')
        .criteria
        .firstWhere((c) => c.id == 'kra-I-B');
    final indicator = criterion.indicators.firstWhere((i) => i.id == 'kra-I-B-1-1');

    await tester.pumpWidget(
      MaterialApp(
        home: UploadEvidenceScreen(
          repo: repo,
          onSave: () async {},
          initialKraId: 'kra-I',
          initialCriterionId: 'kra-I-B',
          initialIndicatorId: indicator.id,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byType(KraIAchievementScreen), findsOneWidget);
    expect(find.byType(DropdownButtonFormField<KraNode>), findsNothing);
    final screen = tester.widget<KraIAchievementScreen>(find.byType(KraIAchievementScreen));
    expect(screen.kraId, 'kra-I');
    expect(screen.indicator?.id, 'kra-I-B-1-1');
  });

  testWidgets('Home-style Add Document still asks for KRA', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: UploadEvidenceScreen(repo: _repo(), onSave: () async {}),
      ),
    );
    await tester.pump();

    expect(find.byType(DropdownButtonFormField<KraNode>), findsOneWidget);
    expect(find.byType(KraIAchievementScreen), findsNothing);
  });

  testWidgets('criterion stays expanded after returning from indicator', (tester) async {
    await tester.binding.setSurfaceSize(const Size(400, 1600));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      MaterialApp(
        home: AssessmentTab(
          repo: _repo(),
          onSave: () async {},
          selectedKraId: 'kra-IV',
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.textContaining('Awards'));
    await tester.pumpAndSettle();
    expect(find.text('Award of distinction'), findsOneWidget);

    await tester.tap(find.text('Award of distinction'));
    await tester.pumpAndSettle();
    expect(find.byType(KraIAchievementScreen), findsOneWidget);

    await tester.pageBack();
    await tester.pumpAndSettle();

    expect(find.text('Award of distinction'), findsOneWidget);
    expect(find.text('Maximum: 4 points'), findsOneWidget);
  });
}
