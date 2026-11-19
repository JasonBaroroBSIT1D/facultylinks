import 'package:flutter/material.dart';

import '../../models/institution_config.dart';
import '../../repositories/mock_repository.dart';
import 'assessment_tab.dart';

/// Shell Assessment tab — unified My Assessment (formerly Simulation).
class SimulationTab extends StatefulWidget {
  final MockRepository repo;
  final InstitutionConfig institutionConfig;
  final Future<void> Function() onRefresh;

  const SimulationTab({
    super.key,
    required this.repo,
    required this.institutionConfig,
    required this.onRefresh,
  });

  @override
  State<SimulationTab> createState() => _SimulationTabState();
}

class _SimulationTabState extends State<SimulationTab> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      widget.onRefresh();
    });
  }

  @override
  Widget build(BuildContext context) {
    return AssessmentTab(
      key: const ValueKey('assessment-shell-tab'),
      repo: widget.repo,
      institutionConfig: widget.institutionConfig,
      onSave: widget.onRefresh,
      embedInTab: true,
    );
  }
}
