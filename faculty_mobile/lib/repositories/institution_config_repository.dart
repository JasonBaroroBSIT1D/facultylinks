import 'dart:convert';

import '../models/institution_config.dart';
import '../services/api_client.dart';

class InstitutionConfigRepository {
  static Future<InstitutionConfig> load() async {
    try {
      final res = await ApiClient.get('/api/config/institution');
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body) as Map<String, dynamic>;
        if (data['configured'] == true && data['institutionConfig'] != null) {
          return InstitutionConfig.fromJson(data['institutionConfig'] as Map<String, dynamic>);
        }
      }
    } catch (_) {
      /* fall through */
    }
    return InstitutionConfig.defaults();
  }
}
