import 'dart:typed_data';

import 'package:faculty_mobile/core/ui_strings.dart';
import 'package:faculty_mobile/services/camera_document_capture.dart';
import 'package:faculty_mobile/services/selected_upload_file.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('camera SelectedUploadFile retains bytes for submit/retry', () {
    final bytes = List<int>.generate(1200, (i) => i % 256);
    final file = SelectedUploadFile(
      filename: 'document_photo_20260101.jpg',
      bytes: bytes,
      mimeType: 'image/jpeg',
      source: UploadFileSource.camera,
    );

    expect(file.isReadable, isTrue);
    expect(file.fromCamera, isTrue);
    expect(file.isImage, isTrue);
    expect(file.sizeBytes, 1200);
    // Same object retained across submit/retry attempts.
    expect(identical(file.bytes, bytes), isTrue);
  });

  test('file-picker selection is not marked as camera', () {
    const file = SelectedUploadFile(
      filename: 'scan.pdf',
      bytes: [1, 2, 3],
      mimeType: 'application/pdf',
    );
    expect(file.fromCamera, isFalse);
    expect(file.source, UploadFileSource.filePicker);
  });

  testWidgets('photo preview offers Retake and Use photo', (tester) async {
    bool? result;
    final jpegish = Uint8List.fromList(List<int>.filled(64, 0));

    await tester.pumpWidget(
      MaterialApp(
        home: Builder(
          builder: (context) {
            return Scaffold(
              body: TextButton(
                onPressed: () async {
                  result = await showCapturedPhotoPreview(
                    context,
                    bytes: jpegish,
                    filename: 'document_photo.jpg',
                  );
                },
                child: const Text('open'),
              ),
            );
          },
        ),
      ),
    );

    await tester.tap(find.text('open'));
    await tester.pumpAndSettle();

    expect(find.text('Use this photo?'), findsOneWidget);
    expect(find.text('Retake'), findsOneWidget);
    expect(find.text('Use photo'), findsOneWidget);
    expect(
      find.textContaining('not an automatic scan'),
      findsOneWidget,
    );

    await tester.tap(find.text('Use photo'));
    await tester.pumpAndSettle();
    expect(result, isTrue);
  });

  testWidgets('Retake returns false from preview', (tester) async {
    bool? result;
    final jpegish = Uint8List.fromList(List<int>.filled(32, 1));

    await tester.pumpWidget(
      MaterialApp(
        home: Builder(
          builder: (context) {
            return Scaffold(
              body: TextButton(
                onPressed: () async {
                  result = await showCapturedPhotoPreview(
                    context,
                    bytes: jpegish,
                    filename: 'document_photo.jpg',
                  );
                },
                child: const Text('open'),
              ),
            );
          },
        ),
      ),
    );

    await tester.tap(find.text('open'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Retake'));
    await tester.pumpAndSettle();
    expect(result, isFalse);
  });

  test('SET/SEF messaging states PDF-only specialized pipeline', () {
    expect(UiStrings.setSefCameraNotSupported.toLowerCase(), contains('pdf'));
    expect(UiStrings.setSefCameraNotSupported.toLowerCase(), contains('not supported'));
    expect(UiStrings.setSefUploadHint.toLowerCase(), contains('camera photos are not accepted'));
  });
}
