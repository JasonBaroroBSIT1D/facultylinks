import 'package:flutter/material.dart';

import '../core/simulation_presenter.dart';
import '../core/ui_strings.dart';
import '../data/assessment_catalog.dart';
import '../models/institution_config.dart';
import '../repositories/mock_repository.dart';
import '../services/simulation_engine.dart';
import '../theme/app_spacing.dart';
import '../theme/app_theme.dart';

class RankSimulationScreen extends StatefulWidget {
  final MockRepository repo;
  final InstitutionConfig institutionConfig;
  final WhatIfScenario initialWhatIf;
  final ValueChanged<WhatIfScenario>? onWhatIfChanged;
  final bool embedInTab;

  const RankSimulationScreen({
    super.key,
    required this.repo,
    required this.institutionConfig,
    this.initialWhatIf = WhatIfScenario.empty,
    this.onWhatIfChanged,
    this.embedInTab = false,
  });

  @override
  State<RankSimulationScreen> createState() => _RankSimulationScreenState();
}

class _RankSimulationScreenState extends State<RankSimulationScreen> {
  late WhatIfScenario _whatIf;
  late String _targetRank;
  bool _showVerified = false;
  final _whatIfKraCtrl = TextEditingController();
  final _whatIfInstrCtrl = TextEditingController(text: '0');

  @override
  void initState() {
    super.initState();
    _whatIf = widget.initialWhatIf;
    _targetRank = SimulationEngine.nextRankOption(widget.institutionConfig, widget.repo.profile.rank);
  }

  @override
  void dispose() {
    _whatIfKraCtrl.dispose();
    _whatIfInstrCtrl.dispose();
    super.dispose();
  }

  void _applyWhatIf() {
    final kraExtra = double.tryParse(_whatIfKraCtrl.text) ?? 0;
    final instr = double.tryParse(_whatIfInstrCtrl.text) ?? 0;
    setState(() {
      _whatIf = WhatIfScenario(
        extraWeightedByKra: {'kra-II': kraExtra},
        extraInstructionRaw: instr,
      );
    });
    widget.onWhatIfChanged?.call(_whatIf);
  }

  void _resetScenario() {
    setState(() {
      _whatIf = WhatIfScenario.empty;
      _whatIfKraCtrl.clear();
      _whatIfInstrCtrl.text = '0';
    });
    widget.onWhatIfChanged?.call(WhatIfScenario.empty);
  }

  String _kraShort(String kraId) {
    final k = assessmentKras.where((e) => e.id == kraId).firstOrNull;
    return k?.shortDropdownLabel ?? kraId;
  }

