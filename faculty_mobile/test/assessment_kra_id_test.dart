import 'package:faculty_mobile/data/assessment_catalog.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('kraIdFromCriterion resolves parent KRA not criterion', () {
    expect(kraIdFromCriterion('kra-III-B'), 'kra-III');
    expect(kraIdFromCriterion('kra-III-B-2-1'), 'kra-III');
    expect(kraIdFromCriterion('kra-II-C'), 'kra-II');
    expect(kraIdFromCriterion('kra-I-B'), 'kra-I');
    expect(kraIdFromCriterion('kra-IV-A'), 'kra-IV');
  });

  test('kraIdFromIndicator prefers criterion when provided', () {
    expect(
      kraIdFromIndicator('kra-III-B-2-1', criterionId: 'kra-III-B'),
      'kra-III',
    );
    expect(kraIdFromIndicator('kra-III-B-2-1'), 'kra-III');
    expect(kraIdFromIndicator('kra-II-B-1-1'), 'kra-II');
  });

  test('kraIdFromPublishedCatalog walks catalog hierarchy', () {
    final kras = parsePublishedCatalog({
      'kras': [
        {
          'id': 'kra-III',
          'criteria': [
            {
              'id': 'kra-III-B',
              'indicators': [
                {'id': 'kra-III-B-2-1', 'name': 'ISR'},
              ],
            },
          ],
        },
      ],
    });
    expect(kraIdFromPublishedCatalog(kras, 'kra-III-B-2-1'), 'kra-III');
    expect(kraIdFromPublishedCatalog(kras, 'missing'), isNull);
  });
}
