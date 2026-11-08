import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';

import '../core/api_config.dart';
import 'api_client.dart';

class DocumentApi {
  static Future<List<Map<String, dynamic>>> listMine() async {
    final res = await ApiClient.get('/api/documents');
    if (res.statusCode != 200) {
      throw Exception('Could not load documents.');
    }
    final data = jsonDecode(res.body) as Map<String, dynamic>;
    return (data['documents'] as List<dynamic>).cast<Map<String, dynamic>>();
  }

  static Future<Map<String, dynamic>> upload({
    required List<int> bytes,
    required String filename,
    required String mimeType,
    required String indicatorId,
    required String kraId,
    String? title,
    double? estimatedPoints,
  }) async {
    final req = http.MultipartRequest('POST', ApiConfig.uri('/api/documents'));
    final headers = await ApiClient.headers(jsonBody: false);
    req.headers.addAll(headers);
    req.fields['indicatorId'] = indicatorId;
    req.fields['kraId'] = kraId;
    if (title != null && title.isNotEmpty) req.fields['title'] = title;
    if (estimatedPoints != null) req.fields['estimatedPoints'] = estimatedPoints.toString();
    req.files.add(
      http.MultipartFile.fromBytes(
        'file',
        bytes,
        filename: filename,
        contentType: MediaType.parse(mimeType),
      ),
    );
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
}
