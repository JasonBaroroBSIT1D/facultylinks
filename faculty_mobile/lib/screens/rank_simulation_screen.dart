import 'package:flutter/material.dart';

import '../models/institution_config.dart';
import '../repositories/mock_repository.dart';
import 'tabs/assessment_tab.dart';

/// Compatibility entry for older links/tests — opens the unified My Assessment screen.
///
/// Prefer [AssessmentTab] (shell tab or push) for new navigation.
class RankSimulationScreen extends StatelessWidget {
  final MockRepository repo;
  final InstitutionConfig institutionConfig;
  final bool embedInTab;
  final Future<void> Function()? onRefresh;

  const RankSimulationScreen({
    super.key,
    required this.repo,
    required this.institutionConfig,
    this.embedInTab = false,
    this.onRefresh,
  });

  @override
  Widget build(BuildContext context) {
    return AssessmentTab(
      repo: repo,
      institutionConfig: institutionConfig,
      onSave: onRefresh ?? () async {},
      embedInTab: embedInTab,
    );
  }
}
