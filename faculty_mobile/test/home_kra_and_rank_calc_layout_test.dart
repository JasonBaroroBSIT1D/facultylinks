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
                child: HomeKraGrid(repo: repo, onOpenAssessment: () {}),
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
                child: HomeKraGrid(repo: repo, onOpenAssessment: () {}),
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

  testWidgets('Rank simulation screen builds without overflow at 360px', (tester) async {
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

    expect(find.text('Rank simulation'), findsOneWidget);
    expect(tester.takeException(), isNull);
    expect(_overflowIndicators(), findsNothing);

    final viewCalc = find.text('View calculation');
    if (viewCalc.evaluate().isNotEmpty) {
      await tester.ensureVisible(viewCalc);
      await tester.tap(viewCalc);
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
      expect(_overflowIndicators(), findsNothing);
    }
  });
}
