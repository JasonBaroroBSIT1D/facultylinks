import 'dart:convert';

import 'api_client.dart';

class SetSefApi {
  static Future<Map<String, dynamic>> fetchExtraction(String documentId) async {
    final res = await ApiClient.get('/api/documents/$documentId/set-sef');
    if (res.statusCode == 403) {
      throw Exception('Not authorized to view this document.');
    }
    if (res.statusCode == 404) {
      throw Exception('Document not found.');
    }
    if (res.statusCode != 200) {
      final err = jsonDecode(res.body) as Map<String, dynamic>?;
      throw Exception(err?['error'] ?? 'Could not load SET/SEF extraction.');
    }
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  static Future<void> retryOcr(String documentId) async {
    final res = await ApiClient.postJson('/api/documents/$documentId/set-sef/retry-ocr', {});
    if (res.statusCode != 200 && res.statusCode != 201 && res.statusCode != 202) {
      final err = jsonDecode(res.body) as Map<String, dynamic>?;
      throw Exception(err?['error'] ?? 'Could not retry OCR.');
    }
  }

  static Future<Map<String, dynamic>> fetchCriterionA() async {
    final res = await ApiClient.get('/api/faculty/teaching-effectiveness/criterion-a');
    if (res.statusCode != 200) {
      final err = jsonDecode(res.body) as Map<String, dynamic>?;
      throw Exception(err?['error'] ?? 'Could not load Criterion A totals.');
    }
    return jsonDecode(res.body) as Map<String, dynamic>;
  }
}
