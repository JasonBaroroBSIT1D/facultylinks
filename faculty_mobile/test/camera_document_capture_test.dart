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

  test('upload copy invites multiple files or camera scans', () {
    expect(
      UiStrings.uploadDocumentHint,
      'Add your files or scan printed documents. You can attach more than one document.',
    );
    expect(UiStrings.setSefUploadHint, UiStrings.uploadDocumentHint);
    expect(UiStrings.scanWithCameraLabel, 'Scan with Camera');
    expect(UiStrings.addFilesLabel, 'Add files');
  });

  test('PendingDocumentUpload treats multi-page scan as one document', () {
    final pages = [
      SelectedUploadFile(
        filename: 'p1.jpg',
        bytes: [1, 2, 3],
        mimeType: 'image/jpeg',
        source: UploadFileSource.camera,
      ),
      SelectedUploadFile(
        filename: 'p2.jpg',
        bytes: [4, 5, 6],
        mimeType: 'image/jpeg',
        source: UploadFileSource.camera,
      ),
    ];
    final pending = PendingDocumentUpload.scanPages(pages);
    expect(pending.isMultiPage, isTrue);
    expect(pending.uploadAsPagesField, isTrue);
    expect(pending.displayName, '2-page scan');
    expect(pending.fromCamera, isTrue);
    expect(pending.sizeBytes, 6);
  });

  test('UploadSessionItem tracks per-document retry without clearing successes', () {
    final a = UploadSessionItem(
      localKey: 'a',
      document: PendingDocumentUpload.single(
        const SelectedUploadFile(filename: 'a.pdf', bytes: [1], mimeType: 'application/pdf'),
      ),
      status: UploadSessionItemStatus.uploaded,
      publicId: 'doc-a',
    );
    final b = UploadSessionItem(
      localKey: 'b',
      document: PendingDocumentUpload.single(
        const SelectedUploadFile(filename: 'b.pdf', bytes: [2], mimeType: 'application/pdf'),
      ),
      status: UploadSessionItemStatus.failed,
      errorMessage: 'network',
    );
    expect(a.isUploaded, isTrue);
    expect(a.needsUpload, isFalse);
    expect(b.needsUpload, isTrue);
    expect(b.isUploaded, isFalse);
  });
}