  @override
  Widget build(BuildContext context) {
    final est = SimulationEngine.compute(widget.repo, whatIf: _whatIf);
    final ver = SimulationEngine.compute(widget.repo, verified: true, whatIf: _whatIf);
    final active = _showVerified ? ver : est;
    final eval = SimulationEngine.evaluateTarget(
      cfg: widget.institutionConfig,
      targetRank: _targetRank,
      weightedTotal: active.weightedTotal,
    );
    final potential = SimulationPresenter.potentialRankLabel(eval, widget.institutionConfig);
    final readiness = SimulationPresenter.readinessLine(eval, widget.institutionConfig);
    final rulesNote = SimulationPresenter.rankRulesNotice(widget.institutionConfig);
    final scale = MediaQuery.textScalerOf(context);

    final body = ListView(
      padding: FlLayout.pagePadding,
      children: [
        FlSurfaceCard(
          child: Text(UiStrings.simDisclaimer, style: TextStyle(fontSize: scale.scale(16), height: 1.5)),
        ),
        const SizedBox(height: 12),
        Text(
          'See if you are on track. Committees make the official promotion decision.',
          style: TextStyle(fontSize: scale.scale(17), color: AppColors.textMuted, height: 1.45),
        ),
        const SizedBox(height: FlLayout.sectionGap),
        FlSectionTitle('1. Your current rank'),
        FlSurfaceCard(
          child: Text(
            widget.repo.profile.rank,
            style: TextStyle(fontSize: scale.scale(20), fontWeight: FontWeight.w700),
          ),
        ),
        const SizedBox(height: FlLayout.sectionGap),
        FlSectionTitle('2. Your points'),
        Semantics(
          label: 'Choose estimated or reviewer verified points',
          child: SegmentedButton<bool>(
            segments: const [
              ButtonSegment(value: false, label: Text(UiStrings.estimatedPoints)),
              ButtonSegment(value: true, label: Text(UiStrings.verifiedPoints)),
            ],
            selected: {_showVerified},
            onSelectionChanged: (s) => setState(() => _showVerified = s.first),
          ),
        ),
        const SizedBox(height: 12),
        FlSurfaceCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                _showVerified ? UiStrings.verifiedPoints : UiStrings.estimatedPoints,
                style: TextStyle(fontSize: scale.scale(15), color: AppColors.textMuted),
              ),
              const SizedBox(height: 4),
              Text(
                active.weightedTotal.toStringAsFixed(2),
                style: TextStyle(fontSize: scale.scale(30), fontWeight: FontWeight.w800, color: AppColors.textNavy),
              ),
              const SizedBox(height: 8),
              Text(
                'Raw sum (before KRA weights): ${active.overallRaw.toStringAsFixed(2)}',
                style: TextStyle(fontSize: scale.scale(16), color: AppColors.textMuted),
              ),
            ],
          ),
        ),
        const SizedBox(height: FlLayout.sectionGap),
        FlSectionTitle('3. Your potential rank'),
        FlSurfaceCard(
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: DropdownButtonFormField<String>(
              isExpanded: true,
              value: _targetRank,
              decoration: const InputDecoration(
                labelText: 'Rank you are exploring',
                helperText: 'Compare your points to this rank when rules are set',
              ),
              items: widget.institutionConfig.rankOptions
                  .map((r) => DropdownMenuItem(value: r, child: Text(r, overflow: TextOverflow.ellipsis)))
                  .toList(),
              onChanged: (v) => setState(() => _targetRank = v ?? _targetRank),
            ),
          ),
        ),
        const SizedBox(height: 10),
        FlSurfaceCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                potential,
                style: TextStyle(fontSize: scale.scale(20), fontWeight: FontWeight.w700),
              ),
              if (rulesNote != null) ...[
                const SizedBox(height: 8),
                Text(rulesNote, style: TextStyle(fontSize: scale.scale(16), color: AppColors.textMuted, height: 1.45)),
              ] else if (readiness != null) ...[
                const SizedBox(height: 8),
                Text('Readiness: $readiness', style: TextStyle(fontSize: scale.scale(16), height: 1.4)),
              ],
              const SizedBox(height: 6),
              Text(
                SimulationPresenter.statusLine(eval, widget.institutionConfig),
                style: TextStyle(fontSize: scale.scale(15), color: AppColors.textMuted),
              ),
            ],
          ),
        ),
        const SizedBox(height: FlLayout.sectionGap),
        FlSectionTitle('4. Points by KRA'),
        ...active.kras.map(
          (k) => Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: FlSurfaceCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(_kraShort(k.kraId), style: TextStyle(fontSize: scale.scale(17), fontWeight: FontWeight.w700)),
                  const SizedBox(height: 4),
                  Text(k.name, style: TextStyle(fontSize: scale.scale(15), color: AppColors.textMuted, height: 1.4)),
                  const SizedBox(height: 10),
                  Text(
                    'Raw ${k.rawTotal.toStringAsFixed(2)}${k.rawCap != null ? ' (cap ${k.rawCap})' : ''} · '
                    'Weight ${(k.weight * 100).toStringAsFixed(0)}% · '
                    'Contribution ${k.weightedContribution.toStringAsFixed(2)}',
                    style: TextStyle(fontSize: scale.scale(15), height: 1.45),
                  ),
                ],
              ),
            ),
          ),
        ),
        FlSurfaceCard(
          child: ExpansionTile(
            tilePadding: EdgeInsets.zero,
            title: Text('How are my points calculated?', style: TextStyle(fontSize: scale.scale(17), fontWeight: FontWeight.w600)),
            children: [
              Text(
                'Each KRA has a weight. SET and SEF ratings feed Instruction. '
                'Estimated points are your self-assessment. Reviewer-verified points are checked by your reviewer.',
                style: TextStyle(fontSize: scale.scale(16), height: 1.5, color: AppColors.textMuted),
              ),
            ],
          ),
        ),
        if (est.missingRequirements.isNotEmpty) ...[
          const SizedBox(height: 8),
          FlSectionTitle('Still needed'),
          ...est.missingRequirements.map(
            (m) => Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: FlSurfaceCard(child: ListTile(leading: const Icon(Icons.error_outline), title: Text(m))),
            ),
          ),
        ],
        if (est.pendingEvidence.isNotEmpty) ...[
          FlSectionTitle('Documents in progress'),
          ...est.pendingEvidence.map(
            (p) => Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: FlSurfaceCard(child: ListTile(leading: const Icon(Icons.upload_file), title: Text(p))),
            ),
          ),
        ],
        if (eval.unmetConditions.isNotEmpty && SimulationPresenter.rulesConfigured(widget.institutionConfig)) ...[
          FlSectionTitle('Rules not met yet'),
          ...eval.unmetConditions.map(
            (u) => Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: FlSurfaceCard(child: ListTile(dense: true, title: Text(u))),
            ),
          ),
        ],
        const SizedBox(height: FlLayout.sectionGap),
        FlSectionTitle('5. What you can do next'),
        FlSurfaceCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('• Add or update proof documents.', style: TextStyle(fontSize: scale.scale(16), height: 1.45)),
              Text('• Complete SET and SEF ratings.', style: TextStyle(fontSize: scale.scale(16), height: 1.45)),
              Text('• Try practice points below (does not change saved data).', style: TextStyle(fontSize: scale.scale(16), height: 1.45)),
            ],
          ),
        ),
        const Divider(height: 36),
        Text(UiStrings.whatIfPoints, style: TextStyle(fontWeight: FontWeight.w700, fontSize: scale.scale(18))),
        const SizedBox(height: 6),
        Text(UiStrings.whatIfPointsHelp, style: TextStyle(fontSize: scale.scale(16), height: 1.45, color: AppColors.textMuted)),
        const SizedBox(height: 12),
        FlSurfaceCard(
          child: Column(
            children: [
              TextField(
                controller: _whatIfInstrCtrl,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Extra Instruction raw points (hypothetical)',
                  helperText: 'Added before KRA I 60% weight',
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _whatIfKraCtrl,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Extra weighted KRA II contribution',
                  helperText: 'Added directly to weighted total scenario',
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        Wrap(
          spacing: 10,
          runSpacing: 10,
          children: [
            FilledButton(onPressed: _applyWhatIf, child: const Text('Try a Scenario')),
            OutlinedButton(onPressed: _resetScenario, child: const Text('Reset Scenario')),
          ],
        ),
        if (_whatIf != WhatIfScenario.empty)
          Padding(
            padding: const EdgeInsets.only(top: 10),
            child: Text(
              'Scenario active — values differ from your saved assessment.',
              style: TextStyle(fontSize: scale.scale(15), color: AppColors.success, fontWeight: FontWeight.w600),
            ),
          ),
        const SizedBox(height: 24),
      ],
    );

    if (widget.embedInTab) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          FlPageHeader(
            title: 'Rank simulation',
            subtitle: 'Practice your points and explore the next rank.',
          ),
          Expanded(child: body),
        ],
      );
    }
    return Scaffold(appBar: AppBar(title: const Text('Rank simulation')), body: body);
  }
}
