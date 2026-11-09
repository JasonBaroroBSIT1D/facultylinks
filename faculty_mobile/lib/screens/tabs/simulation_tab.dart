import 'package:flutter/material.dart';

import '../../models/institution_config.dart';
import '../../repositories/mock_repository.dart';
import '../../services/simulation_engine.dart';
import '../rank_simulation_screen.dart';

class SimulationTab extends StatefulWidget {
  final MockRepository repo;
  final InstitutionConfig institutionConfig;
  final WhatIfScenario whatIf;
  final ValueChanged<WhatIfScenario> onWhatIfChanged;
  final Future<void> Function() onRefresh;

  const SimulationTab({
    super.key,
    required this.repo,
    required this.institutionConfig,
    required this.whatIf,
    required this.onWhatIfChanged,
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
    return RankSimulationScreen(
      repo: widget.repo,
      institutionConfig: widget.institutionConfig,
      initialWhatIf: widget.whatIf,
      onWhatIfChanged: widget.onWhatIfChanged,
      embedInTab: true,
      onRefresh: widget.onRefresh,
    );
  }
}
