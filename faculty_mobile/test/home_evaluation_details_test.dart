import 'package:faculty_mobile/models/institution_config.dart';
import 'package:faculty_mobile/repositories/mock_repository.dart';
import 'package:faculty_mobile/screens/evaluation_details_screen.dart';
import 'package:faculty_mobile/widgets/home_progress_overview.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

Finder _overflowIndicators() => find.byWidgetPredicate(
      (w) => w.runtimeType.toString().contains('OverflowIndicator'),
    );

void main() {
  setUpAll(() {
    TestWidgetsFlutterBinding.ensureInitialized();
    SharedPreferences.setMockInitialValues({});
  });

  Future<void> pumpHomeWithOverview(
    WidgetTester tester, {
    required Size size,
    TextScaler scaler = TextScaler.noScaling,
    FacultyProfile? profile,
    PreparationPeriod? period,
  }) async {
    final repo = MockRepository();
    repo.profile = profile ??
        FacultyProfile(
          id: 'f1',
          name: 'Faculty User',
          email: 'f@example.com',
          rank: 'Instructor I',
          reviewerName: 'Ana Reviewer',
          reviewerRole: 'Assigned Evaluator',
          reviewerAssignmentStatus: 'Active',
        );
    final cfg = InstitutionConfig.defaults();
    final institution = InstitutionConfig(
      preparationPeriod: period ??
          PreparationPeriod(
            start: DateTime(2026, 1, 15),
            end: DateTime(2026, 6, 30),
            reviewerAvailableFrom: DateTime(2026, 2, 1),
          ),
      rankOptions: cfg.rankOptions,
      rankRequirements: cfg.rankRequirements,
      rankMappingStatus: cfg.rankMappingStatus,
    );

    await tester.binding.setSurfaceSize(size);
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: MediaQuery(
            data: MediaQueryData(size: size, textScaler: scaler),
            child: Builder(
              builder: (context) => SingleChildScrollView(
                padding: const EdgeInsets.all(16),
                child: HomeProgressOverview(
                  repo: repo,
                  institutionConfig: institution,
                  onOpenSimulationModal: () {},
                  onOpenEvaluationDetails: () {
                    Navigator.of(context).push(
                      MaterialPageRoute(
                        settings: const RouteSettings(name: EvaluationDetailsScreen.routeName),
                        builder: (_) => EvaluationDetailsScreen(
                          period: institution.preparationPeriod,
                          profile: repo.profile,
                        ),
                      ),
                    );
                  },
                ),
              ),
            ),
          ),
        ),
      ),
    );
    await tester.pump();
  }

  testWidgets('home shows one combined evaluation tile', (tester) async {
    await pumpHomeWithOverview(tester, size: const Size(360, 800));

    expect(find.text('Evaluation & reviewer details'), findsOneWidget);
    expect(find.text('View your schedule and assigned reviewer'), findsOneWidget);
    expect(find.text('Evaluation Period'), findsNothing);
    expect(find.text('Your Reviewer'), findsNothing);
    expect(find.text('Ana Reviewer'), findsNothing);
    expect(find.byIcon(Icons.chevron_right), findsOneWidget);
    expect(find.text('Assessment outlook'), findsOneWidget);
    expect(tester.takeException(), isNull);
    expect(_overflowIndicators(), findsNothing);
  });

  testWidgets('tapping tile opens schedule and reviewer together', (tester) async {
    await pumpHomeWithOverview(tester, size: const Size(400, 1200));

    await tester.tap(find.text('Evaluation & reviewer details'));
    await tester.pumpAndSettle();

    expect(find.byType(EvaluationDetailsScreen), findsOneWidget);
    expect(find.text('Evaluation schedule'), findsOneWidget);
    expect(find.text('Assigned reviewer'), findsOneWidget);
    expect(find.textContaining('Jan 15, 2026'), findsWidgets);
    expect(find.textContaining('Jun 30, 2026'), findsWidgets);
    expect(find.text('Ana Reviewer'), findsOneWidget);
    expect(find.text('Assigned Evaluator'), findsOneWidget);
    expect(find.text('You can still prepare documents and check estimated points.'), findsOneWidget);

    await tester.pageBack();
    await tester.pumpAndSettle();
    expect(find.text('Evaluation & reviewer details'), findsOneWidget);
  });

  testWidgets('details page handles unassigned reviewer', (tester) async {
    await pumpHomeWithOverview(
      tester,
      size: const Size(400, 1200),
      profile: FacultyProfile(
        id: 'f1',
        name: 'Faculty User',
        email: 'f@example.com',
        rank: 'Instructor I',
        reviewerName: '',
        reviewerAssignmentStatus: 'Unassigned',
      ),
    );

    await tester.tap(find.text('Evaluation & reviewer details'));
    await tester.pumpAndSettle();

    expect(find.text('No reviewer assigned yet'), findsOneWidget);
    expect(find.text('Evaluation schedule'), findsOneWidget);
  });

  for (final width in [320.0, 360.0]) {
    testWidgets('combined tile fits ${width.toInt()}px with large text', (tester) async {
      await pumpHomeWithOverview(
        tester,
        size: Size(width, 900),
        scaler: const TextScaler.linear(1.3),
      );

      expect(find.text('Evaluation & reviewer details'), findsOneWidget);
      expect(find.text('View your schedule and assigned reviewer'), findsOneWidget);
      expect(tester.takeException(), isNull);
      expect(_overflowIndicators(), findsNothing);
    });
  }
}
