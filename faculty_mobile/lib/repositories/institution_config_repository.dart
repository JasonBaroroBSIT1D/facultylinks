import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import '../models/institution_config.dart';

class InstitutionConfigRepository {
  static const _key = 'facultylink_institution_config_v1';

  static Future<InstitutionConfig> load() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_key);
    if (raw == null) {
      final defaults = InstitutionConfig.defaults();
      await save(defaults);
      return defaults;
    }
    return InstitutionConfig.fromJson(jsonDecode(raw) as Map<String, dynamic>);
  }

  static Future<void> save(InstitutionConfig cfg) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_key, jsonEncode(cfg.toJson()));
  }
}
