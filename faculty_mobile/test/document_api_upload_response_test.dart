import 'package:faculty_mobile/services/document_api.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('publicIdFromUploadResponse reads canonical id from document object', () {
    const uuid = 'a1b2c3d4-e5f6-7890-abcd-ef1234567890';
    final body = {
      'document': {
        'id': uuid,
        'fileName': 'evidence.pdf',
        'uploadStatus': 'stored',
      },
    };
    expect(DocumentApi.publicIdFromUploadResponse(body), uuid);
  });

  test('publicIdFromUploadResponse accepts explicit publicId', () {
    const uuid = 'b2c3d4e5-f6a7-8901-bcde-f12345678901';
    expect(
      DocumentApi.publicIdFromUploadResponse({
        'document': {'publicId': uuid, 'id': uuid},
      }),
      uuid,
    );
  });

  test('publicIdFromUploadResponse rejects internal numeric id', () {
    expect(
      DocumentApi.publicIdFromUploadResponse({
        'document': {'id': '42', 'fileName': 'x.pdf'},
      }),
      isNull,
    );
  });

  test('publicIdFromUploadResponse matches backend upload JSON shape', () {
    const uuid = 'c3d4e5f6-a7b8-9012-cdef-123456789012';
    final body = {
      'document': {
        'id': uuid,
        'publicId': uuid,
        'filename': 'module.pdf',
        'fileName': 'module.pdf',
        'mimeType': 'application/pdf',
        'sizeBytes': 1024,
        'indicatorId': 'kra-I-B-1-2',
        'kraId': 'kra-I',
        'uploadStatus': 'stored',
      },
    };
    expect(DocumentApi.publicIdFromUploadResponse(body), uuid);
  });
}
