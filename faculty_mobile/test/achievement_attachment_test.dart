import 'dart:typed_data';

import 'package:faculty_mobile/services/achievement_attachment_upload.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('validatePickedFile allows pdf and images within size limit', () {
    expect(validatePickedFile(filename: 'a.pdf', size: 1000, extension: 'pdf'), isNull);
    expect(validatePickedFile(filename: 'b.png', size: 1000, extension: 'png'), isNull);
    expect(validatePickedFile(filename: 'c.exe', size: 1000, extension: 'exe'), isNotNull);
    expect(validatePickedFile(filename: 'big.pdf', size: kMaxUploadBytes + 1, extension: 'pdf'), isNotNull);
  });

  test('upload skips when document id already set', () async {
    final item = AchievementAttachment(
      localKey: 'k1',
      filename: 'x.pdf',
      sizeBytes: 10,
      bytes: Uint8List.fromList([1, 2, 3]),
      mimeType: 'application/pdf',
      documentPublicId: 'existing-id',
      status: AchievementAttachmentStatus.uploaded,
    );
    await uploadAchievementAttachment(
      item: item,
      indicatorId: 'kra-I-B-1-2',
      kraId: 'kra-I',
    );
    expect(item.documentPublicId, 'existing-id');
    expect(item.status, AchievementAttachmentStatus.uploaded);
  });
}
