import 'package:faculty_mobile/data/assessment_catalog.dart';
import 'package:faculty_mobile/models/institution_config.dart';
import 'package:faculty_mobile/repositories/mock_repository.dart';
import 'package:faculty_mobile/screens/tabs/assessment_tab.dart';
import 'package:faculty_mobile/screens/tabs/home_tab.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

MockRepository _repo() {
  final repo = MockRepository();
  repo.profile.name = 'Test Faculty';
  repo.catalogKras = assessmentKras;
  repo.catalogLoadedFromApi = true;
  repo.scoresConfigured = true;
  return repo;
}

Future<void> _pumpHome(WidgetTester tester, MockRepository repo) async {
  await tester.binding.setSurfaceSize(const Size(400, 1600));
  addTearDown(() => tester.binding.setSurfaceSize(null));
  await tester.pumpWidget(
    MaterialApp(
      home: Builder(
        builder: (context) {
          return Scaffold(
            body: HomeTab(
              repo: repo,
              institutionConfig: InstitutionConfig.defaults(),
              onRefresh: () async {},
              onOpenAssessment: () {
                Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => AssessmentTab(
                      key: const ValueKey('assessment-all'),
                      repo: repo,
                      onSave: () async {},
                      institutionConfig: InstitutionConfig.defaults(),
                    ),
                  ),
                );
              },
              onOpenNotifications: () {},
            ),
          );
        },
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  setUpAll(() {
    TestWidgetsFlutterBinding.ensureInitialized();
    SharedPreferences.setMockInitialValues({});
  });

  test('AssessmentTab titles use stable kra ids', () {
    expect(AssessmentTab.titleForKraId(null), 'My Assessment');
    expect(AssessmentTab.titleForKraId('kra-I'), 'KRA I — Instruction');
    expect(AssessmentTab.titleForKraId('kra-II'), 'KRA II — Research');
    expect(AssessmentTab.titleForKraId('kra-III'), 'KRA III — Extension');
    expect(AssessmentTab.titleForKraId('kra-IV'), 'KRA IV — Professional Development');
  });

  testWidgets('Home KRA II opens Research-only assessment without KRA I SET/SEF', (tester) async {
    final repo = _repo();
    await _pumpHome(tester, repo);

    await tester.ensureVisible(find.text('Research'));
    await tester.tap(find.text('Research'));
    await tester.pumpAndSettle();

    expect(find.text('KRA II — Research'), findsOneWidget);
    expect(find.text('My Assessment'), findsNothing);
    expect(find.text('KRA I · Instruction'), findsNothing);
    expect(find.text('KRA III · Extension'), findsNothing);
    expect(find.text('Upload SET / SEF evaluation'), findsNothing);
    expect(find.text('SET & SEF'), findsNothing);
    expect(find.textContaining('assessment-definitions.js'), findsNothing);

    expect(find.textContaining('Criterion A – Research'), findsOneWidget);
    expect(find.text('Criterion A – Teaching Effectiveness'), findsNothing);
  });

  testWidgets('Home KRA III / IV / I each show only their own content', (tester) async {
    final repo = _repo();
    await _pumpHome(tester, repo);

    Future<void> openArea(String areaTitle, String appTitle, {required bool expectSetSef}) async {
      await tester.ensureVisible(find.text(areaTitle));
      await tester.tap(find.text(areaTitle));
      await tester.pumpAndSettle();
      expect(find.text(appTitle), findsOneWidget);
      // SET/SEF stays hidden until KRA I Criterion A is expanded.
      expect(find.text('Upload SET / SEF evaluation'), findsNothing);
      expect(find.text('SET & SEF'), findsNothing);
      if (expectSetSef) {
        expect(find.text('Criterion A – Teaching Effectiveness'), findsOneWidget);
        await tester.tap(find.text('Criterion A – Teaching Effectiveness'));
        await tester.pumpAndSettle();
        expect(find.text('Upload SET / SEF evaluation'), findsOneWidget);
        expect(find.text('SET & SEF'), findsOneWidget);
      }
      expect(find.textContaining('assessment-definitions.js'), findsNothing);
      await tester.pageBack();
      await tester.pumpAndSettle();
      expect(find.text('Assessment areas'), findsOneWidget);
    }

    await openArea('Extension', 'KRA III — Extension', expectSetSef: false);
    await openArea('Professional Development', 'KRA IV — Professional Development', expectSetSef: false);
    await openArea('Instruction', 'KRA I — Instruction', expectSetSef: true);
  });

  testWidgets('My Assessment quick action remains full overview', (tester) async {
    final repo = _repo();
    await _pumpHome(tester, repo);

    await tester.ensureVisible(find.text('My Assessment'));
    await tester.tap(find.text('My Assessment'));
    await tester.pumpAndSettle();

    expect(find.widgetWithText(AppBar, 'My Assessment'), findsOneWidget);
    expect(find.text('KRA I · Instruction'), findsOneWidget);
    expect(find.text('KRA II · Research'), findsOneWidget);
    expect(find.text('KRA III · Extension'), findsOneWidget);
    expect(find.text('KRA IV · Professional Development'), findsOneWidget);
    // SET/SEF not at top-level; only under expanded KRA I Criterion A
    expect(find.text('Upload SET / SEF evaluation'), findsNothing);

    final kraHeader = find.byKey(const ValueKey('kra-expand-kra-I'));
    await tester.ensureVisible(kraHeader);
    await tester.tap(kraHeader);
    await tester.pumpAndSettle();
    final criterionA = find.text('Criterion A – Teaching Effectiveness');
    await tester.ensureVisible(criterionA);
    expect(criterionA, findsOneWidget);
    expect(find.text('Upload SET / SEF evaluation'), findsNothing);

    await tester.tap(criterionA);
    await tester.pumpAndSettle();
    expect(find.text('Upload SET / SEF evaluation'), findsOneWidget);
    expect(find.text('SET & SEF'), findsOneWidget);
  });

  testWidgets('Scoped AssessmentTab ignores other KRA catalog rows', (tester) async {
    final repo = _repo();
    await tester.pumpWidget(
      MaterialApp(
        home: AssessmentTab(
          repo: repo,
          onSave: () async {},
          selectedKraId: 'kra-IV',
        ),
      ),
    );
    await tester.pump();

    expect(find.text('KRA IV — Professional Development'), findsOneWidget);
    expect(find.text('KRA I · Instruction'), findsNothing);
    expect(find.text('KRA II · Research'), findsNothing);
    expect(find.text('Academic Book'), findsNothing);
    expect(find.text('Upload SET / SEF evaluation'), findsNothing);
  });
}
