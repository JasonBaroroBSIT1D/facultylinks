import 'dart:convert';

import 'api_client.dart';

class AchievementApi {
  static Future<List<Map<String, dynamic>>> list({String? criterionId, String? indicatorId}) async {
    final q = <String>[];
    if (criterionId != null) q.add('criterionId=${Uri.encodeQueryComponent(criterionId)}');
    if (indicatorId != null) q.add('indicatorId=${Uri.encodeQueryComponent(indicatorId)}');
    final path = '/api/faculty/achievements${q.isEmpty ? '' : '?${q.join('&')}'}';
    final res = await ApiClient.get(path);
    if (res.statusCode != 200) throw Exception('Failed to load achievements');
    final body = jsonDecode(res.body) as Map<String, dynamic>;
    return (body['achievements'] as List<dynamic>? ?? []).cast<Map<String, dynamic>>();
  }

  static Future<Map<String, dynamic>> previewRule(Map<String, dynamic> fields) async {
    final res = await ApiClient.postJson('/api/faculty/achievements/preview-rule', fields);
    return (jsonDecode(res.body) as Map<String, dynamic>);
  }

  static Future<Map<String, dynamic>> create(Map<String, dynamic> body) async {
    final res = await ApiClient.postJson('/api/faculty/achievements', body);
    if (res.statusCode != 201) {
      final err = jsonDecode(res.body) as Map<String, dynamic>;
      throw Exception(err['error'] ?? 'Create failed');
    }
    return (jsonDecode(res.body) as Map<String, dynamic>)['achievement'] as Map<String, dynamic>;
  }

  static Future<Map<String, dynamic>> update(String id, Map<String, dynamic> patch) async {
    final res = await ApiClient.putJson('/api/faculty/achievements/$id', patch);
    if (res.statusCode != 200) {
      final err = jsonDecode(res.body) as Map<String, dynamic>;
      throw Exception(err['error'] ?? 'Update failed');
    }
    return (jsonDecode(res.body) as Map<String, dynamic>)['achievement'] as Map<String, dynamic>;
  }

  static Future<Map<String, dynamic>> submit(String id, {Map<String, dynamic>? body}) async {
    final res = await ApiClient.postJson('/api/faculty/achievements/$id/submit', body ?? {});
    if (res.statusCode != 200) {
      final err = jsonDecode(res.body) as Map<String, dynamic>;
      throw Exception(err['error'] ?? 'Submit failed');
    }
    return (jsonDecode(res.body) as Map<String, dynamic>)['achievement'] as Map<String, dynamic>;
  }
}
