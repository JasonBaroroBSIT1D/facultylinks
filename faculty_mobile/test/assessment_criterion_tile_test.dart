import 'package:faculty_mobile/data/assessment_catalog.dart';
import 'package:faculty_mobile/repositories/mock_repository.dart';
import 'package:faculty_mobile/screens/tabs/assessment_tab.dart';
import 'package:faculty_mobile/widgets/assessment_criterion_tile.dart';
import 'package:faculty_mobile/widgets/assessment_indicator_row.dart';
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

  testWidgets('criteria start collapsed and expand independently', (tester) async {
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

    expect(find.byType(AssessmentCriterionTile), findsWidgets);
    expect(find.text('Upload SET / SEF evaluation'), findsNothing);
    expect(find.text('SET & SEF'), findsNothing);

    final criterionA = find.text('Criterion A – Teaching Effectiveness');
    final criterionB = find.text('Criterion B – Instructional Materials Development');
    expect(criterionA, findsOneWidget);
    expect(criterionB, findsOneWidget);

    await tester.tap(criterionA);
    await tester.pumpAndSettle();
    expect(find.text('Upload SET / SEF evaluation'), findsOneWidget);
    expect(find.text('SET & SEF'), findsOneWidget);

    // B stays collapsed while A is open.
    final indicatorUnderB = find.textContaining('Sole Author');
    expect(indicatorUnderB, findsNothing);

    await tester.tap(criterionB);
    await tester.pumpAndSettle();
    expect(find.text('Upload SET / SEF evaluation'), findsOneWidget);
    expect(indicatorUnderB, findsWidgets);
    expect(find.text('Maximum: 30 points'), findsOneWidget);
    expect(find.byIcon(Icons.chevron_right), findsWidgets);

    await tester.tap(criterionA);
    await tester.pumpAndSettle();
    expect(find.text('Upload SET / SEF evaluation'), findsNothing);
    expect(indicatorUnderB, findsWidgets);
  });

  testWidgets('indicator rows show maximum points and wrap on narrow screens', (tester) async {
    await tester.binding.setSurfaceSize(const Size(320, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      MaterialApp(
        home: MediaQuery(
          data: const MediaQueryData(size: Size(320, 900), textScaler: TextScaler.linear(1.3)),
          child: AssessmentTab(
            repo: _repo(),
            onSave: () async {},
            selectedKraId: 'kra-II',
          ),
        ),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    final criterionA = find.textContaining('Criterion A – Research');
    await tester.ensureVisible(criterionA);
    await tester.tap(criterionA);
    await tester.pumpAndSettle();

    expect(find.text('Academic Book'), findsOneWidget);
    expect(find.text('Book Chapter'), findsOneWidget);
    expect(find.text('Maximum: 100 points'), findsWidgets); // Academic Book + Monograph
    expect(find.text('Maximum: 35 points'), findsWidgets);
    expect(find.byType(AssessmentIndicatorRow), findsWidgets);
    expect(find.text('Upload SET / SEF evaluation'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('switching KRA remounts with collapsed criteria and no SET/SEF leak', (tester) async {
    final repo = _repo();
    await tester.binding.setSurfaceSize(const Size(400, 1600));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    Future<void> pumpScoped(String kraId) async {
      await tester.pumpWidget(
        MaterialApp(
          home: AssessmentTab(
            key: ValueKey('assessment-$kraId'),
            repo: repo,
            onSave: () async {},
            selectedKraId: kraId,
          ),
        ),
      );
      await tester.pumpAndSettle();
    }

    await pumpScoped('kra-I');
    await tester.tap(find.text('Criterion A – Teaching Effectiveness'));
    await tester.pumpAndSettle();
    expect(find.text('SET & SEF'), findsOneWidget);

    await pumpScoped('kra-II');
    expect(find.text('KRA II — Research'), findsOneWidget);
    expect(find.text('SET & SEF'), findsNothing);
    expect(find.text('Upload SET / SEF evaluation'), findsNothing);
    expect(find.textContaining('Criterion A – Research'), findsOneWidget);

    // Research criterion starts collapsed again (no KRA I expansion state).
    expect(find.textContaining('Academic'), findsNothing);
  });
}
