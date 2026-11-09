import 'package:faculty_mobile/screens/document_detail_screen.dart';
import 'package:faculty_mobile/repositories/mock_repository.dart';
import 'package:faculty_mobile/widgets/set_sef_semester_list.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

List<Map<String, dynamic>> _sampleRecords() => [
      {
        'academicYear': '2023-2024',
        'semester': '1st Semester',
        'facultyNameExtracted': 'Jason Baroro',
        'setRatingExtracted': 91.0,
        'sefRatingExtracted': 93.5,
        'setRatingConfirmed': 92.0,
        'sefRatingConfirmed': 94.0,
        'setVerificationStatus': 'verified',
        'sefVerificationStatus': 'verified',
        'setSourcePages': [1],
        'sefSourcePages': [1],
      },
      {
        'academicYear': '2023-2024',
        'semester': '2nd Semester',
        'facultyNameExtracted': 'Jason Baroro',
        'setRatingExtracted': 88.0,
        'sefRatingExtracted': null,
        'setRatingConfirmed': null,
        'sefRatingConfirmed': null,
        'setVerificationStatus': 'pending',
        'sefVerificationStatus': 'pending',
        'setSourcePages': [2],
        'sefSourcePages': [],
      },
    ];

Widget _harness({
  required double width,
  required Widget child,
  double textScale = 1.0,
}) {
  return MaterialApp(
    home: MediaQuery(
      data: MediaQueryData(
        size: Size(width, 900),
        textScaler: TextScaler.linear(textScale),
      ),
      child: Scaffold(body: SingleChildScrollView(padding: const EdgeInsets.all(16), child: child)),
    ),
  );
}

void main() {
  setUpAll(() {
    TestWidgetsFlutterBinding.ensureInitialized();
    SharedPreferences.setMockInitialValues({});
  });

  for (final width in [320.0, 390.0, 600.0]) {
    testWidgets('semester cards show SET/SEF at ${width.toInt()}px without overflow', (tester) async {
      await tester.binding.setSurfaceSize(Size(width, 900));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await tester.pumpWidget(
        _harness(
          width: width,
          textScale: 1.3,
          child: SetSefSemesterList(records: _sampleRecords()),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Jason Baroro'), findsOneWidget);
      expect(find.textContaining('SET: 92.00'), findsOneWidget);
      expect(find.textContaining('SEF: 94.00'), findsOneWidget);
      expect(find.text('SET: Verified'), findsWidgets);
      expect(find.textContaining('Source: Page 1'), findsOneWidget);
      expect(find.textContaining('SEF: Not available'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  }

  testWidgets('DocumentDetailScreen route uses semester cards (not DataTable)', (tester) async {
    final repo = MockRepository();
    repo.profile.name = 'Faculty User';
    final doc = FacultyDocument(
      id: 'doc-test',
      indicatorId: 'kra-I-A-setsef-eval',
      kraId: 'kra-I',
      fileName: 'set-sef.pdf',
      reviewStatus: 'approved',
      documentKind: 'set_sef_unified',
      processingStatus: 'completed',
      ocrStatus: 'completed',
    );

    await tester.binding.setSurfaceSize(const Size(390, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      MaterialApp(
        home: DocumentDetailScreen(doc: doc, repo: repo),
      ),
    );
    await tester.pump();

    expect(find.byType(DataTable), findsNothing);
    expect(find.text('Extracted semesters'), findsOneWidget);
  });
}
