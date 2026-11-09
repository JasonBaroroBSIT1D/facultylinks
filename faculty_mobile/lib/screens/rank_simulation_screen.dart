import 'package:flutter/material.dart';

import '../core/simulation_presenter.dart';
import '../core/ui_strings.dart';
import '../data/assessment_catalog.dart';
import '../models/institution_config.dart';
import '../models/rank_simulation.dart';
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
  final Future<void> Function()? onRefresh;

  const RankSimulationScreen({
    super.key,
    required this.repo,
    required this.institutionConfig,
    this.initialWhatIf = WhatIfScenario.empty,
    this.onWhatIfChanged,
    this.embedInTab = false,
    this.onRefresh,
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

  String _criterionBreakdownLabel(CriterionBreakdownLine c) {
    final fromCatalog = assessmentKras
        .expand((k) => k.criteria)
        .where((cr) => cr.id == c.criterionId)
        .map((cr) => cr.name)
        .firstOrNull;
    final label = c.name ?? fromCatalog ?? c.criterionId;
    final cap = c.capMaxPoints;
    if (cap != null) {
      return '$label: ${c.rawTotal.toStringAsFixed(2)} / ${cap.toStringAsFixed(0)} pts';
    }
    return '$label: ${c.rawTotal.toStringAsFixed(2)} pts';
  }

  @override
  Widget build(BuildContext context) {
    final est = SimulationEngine.compute(widget.repo, whatIf: _whatIf);
    final ver = SimulationEngine.compute(widget.repo, verified: true, whatIf: _whatIf);
    final active = _showVerified ? ver : est;
    final eval = active.usesRankTableWeights
        ? SimulationEngine.evaluateFromSnapshot(active)
        : SimulationEngine.evaluateTarget(
            cfg: widget.institutionConfig,
            targetRank: _targetRank,
            weightedTotal: active.weightedTotal,
            scoringAuthoritative: active.scoringAuthoritative,
          );
    final usesRankTable = active.usesRankTableWeights;
    final rankSimJson = widget.repo.rankSimulationJson;
    final rankBucket = rankSimJson != null
        ? (_showVerified
            ? FacultyRankSimulation.fromJson(rankSimJson).verified
            : FacultyRankSimulation.fromJson(rankSimJson).estimated)
        : RankSimulationBucket(configured: false, scoreSource: 'estimated');
    final displayCurrent = active.bucketCurrentRank ?? widget.repo.profile.rank;
    final subRankInc = active.subRankBracket?.subRankIncrements ?? active.subRankBracket?.provisionalIncrements;
    final potential = SimulationPresenter.potentialRankLabel(
      eval,
      widget.institutionConfig,
      usesRankTable: usesRankTable,
    );
    final rulesNote = usesRankTable ? null : SimulationPresenter.rankRulesNotice(widget.institutionConfig);
    final readiness = usesRankTable ? null : SimulationPresenter.readinessLine(eval, widget.institutionConfig);
    final decimalPolicyConditional = usesRankTable && _decimalPolicyConditional(active);
    final scale = MediaQuery.textScalerOf(context);

    final bottomInset = MediaQuery.paddingOf(context).bottom;
    final listPadding = const EdgeInsets.fromLTRB(18, 4, 18, 16).copyWith(bottom: 16 + bottomInset);

    final scrollable = ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: listPadding,
      children: [
        if (!widget.embedInTab)
          const FlPageHeader(
            title: 'Rank simulation',
            subtitle: 'Explore your possible next rank.',
          ),
        FlSurfaceCard(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          child: _currentRankRow(scale, displayCurrent),
        ),
        const SizedBox(height: FlLayout.sectionGap),
        Semantics(
          label: 'Choose estimated or reviewer verified points',
          child: _buildScoreModeSelector(scale),
        ),
        const SizedBox(height: FlLayout.sectionGap),
        if (usesRankTable) ...[
          FlSurfaceCard(
            child: _buildMainResultCard(
              scale: scale,
              weightedScore: active.weightedTotal,
              showCenturyScale: true,
              rankTitle: decimalPolicyConditional ? 'Conditional potential rank' : 'Potential rank',
              destination: potential,
              fromRank: displayCurrent,
              subRankIncrements: subRankInc,
              qualification: _visibleQualification(active, decimalPolicyConditional),
            ),
          ),
          const SizedBox(height: FlLayout.sectionGap),
          FlSurfaceCard(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
            child: Theme(
              data: Theme.of(context).copyWith(dividerColor: AppColors.border),
              child: ExpansionTile(
                tilePadding: const EdgeInsets.symmetric(horizontal: 4),
                childrenPadding: const EdgeInsets.fromLTRB(4, 0, 4, 12),
                collapsedShape: const RoundedRectangleBorder(side: BorderSide.none),
                shape: const RoundedRectangleBorder(side: BorderSide.none),
                title: Text(
                  'View calculation',
                  style: TextStyle(fontSize: scale.scale(16), fontWeight: FontWeight.w600, color: AppColors.textMain),
                ),
                children: _viewCalculationChildren(
                  scale: scale,
                  active: active,
                  rankBucket: rankBucket,
                  eval: eval,
                ),
              ),
            ),
          ),
        ] else ...[
          FlSectionTitle('Potential rank'),
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
                  SimulationPresenter.statusLine(eval, widget.institutionConfig, usesRankTable: false),
                  style: TextStyle(fontSize: scale.scale(15), color: AppColors.textMuted),
                ),
              ],
            ),
          ),
          const SizedBox(height: FlLayout.sectionGap),
          FlSectionTitle('KRA breakdown'),
          ..._kraBreakdownCards(active, scale),
          FlSurfaceCard(
            child: ExpansionTile(
              tilePadding: EdgeInsets.zero,
              title: Text('Calculation details', style: TextStyle(fontSize: scale.scale(16), fontWeight: FontWeight.w600)),
              children: [
                Text(
                  'Promotion score = sum of (capped KRA raw × current-rank weight). '
                  'Raw KRA sum ${active.overallRaw.toStringAsFixed(2)} is not the promotion score.',
                  style: TextStyle(fontSize: scale.scale(15), height: 1.45, color: AppColors.textMuted),
                ),
              ],
            ),
          ),
        ],
        if (est.missingRequirements.isNotEmpty) ...[
          const SizedBox(height: FlLayout.sectionGap),
          FlHomeSectionLabel('Still needed'),
          FlSurfaceCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: est.missingRequirements
                  .map(
                    (m) => Padding(
                      padding: const EdgeInsets.only(bottom: 6),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Icon(Icons.info_outline, size: 18, color: AppColors.amberText),
                          const SizedBox(width: 8),
                          Expanded(child: Text(m, style: TextStyle(fontSize: scale.scale(14), height: 1.4))),
                        ],
                      ),
                    ),
                  )
                  .toList(),
            ),
          ),
        ],
        if (est.pendingEvidence.isNotEmpty) ...[
          const SizedBox(height: FlLayout.sectionGap),
          FlHomeSectionLabel('Documents in progress'),
          FlSurfaceCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: est.pendingEvidence
                  .map(
                    (p) => Padding(
                      padding: const EdgeInsets.only(bottom: 6),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Icon(Icons.upload_file, size: 18, color: AppColors.primaryBlue),
                          const SizedBox(width: 8),
                          Expanded(child: Text(p, style: TextStyle(fontSize: scale.scale(14), height: 1.4))),
                        ],
                      ),
                    ),
                  )
                  .toList(),
            ),
          ),
        ],
        if (!usesRankTable &&
            eval.unmetConditions.isNotEmpty &&
            SimulationPresenter.rulesConfigured(widget.institutionConfig)) ...[
          FlSectionTitle('Rules not met yet'),
          ...eval.unmetConditions.map(
            (u) => Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: FlSurfaceCard(child: ListTile(dense: true, title: Text(u))),
            ),
          ),
        ],
        if (!usesRankTable) ...[
          const SizedBox(height: FlLayout.sectionGap),
          FlHomeSectionLabel('Next steps'),
          FlSurfaceCard(
            child: Text(
              'Add proof documents, complete SET/SEF ratings, or try a practice scenario below.',
              style: TextStyle(fontSize: scale.scale(15), height: 1.45, color: AppColors.textMuted),
            ),
          ),
        ],
        const SizedBox(height: FlLayout.sectionGap),
        FlHomeSectionLabel(UiStrings.whatIfPoints),
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
        const SizedBox(height: FlLayout.sectionGap),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 4),
          child: Text(
            'For preparation only. Official decisions remain with authorized committees.',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: scale.scale(13), height: 1.45, color: AppColors.textMuted),
          ),
        ),
        const SizedBox(height: 12),
      ],
    );

    final body = widget.onRefresh == null
        ? scrollable
        : RefreshIndicator(
            color: AppColors.primaryBlue,
            onRefresh: widget.onRefresh!,
            child: scrollable,
          );

    if (widget.embedInTab) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          FlPageHeader(
            title: 'Rank simulation',
            subtitle: 'Explore your possible next rank.',
          ),
          Expanded(child: body),
        ],
      );
    }
    return Scaffold(appBar: AppBar(title: const Text('Rank simulation')), body: body);
  }

  bool _decimalPolicyConditional(SimulationSnapshot active) {
    final b = active.subRankBracket;
    if (b == null) return false;
    return b.status == 'conditional' ||
        (b.subRankIncrements == null && b.provisionalIncrements != null);
  }

  String _visibleQualification(SimulationSnapshot active, bool decimalPolicyConditional) {
    if (decimalPolicyConditional) {
      return 'Subject to confirmation of the scoring policy.';
    }
    if (!active.scoringAuthoritative) {
      return 'Provisional scoring — not confirmed.';
    }
    final pr = active.potentialRank;
    if (pr?.status == 'eligibility_required') {
      return 'Eligibility subject to verification.';
    }
    if (pr?.displayLabel != null && pr!.displayLabel!.isNotEmpty) {
      return pr.displayLabel!;
    }
    return 'Preparation only — not an official promotion decision.';
  }

  Widget _currentRankRow(TextScaler scale, String rank) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(Icons.school_outlined, size: scale.scale(22), color: AppColors.primaryBlue),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Current rank',
                style: TextStyle(fontSize: scale.scale(13), color: AppColors.textMuted, fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 2),
              Text(
                rank,
                style: TextStyle(fontSize: scale.scale(18), fontWeight: FontWeight.w700, color: AppColors.textMain, height: 1.3),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildScoreModeSelector(TextScaler scale) {
    Widget option({required bool selected, required String label, required VoidCallback onTap}) {
      return Material(
        color: selected ? AppColors.primarySoft : AppColors.cardWhite,
        borderRadius: BorderRadius.circular(12),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(12),
          child: Container(
            constraints: const BoxConstraints(minHeight: 48),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: selected ? AppColors.primaryBlue : AppColors.border, width: selected ? 1.5 : 1),
            ),
            alignment: Alignment.center,
            child: Text(
              label,
              textAlign: TextAlign.center,
              softWrap: true,
              style: TextStyle(
                fontSize: scale.scale(14),
                fontWeight: selected ? FontWeight.w700 : FontWeight.w600,
                color: selected ? AppColors.primaryBlue : AppColors.textMain,
                height: 1.25,
              ),
            ),
          ),
        ),
      );
    }

    return LayoutBuilder(
      builder: (context, constraints) {
        final narrow = constraints.maxWidth < 360;
        if (narrow) {
          return Column(
            children: [
              option(
                selected: !_showVerified,
                label: UiStrings.estimatedPoints,
                onTap: () => setState(() => _showVerified = false),
              ),
              const SizedBox(height: 8),
              option(
                selected: _showVerified,
                label: UiStrings.verifiedPoints,
                onTap: () => setState(() => _showVerified = true),
              ),
            ],
          );
        }
        return Row(
          children: [
            Expanded(
              child: option(
                selected: !_showVerified,
                label: UiStrings.estimatedPoints,
                onTap: () => setState(() => _showVerified = false),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: option(
                selected: _showVerified,
                label: UiStrings.verifiedPoints,
                onTap: () => setState(() => _showVerified = true),
              ),
            ),
          ],
        );
      },
    );
  }

  Widget _buildMainResultCard({
    required TextScaler scale,
    required double weightedScore,
    required bool showCenturyScale,
    required String rankTitle,
    required String destination,
    required String fromRank,
    required int? subRankIncrements,
    required String qualification,
  }) {
    final incPhrase = subRankIncrements != null
        ? '$subRankIncrements sub-rank increment${subRankIncPlural(subRankIncrements)}'
        : 'sub-rank increment pending';
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Overall weighted score',
          style: TextStyle(fontSize: scale.scale(13), color: AppColors.textMuted, fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 6),
        Wrap(
          crossAxisAlignment: WrapCrossAlignment.center,
          spacing: 4,
          children: [
            Text(
              weightedScore.toStringAsFixed(2),
              style: TextStyle(fontSize: scale.scale(32), fontWeight: FontWeight.w800, color: AppColors.textNavy, height: 1.1),
            ),
            if (showCenturyScale)
              Text(
                '/ 100',
                style: TextStyle(fontSize: scale.scale(18), fontWeight: FontWeight.w600, color: AppColors.textMuted),
              ),
          ],
        ),
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 16),
          child: Divider(height: 1, color: AppColors.border),
        ),
        Text(
          rankTitle,
          style: TextStyle(fontSize: scale.scale(13), color: AppColors.textMuted, fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 6),
        Text(
          destination,
          style: TextStyle(fontSize: scale.scale(24), fontWeight: FontWeight.w800, color: AppColors.textNavy, height: 1.2),
        ),
        const SizedBox(height: 8),
        Text(
          'From $fromRank · $incPhrase',
          style: TextStyle(fontSize: scale.scale(15), height: 1.4, color: AppColors.textMain),
        ),
        const SizedBox(height: 10),
        Text(
          qualification,
          style: TextStyle(fontSize: scale.scale(13), color: AppColors.amberText, height: 1.4),
        ),
      ],
    );
  }

  String subRankIncPlural(int n) => n == 1 ? '' : 's';

  List<Widget> _viewCalculationChildren({
    required TextScaler scale,
    required SimulationSnapshot active,
    required RankSimulationBucket rankBucket,
    required RankEvaluation eval,
  }) {
    final bracket = active.subRankBracket;
    final muted = TextStyle(fontSize: scale.scale(15), height: 1.45, color: AppColors.textMuted);
    final sectionTitle = TextStyle(fontSize: scale.scale(15), fontWeight: FontWeight.w700);

    return [
      if (active.rankCategoryLabel != null) ...[
        Text('Weight category (Table 2.2)', style: sectionTitle),
        const SizedBox(height: 6),
        Text(active.rankCategoryLabel!, style: muted),
        const SizedBox(height: 14),
      ],
      Text('Score bracket (Table 3.1)', style: sectionTitle),
      const SizedBox(height: 6),
      if (bracket != null) ...[
        Text(bracket.label ?? '—', style: muted),
        if (bracket.unresolvedReason != null) ...[
          const SizedBox(height: 6),
          Text('Decimal policy: ${bracket.unresolvedReason}', style: muted),
        ],
      ] else
        Text('No bracket resolved for this score.', style: muted),
      const SizedBox(height: 14),
      Text('KRA weights and contributions', style: sectionTitle),
      const SizedBox(height: 8),
      ..._kraBreakdownCards(active, scale, compact: true),
      const SizedBox(height: 8),
      Text(
        'Promotion score = sum of (capped KRA raw × current-rank weight). '
        'Raw KRA sum ${active.overallRaw.toStringAsFixed(2)} is not the promotion score.',
        style: muted,
      ),
      if (rankBucket.conditionalRankProjections.isNotEmpty) ...[
        const SizedBox(height: 14),
        Text('Conditional projections', style: sectionTitle),
        const SizedBox(height: 6),
        ...rankBucket.conditionalRankProjections.map(
          (c) => Padding(
            padding: const EdgeInsets.only(bottom: 6),
            child: Text(
              '${c.policyLabel ?? c.policyKey}: ${c.potentialRank?.potentialRank ?? '—'} '
              '(+${c.subRankIncrements ?? '—'} sub-rank(s), ${c.bracketLabel ?? ''})',
              style: muted,
            ),
          ),
        ),
      ],
      if (eval.unmetConditions.isNotEmpty) ...[
        const SizedBox(height: 14),
        Text('Eligibility and policy notes', style: sectionTitle),
        const SizedBox(height: 6),
        ...eval.unmetConditions.map((u) => Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: Text(u, style: muted),
            )),
      ],
    ];
  }

  List<Widget> _kraBreakdownCards(SimulationSnapshot active, TextScaler scale, {bool compact = false}) {
    return active.kras.map(
      (k) => Padding(
        padding: EdgeInsets.only(bottom: compact ? 8 : 10),
        child: compact
            ? Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    _kraShort(k.kraId),
                    style: TextStyle(fontSize: scale.scale(15), fontWeight: FontWeight.w600),
                  ),
                  Text(
                    'Raw ${k.rawTotal.toStringAsFixed(2)} · '
                    'Weight ${(k.weight * 100).toStringAsFixed(0)}% · '
                    'Contribution ${k.weightedContribution.toStringAsFixed(2)}',
                    style: TextStyle(fontSize: scale.scale(14), height: 1.45, color: AppColors.textMuted),
                  ),
                  if (k.rawIncomplete)
                    Text(
                      'Criterion A incomplete — ${k.incompleteReason ?? 'verify SET/SEF semester ratings.'}',
                      style: TextStyle(fontSize: scale.scale(14), color: AppColors.amberText),
                    ),
                ],
              )
            : FlSurfaceCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(_kraShort(k.kraId), style: TextStyle(fontSize: scale.scale(17), fontWeight: FontWeight.w700)),
                    const SizedBox(height: 4),
                    Text(k.name, style: TextStyle(fontSize: scale.scale(15), color: AppColors.textMuted, height: 1.4)),
                    const SizedBox(height: 10),
                    if (k.rawIncomplete) ...[
                      Text(
                        'Criterion A incomplete — ${k.incompleteReason ?? 'verify SET/SEF semester ratings.'}',
                        style: TextStyle(fontSize: scale.scale(15), height: 1.45, color: AppColors.amberText),
                      ),
                      const SizedBox(height: 6),
                    ],
                    Text(
                      'Raw ${k.rawTotal.toStringAsFixed(2)} · '
                      'Weight ${(k.weight * 100).toStringAsFixed(0)}% · '
                      'Contribution ${k.weightedContribution.toStringAsFixed(2)}',
                      style: TextStyle(fontSize: scale.scale(15), height: 1.45),
                    ),
                    if (k.criteria.isNotEmpty) ...[
                      const SizedBox(height: 8),
                      ...k.criteria.map(
                        (c) => Padding(
                          padding: const EdgeInsets.only(top: 4),
                          child: Text(
                            _criterionBreakdownLabel(c),
                            style: TextStyle(fontSize: scale.scale(14), height: 1.4, color: AppColors.textMuted),
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
      ),
    ).toList();
  }
}
