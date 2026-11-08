import 'package:flutter_test/flutter_test.dart';
import 'package:faculty_mobile/main.dart';

void main() {
  testWidgets('App smoke test', (tester) async {
    await tester.pumpWidget(const FacultyLinkApp());
    expect(find.textContaining('Faculty'), findsWidgets);
  });
}
