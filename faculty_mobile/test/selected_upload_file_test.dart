import 'dart:typed_data';

import 'package:faculty_mobile/services/selected_upload_file.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('SelectedUploadFile requires non-empty bytes', () {
    const empty = SelectedUploadFile(filename: 'a.pdf', bytes: [], mimeType: 'application/pdf');
    const ok = SelectedUploadFile(filename: 'a.pdf', bytes: [1, 2, 3], mimeType: 'application/pdf');
    expect(empty.isReadable, isFalse);
    expect(ok.isReadable, isTrue);
    expect(ok.sizeBytes, 3);
  });

  test('readPlatformFileForUpload uses withData bytes', () async {
    final file = PlatformFile(
      name: 'rating.pdf',
      size: 4,
      bytes: Uint8List.fromList([37, 80, 68, 70]), // %PDF
    );
    final loaded = await readPlatformFileForUpload(file);
    expect(loaded, isNotNull);
    expect(loaded!.filename, 'rating.pdf');
    expect(loaded.mimeType, 'application/pdf');
    expect(loaded.bytes, [37, 80, 68, 70]);
  });

  test('readPlatformFileForUpload returns null when name empty', () async {
    final file = PlatformFile(name: '  ', size: 0, bytes: Uint8List.fromList([1]));
    expect(await readPlatformFileForUpload(file), isNull);
  });

  test('readPlatformFileForUpload marks source as filePicker', () async {
    final file = PlatformFile(
      name: 'photo.jpg',
      size: 3,
      bytes: Uint8List.fromList([1, 2, 3]),
    );
    final loaded = await readPlatformFileForUpload(file);
    expect(loaded!.source, UploadFileSource.filePicker);
    expect(loaded.mimeType, 'image/jpeg');
    expect(loaded.isImage, isTrue);
  });
}
