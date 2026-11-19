import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';

import '../core/api_config.dart';
import 'api_client.dart';

class DocumentApi {
  /// POST `/api/documents` returns `{ "document": { "id": "<public_uuid>", ... } }`.
  /// The `id` field is the canonical public identifier (not the internal numeric row id).
  static String? publicIdFromUploadResponse(Map<String, dynamic> body) {
    final nested = body['document'];
    if (nested is Map) {
      final fromDoc = nested['publicId'] ?? nested['id'];
      if (fromDoc != null) {
        final s = fromDoc.toString().trim();
        if (s.isNotEmpty && _isPublicDocumentId(s)) return s;
      }
    }
    final top = body['publicId'] ?? body['id'];
    if (top != null) {
      final s = top.toString().trim();
      if (s.isNotEmpty && _isPublicDocumentId(s)) return s;
    }
    return null;
  }

  static bool _isPublicDocumentId(String id) {
    if (RegExp(r'^\d{1,9}$').hasMatch(id)) return false;
    return true;
  }

  /// After a successful upload with a missing id in the response, match an already-stored file.
  static Future<String?> reconcileStoredUpload({
    required String filename,
    required String indicatorId,
    required int sizeBytes,
  }) async {
    final docs = await listMine();
    for (final d in docs) {
      final name = (d['fileName'] ?? d['filename'])?.toString();
      if (name != filename) continue;
      if ((d['indicatorId']?.toString() ?? '') != indicatorId) continue;
      final size = (d['sizeBytes'] as num?)?.toInt();
      if (size != null && size != sizeBytes) continue;
      final status = d['uploadStatus']?.toString() ?? 'stored';
      if (status != 'stored' && status != 'pending') continue;
      final id = d['publicId'] ?? d['id'];
      if (id == null) continue;
      final s = id.toString().trim();
      if (s.isNotEmpty && _isPublicDocumentId(s)) return s;
    }
    return null;
  }

  static Future<List<Map<String, dynamic>>> listMine() async {
    final res = await ApiClient.get('/api/documents');
    if (res.statusCode != 200) {
      throw Exception('Could not load documents.');
    }
    final data = jsonDecode(res.body) as Map<String, dynamic>;
    return (data['documents'] as List<dynamic>).cast<Map<String, dynamic>>();
  }

  /// Upload one document. Pass either a single [bytes]/[filename]/[mimeType]
  /// or [pages] (one or more camera/scan images). Multiple [pages] are sent as
  /// repeated multipart fields named `pages` and stored as one document.
  static Future<Map<String, dynamic>> upload({
    List<int>? bytes,
    String? filename,
    String? mimeType,
    List<({List<int> bytes, String filename, String mimeType})>? pages,
    required String indicatorId,
    required String kraId,
    String? criterionId,
    String? title,
    double? estimatedPoints,
    String? replacesDocumentId,
  }) async {
    final req = http.MultipartRequest('POST', ApiConfig.uri('/api/documents'));
    final headers = await ApiClient.headers(jsonBody: false);
    req.headers.addAll(headers);
    req.fields['indicatorId'] = indicatorId;
    req.fields['kraId'] = kraId;
    if (criterionId != null && criterionId.isNotEmpty) {
      req.fields['criterionId'] = criterionId;
    }
    if (title != null && title.isNotEmpty) req.fields['title'] = title;
    if (estimatedPoints != null) req.fields['estimatedPoints'] = estimatedPoints.toString();
    if (replacesDocumentId != null && replacesDocumentId.isNotEmpty) {
      req.fields['replacesDocumentId'] = replacesDocumentId;
    }

    final multi = pages;
    if (multi != null && multi.length > 1) {
      for (final page in multi) {
        req.files.add(
          http.MultipartFile.fromBytes(
            'pages',
            page.bytes,
            filename: page.filename,
            contentType: MediaType.parse(page.mimeType),
          ),
        );
      }
    } else if (multi != null && multi.length == 1) {
      final page = multi.first;
      req.files.add(
        http.MultipartFile.fromBytes(
          'file',
          page.bytes,
          filename: page.filename,
          contentType: MediaType.parse(page.mimeType),
        ),
      );
    } else if (bytes != null && filename != null && mimeType != null) {
      req.files.add(
        http.MultipartFile.fromBytes(
          'file',
          bytes,
          filename: filename,
          contentType: MediaType.parse(mimeType),
        ),
      );
    } else {
      throw Exception('No file provided for upload.');
    }

    final streamed = await req.send();
    final res = await http.Response.fromStream(streamed);
    if (res.statusCode != 201) {
      final err = jsonDecode(res.body) as Map<String, dynamic>?;
      throw Exception(err?['error'] ?? 'Upload failed.');
    }
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  static Future<String> viewUrl(String publicId) async {
    final res = await ApiClient.get('/api/documents/$publicId/view-url');
    if (res.statusCode != 200) {
      throw Exception('Not authorized or not found.');
    }
    final data = jsonDecode(res.body) as Map<String, dynamic>;
    return data['url'] as String;
  }

  static Future<Map<String, dynamic>> fetchValidation(String documentId) async {
    final res = await ApiClient.get('/api/documents/$documentId/validation');
    if (res.statusCode != 200) {
      final err = jsonDecode(res.body) as Map<String, dynamic>?;
      throw Exception(err?['error'] ?? 'Could not load document validation.');
    }
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  /// After a replacement upload (`correction_prepared`), faculty explicitly re-queues review.
  static Future<Map<String, dynamic>> resubmitForReview(String publicId) async {
    final res = await ApiClient.postJson('/api/documents/$publicId/resubmit', {});
    if (res.statusCode != 200) {
      final err = jsonDecode(res.body) as Map<String, dynamic>?;
      throw Exception(err?['error'] ?? 'Could not resubmit for review.');
    }
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  static Future<void> retryValidationOcr(String documentId) async {
    final res = await ApiClient.postJson('/api/documents/$documentId/validation/retry-ocr', {});
    if (res.statusCode != 200 && res.statusCode != 201 && res.statusCode != 202) {
      final err = jsonDecode(res.body) as Map<String, dynamic>?;
      throw Exception(err?['error'] ?? 'Could not retry text check.');
    }
  }
}
