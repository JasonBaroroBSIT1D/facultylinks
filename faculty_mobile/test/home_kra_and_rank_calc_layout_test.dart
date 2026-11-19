import 'package:faculty_mobile/models/institution_config.dart';
import 'package:faculty_mobile/repositories/mock_repository.dart';
import 'package:faculty_mobile/screens/rank_simulation_screen.dart';
import 'package:faculty_mobile/widgets/home_kra_grid.dart';
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

  for (final width in [320.0, 360.0, 412.0]) {
    testWidgets('Home Assessment areas fits ${width.toInt()}px', (tester) async {
      final repo = await MockRepository.load();
      await tester.binding.setSurfaceSize(Size(width, 800));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: MediaQuery(
              data: MediaQueryData(size: Size(width, 800), textScaler: TextScaler.noScaling),
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(16),
                child: HomeKraGrid(repo: repo, onOpenKra: (_) {}),
              ),
            ),
          ),
        ),
      );
      await tester.pump();

      expect(find.text('Assessment areas'), findsOneWidget);
      expect(find.text('KRA I'), findsOneWidget);
      expect(find.text('Instruction'), findsOneWidget);
      expect(find.text('Professional Development'), findsOneWidget);
      // Title is a full word token (not split across widgets).
      final instruction = tester.widget<Text>(find.text('Instruction'));
      expect(instruction.data, 'Instruction');
      expect(tester.takeException(), isNull);
      expect(_overflowIndicators(), findsNothing);
    });

    testWidgets('Home Assessment areas large text at ${width.toInt()}px', (tester) async {
      final repo = await MockRepository.load();
      await tester.binding.setSurfaceSize(Size(width, 900));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: MediaQuery(
              data: MediaQueryData(size: Size(width, 900), textScaler: const TextScaler.linear(1.3)),
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(16),
                child: HomeKraGrid(repo: repo, onOpenKra: (_) {}),
              ),
            ),
          ),
        ),
      );
      await tester.pump();

      expect(find.text('Professional Development'), findsOneWidget);
      expect(tester.takeException(), isNull);
      expect(_overflowIndicators(), findsNothing);
    });
  }

  testWidgets('Unified My Assessment screen builds without overflow at 360px', (tester) async {
    final repo = await MockRepository.load();
    await tester.binding.setSurfaceSize(const Size(360, 800));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: MediaQuery(
            data: const MediaQueryData(size: Size(360, 800)),
            child: RankSimulationScreen(
              repo: repo,
              institutionConfig: InstitutionConfig.defaults(),
              embedInTab: true,
            ),
          ),
        ),
      ),
    );
    await tester.pump();

    expect(find.text('My Assessment'), findsOneWidget);
    expect(find.text('Current rank'), findsOneWidget);
    expect(find.text('Potential rank'), findsWidgets);
    expect(find.text('What-if points'), findsNothing);
    expect(find.text('Try a Scenario'), findsNothing);
    expect(find.text('Reset Scenario'), findsNothing);
    expect(tester.takeException(), isNull);
    expect(_overflowIndicators(), findsNothing);
  });
}
