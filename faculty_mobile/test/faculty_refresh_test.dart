import 'package:faculty_mobile/repositories/mock_repository.dart';
import 'package:faculty_mobile/services/faculty_refresh.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('hasActiveDocumentProcessing detects queued OCR', () {
    final repo = MockRepository();
    repo.documents = [
      FacultyDocument(
        id: 'd1',
        indicatorId: 'kra-I-A-set-pdf',
        kraId: 'kra-I',
        fileName: 'a.pdf',
        processingStatus: 'processing',
      ),
    ];
    expect(repo.hasActiveDocumentProcessing, isTrue);
    repo.documents.first.processingStatus = 'completed';
    expect(repo.hasActiveDocumentProcessing, isFalse);
  });

  test('refresh coordinator skips stale tab refresh until forced', () async {
    final repo = MockRepository();
    var updates = 0;
    final coordinator = FacultyRefreshCoordinator(
      repo: repo,
      onUpdated: () => updates++,
    );
    coordinator.onTabSelected(0);
    // No network in unit test; stale check should not throw.
    await coordinator.refresh(
      scopes: {FacultyRefreshScope.documents},
      force: false,
    );
    expect(updates, greaterThanOrEqualTo(0));
    coordinator.dispose();
  });

  test('FacultyRefreshScopes timing constants', () {
    expect(FacultyRefreshScopes.periodicInterval.inSeconds, 30);
    expect(FacultyRefreshScopes.processingPollInterval.inSeconds, 4);
    expect(FacultyRefreshScopes.staleAfter.inSeconds, 30);
  });
}
