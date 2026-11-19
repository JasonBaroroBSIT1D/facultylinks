import 'package:flutter/material.dart';

import '../../core/scoring.dart';
import '../../core/ui_strings.dart';
import '../../data/assessment_catalog.dart';
import '../../models/institution_config.dart';
import '../../repositories/mock_repository.dart';
import '../../services/achievement_api.dart';
import '../../services/assessment_overview_model.dart';
import '../../services/faculty_refresh.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_theme.dart';
import '../../widgets/assessment_criterion_tile.dart';
import '../../widgets/assessment_indicator_row.dart';
import '../../widgets/assessment_summary_section.dart';
import '../document_detail_screen.dart';
import '../indicator_entries_screen.dart';
import '../kra_i_achievement_screen.dart';
import '../set_sef_screen.dart';
import '../upload_evidence_screen.dart';

/// Unified My Assessment screen — scores, rank outlook, KRA breakdown, and attention.
///
/// - [selectedKraId] `null` → full overview (all KRAs).
/// - [selectedKraId] `kra-I`…`kra-IV` → that KRA’s details (from Home area cards).
/// - [embedInTab] → shell Assessment tab (no back AppBar).
class AssessmentTab extends StatefulWidget {
  final MockRepository repo;
  final Future<void> Function() onSave;
  final String? selectedKraId;
  final InstitutionConfig? institutionConfig;
  final bool embedInTab;

  const AssessmentTab({
    super.key,
    required this.repo,
    required this.onSave,
    this.selectedKraId,
    this.institutionConfig,
    this.embedInTab = false,
  });

  static String titleForKraId(String? kraId) {
    switch (kraId) {
      case 'kra-I':
        return 'KRA I — Instruction';
      case 'kra-II':
        return 'KRA II — Research';
      case 'kra-III':
        return 'KRA III — Extension';
      case 'kra-IV':
        return 'KRA IV — Professional Development';
      default:
        return 'My Assessment';
    }
  }

  @override
  State<AssessmentTab> createState() => _AssessmentTabState();
}

class _AssessmentTabState extends State<AssessmentTab> {
  bool _navigating = false;
  bool _loadingAchievements = true;
  String? _achievementsError;
  List<Map<String, dynamic>> _achievements = const [];
  final Set<String> _keepExpandedCriterionIds = {};
  final Set<String> _expandedKraIds = {};
  bool _showVerified = false;

  bool get _isScoped => widget.selectedKraId != null && widget.selectedKraId!.isNotEmpty;

  InstitutionConfig get _cfg => widget.institutionConfig ?? InstitutionConfig.defaults();

  @override
  void initState() {
    super.initState();
    if (_isScoped) _expandedKraIds.add(widget.selectedKraId!);
    _loadAchievements();
  }

  Future<void> _loadAchievements() async {
    setState(() {
      _loadingAchievements = true;
      _achievementsError = null;
    });
    try {
      final list = await AchievementApi.list();
      if (!mounted) return;
      setState(() {
        _achievements = list;
        _loadingAchievements = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _achievementsError = e.toString().replaceFirst('Exception: ', '');
        _loadingAchievements = false;
      });
    }
  }

  Future<void> _refreshAll() async {
    final coordinator = FacultySession.active;
    if (coordinator != null) {
      await coordinator.refresh(
        scopes: {
          FacultyRefreshScope.scores,
          FacultyRefreshScope.documents,
          FacultyRefreshScope.assessment,
          FacultyRefreshScope.catalog,
        },
        force: true,
      );
    } else {
      await widget.onSave();
    }
    await _loadAchievements();
  }

  AssessmentOverviewModel get _model => AssessmentOverviewModel.fromRepo(
        widget.repo,
        achievements: _achievements,
        achievementsError: _achievementsError,
        achievementsLoading: _loadingAchievements,
      );

  List<KraNode> _visibleKras() {
    final all = widget.repo.catalogKras;
    if (!_isScoped) return all;
    return all.where((k) => k.id == widget.selectedKraId).toList();
  }

  Future<void> _pushRoute(Widget page, {String? keepExpandedCriterionId}) async {
    if (_navigating || !mounted) return;
    setState(() {
      _navigating = true;
      if (keepExpandedCriterionId != null) {
        _keepExpandedCriterionIds.add(keepExpandedCriterionId);
      }
    });
    try {
      await Navigator.push(context, MaterialPageRoute(builder: (_) => page));
      await widget.onSave();
      await _loadAchievements();
    } finally {
      if (mounted) setState(() => _navigating = false);
    }
  }

  Future<void> _openIndicator(KraNode kra, CriterionNode c, IndicatorNode ind) async {
    final wantsAch = isAchievementCriterion(kra.id, c.id);
    final isAch = widget.repo.catalogLoadedFromApi && wantsAch;
    if (wantsAch && !widget.repo.catalogLoadedFromApi) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Self-assessment achievements require the published catalog to be loaded.',
          ),
        ),
      );
      return;
    }
    final page = isAch
        ? KraIAchievementScreen(
            repo: widget.repo,
            kraId: kra.id,
            criterion: c,
            indicator: ind,
            onSave: widget.onSave,
          )
        : IndicatorEntriesScreen(
            repo: widget.repo,
            kraId: kra.id,
            criterionId: c.id,
            indicator: ind,
            onSave: widget.onSave,
          );
    await _pushRoute(page, keepExpandedCriterionId: c.id);
  }

  Future<void> _openAttention(AssessmentAttentionItem item) async {
    if (item.documentId != null) {
      final doc = widget.repo.documentById(item.documentId!);
      if (doc != null) {
        await _pushRoute(
          DocumentDetailScreen(doc: doc, repo: widget.repo, onRefresh: widget.onSave),
          keepExpandedCriterionId: item.criterionId,
        );
        return;
      }
    }
    if (item.indicatorId != null) {
      final kraId = item.kraId ??
          tryKraIdFromIndicator(item.indicatorId!, criterionId: item.criterionId);
      final kra = widget.repo.catalogKras.where((k) => k.id == kraId).firstOrNull;
      final crit = kra?.criteria.where((c) => c.id == item.criterionId).firstOrNull ??
          kra?.criteria.where((c) => c.indicators.any((i) => i.id == item.indicatorId)).firstOrNull;
      final ind = crit?.indicators.where((i) => i.id == item.indicatorId).firstOrNull;
      if (kra != null && crit != null && ind != null) {
        await _openIndicator(kra, crit, ind);
        return;
      }
    }
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('This item could not be opened. Pull to refresh and try again.')),
    );
  }

  @override
  Widget build(BuildContext context) {
    final model = _model;
    final scale = MediaQuery.textScalerOf(context);
    final kras = _visibleKras();
    final useVerifiedLine = _showVerified;
    final bottomInset = MediaQuery.paddingOf(context).bottom;

    final scrollable = RefreshIndicator(
      color: AppColors.primaryBlue,
      onRefresh: _refreshAll,
      child: SingleChildScrollView(
        key: PageStorageKey<String>(
          'assessment_tab_${widget.selectedKraId ?? 'all'}_${widget.embedInTab ? 'tab' : 'push'}',
        ),
        physics: const AlwaysScrollableScrollPhysics(),
        padding: EdgeInsets.fromLTRB(16, 4, 16, 88 + bottomInset),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (!_isScoped) ...[
              AssessmentSummarySection(
                model: model,
                institutionConfig: _cfg,
                currentProfileRank: widget.repo.profile.rank,
                showVerified: _showVerified,
                onShowVerifiedChanged: (v) => setState(() => _showVerified = v),
                scale: scale,
              ),
              const SizedBox(height: FlLayout.sectionGap),
              FlHomeSectionLabel('Needs attention'),
              _AttentionSection(
                items: model.attentionItems(widget.repo),
                scale: scale,
                onOpen: _openAttention,
              ),
              const SizedBox(height: FlLayout.sectionGap),
              FlHomeSectionLabel('KRA breakdown'),
              if (model.scoresWeighted)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Text(
                    'Each card shows this KRA’s contribution for the selected score mode. '
                    'Weights are applied once in the overall score above.',
                    style: TextStyle(fontSize: scale.scale(13), color: AppColors.textMuted, height: 1.4),
                  ),
                ),
            ] else ...[
              Text(
                'Criteria and indicators for this assessment area.',
                style: TextStyle(fontSize: scale.scale(15), color: AppColors.textMuted, height: 1.4),
              ),
              const SizedBox(height: 12),
            ],
            if (model.achievementsLoading)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 12),
                child: LinearProgressIndicator(minHeight: 3),
              ),
            if (model.achievementsError != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: FlSurfaceCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Could not load achievements.',
                        style: TextStyle(fontSize: scale.scale(15), fontWeight: FontWeight.w600),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        model.achievementsError!,
                        style: TextStyle(fontSize: scale.scale(14), color: AppColors.textMuted),
                      ),
                      TextButton(onPressed: _loadAchievements, child: const Text('Retry')),
                    ],
                  ),
                ),
              ),
            ...kras.map((kra) => _buildKraSection(kra, model, scale, useVerifiedLine)),
            if (!_isScoped) ...[
              const SizedBox(height: FlLayout.sectionGap),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 4),
                child: Text(
                  UiStrings.simDisclaimer,
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: scale.scale(13), height: 1.45, color: AppColors.textMuted),
                ),
              ),
            ],
            const SizedBox(height: 12),
          ],
        ),
      ),
    );

    if (widget.embedInTab) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const FlPageHeader(
            title: 'My Assessment',
            subtitle: 'Scores, rank outlook, and requirements that need attention.',
          ),
          Expanded(child: scrollable),
        ],
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: Text(AssessmentTab.titleForKraId(widget.selectedKraId)),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          tooltip: 'Back',
          onPressed: () => Navigator.maybePop(context),
        ),
      ),
      body: scrollable,
    );
  }

  Widget _buildKraSection(
    KraNode kra,
    AssessmentOverviewModel model,
    TextScaler scale,
    bool useVerifiedLine,
  ) {
    final expanded = _isScoped || _expandedKraIds.contains(kra.id);
    final line = (useVerifiedLine && model.verifiedAvailable)
        ? model.kraLine(kra.id, verified: true)
        : model.kraLine(kra.id, verified: false);
    final title = AssessmentOverviewModel.kraTitle(kra.id);
    final modeLabel = useVerifiedLine ? 'Verified' : 'Estimated';

    String? contributionText;
    if (useVerifiedLine && !model.verifiedAvailable) {
      contributionText = 'Not yet verified';
    } else if (line != null) {
      if (model.scoresWeighted) {
        contributionText =
            '$modeLabel · ${line.weightedContribution.toStringAsFixed(2)} weighted pts'
            ' · raw ${line.rawTotal.toStringAsFixed(2)}'
            ' · ${(line.weight * 100).toStringAsFixed(0)}% weight';
      } else {
        contributionText = '$modeLabel · ${line.rawTotal.toStringAsFixed(2)} raw pts';
      }
    }

    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: AppColors.cardWhite,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: AppColors.border),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Material(
              color: Colors.transparent,
              child: InkWell(
                key: ValueKey('kra-expand-${kra.id}'),
                borderRadius: BorderRadius.circular(14),
                onTap: _isScoped
                    ? null
                    : () => setState(() {
                          if (expanded) {
                            _expandedKraIds.remove(kra.id);
                          } else {
                            _expandedKraIds.add(kra.id);
                          }
                        }),
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(14, 12, 10, 12),
                  child: Row(
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              title,
                              style: TextStyle(
                                fontSize: scale.scale(16),
                                fontWeight: FontWeight.w700,
                                color: AppColors.textMain,
                              ),
                            ),
                            if (contributionText != null) ...[
                              const SizedBox(height: 4),
                              Text(
                                contributionText,
                                style: TextStyle(fontSize: scale.scale(13), color: AppColors.textMuted, height: 1.35),
                              ),
                            ],
                            if (line?.rawIncomplete == true &&
                                (line!.incompleteReason?.trim().isNotEmpty ?? false)) ...[
                              const SizedBox(height: 4),
                              Text(
                                line.incompleteReason!.trim(),
                                style: TextStyle(fontSize: scale.scale(12), color: AppColors.amberText, height: 1.35),
                              ),
                            ],
                          ],
                        ),
                      ),
                      if (!_isScoped)
                        Icon(
                          expanded ? Icons.keyboard_arrow_up : Icons.keyboard_arrow_down,
                          color: AppColors.primaryBlue,
                        ),
                    ],
                  ),
                ),
              ),
            ),
            if (expanded) ...[
              const Divider(height: 1, color: AppColors.border),
              Padding(
                padding: const EdgeInsets.fromLTRB(8, 8, 8, 10),
                child: Column(
                  children: kra.criteria.map((c) => _criterionBlock(kra, c, model)).toList(),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _criterionBlock(KraNode kra, CriterionNode c, AssessmentOverviewModel model) {
    final isCriterionA = kra.id == 'kra-I' && c.id == 'kra-I-A';
    final children = isCriterionA
        ? _criterionAChildren()
        : _indicatorChildren(kra, c, model);
    return AssessmentCriterionTile(
      kraId: kra.id,
      criterionId: c.id,
      title: c.name,
      initiallyExpanded: _keepExpandedCriterionIds.contains(c.id),
      children: children,
    );
  }

  List<Widget> _criterionAChildren() {
    final caEst = widget.repo.criterionAEstimatedLine();
    final caVer = widget.repo.criterionAVerifiedLine();
    final set = computeSetSef(widget.repo.setRatings, 'SET');
    final sef = computeSetSef(widget.repo.sefRatings, 'SEF');
    final summary = (caEst.isNotEmpty || caVer.isNotEmpty)
        ? [if (caEst.isNotEmpty) caEst, if (caVer.isNotEmpty) caVer].join('\n')
        : 'Combined raw ${(set.raw + sef.raw).toStringAsFixed(2)} / 60 max';

    return [
      AssessmentIndicatorRow(
        icon: Icons.school_outlined,
        title: 'SET & SEF',
        supportingText: summary,
        showDividerBelow: true,
        onTap: () => _pushRoute(
          SetSefScreen(repo: widget.repo, onSave: widget.onSave),
          keepExpandedCriterionId: 'kra-I-A',
        ),
      ),
      AssessmentIndicatorRow(
        icon: Icons.upload_file,
        title: 'Upload SET / SEF evaluation',
        supportingText: 'Choose a file or scan your printed evaluation',
        onTap: () => _pushRoute(
          UploadEvidenceScreen(
            repo: widget.repo,
            onSave: widget.onSave,
            initialKraId: 'kra-I',
            initialCriterionId: 'kra-I-A',
          ),
          keepExpandedCriterionId: 'kra-I-A',
        ),
      ),
    ];
  }

  List<Widget> _indicatorChildren(KraNode kra, CriterionNode c, AssessmentOverviewModel model) {
    final indicators = scoringIndicatorsForCriterion(c)
        .where((i) => i.type != 'set_sef')
        .where((i) => i.id != criterionASpecialIndicatorId)
        .toList();
    final wantsAch = isAchievementCriterion(kra.id, c.id);
    final out = <Widget>[];

    for (var i = 0; i < indicators.length; i++) {
      final ind = indicators[i];
      final achs = model.achievementsForIndicator(ind.id);
      out.add(
        AssessmentIndicatorRow.forIndicator(
          key: ValueKey('indicator-${kra.id}-${ind.id}'),
          indicator: ind,
          kraId: kra.id,
          showDividerBelow: true,
          onTap: () => _openIndicator(kra, c, ind),
        ),
      );
      if (achs.isEmpty) {
        out.add(
          Padding(
            padding: const EdgeInsets.fromLTRB(14, 0, 14, 8),
            child: Text(
              'No achievements added yet.',
              style: TextStyle(fontSize: 13, color: AppColors.textMuted, height: 1.35),
            ),
          ),
        );
      } else {
        for (final a in achs) {
          out.add(_AchievementMiniRow(
            achievement: a,
            onTap: () => _openIndicator(kra, c, ind),
          ));
        }
      }
      if (wantsAch && widget.repo.catalogLoadedFromApi) {
        out.add(
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 0, 12, 10),
            child: Align(
              alignment: Alignment.centerLeft,
              child: TextButton.icon(
                onPressed: _navigating
                    ? null
                    : () => _pushRoute(
                          KraIAchievementScreen(
                            repo: widget.repo,
                            kraId: kra.id,
                            criterion: c,
                            indicator: ind,
                            onSave: widget.onSave,
                          ),
                          keepExpandedCriterionId: c.id,
                        ),
                icon: const Icon(Icons.add, size: 18),
                label: const Text('Add achievement'),
              ),
            ),
          ),
        );
      }
      if (i < indicators.length - 1) {
        out.add(const Padding(
          padding: EdgeInsets.symmetric(horizontal: 12),
          child: Divider(height: 1, color: AppColors.border),
        ));
      }
    }
    return out;
  }
}

class _AttentionSection extends StatelessWidget {
  final List<AssessmentAttentionItem> items;
  final TextScaler scale;
  final Future<void> Function(AssessmentAttentionItem item) onOpen;

  const _AttentionSection({
    required this.items,
    required this.scale,
    required this.onOpen,
  });

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) {
      return FlSurfaceCard(
        child: Text(
          'Nothing needs your attention right now.',
          style: TextStyle(fontSize: scale.scale(15), color: AppColors.textMuted, height: 1.4),
        ),
      );
    }
    return Column(
      children: items.map((item) {
        final icon = switch (item.kind) {
          AssessmentAttentionKind.needsChanges => Icons.edit_note_outlined,
          AssessmentAttentionKind.pendingReview => Icons.hourglass_top_outlined,
          AssessmentAttentionKind.processingFailed => Icons.error_outline,
          AssessmentAttentionKind.incompleteRequirement => Icons.info_outline,
        };
        final color = switch (item.kind) {
          AssessmentAttentionKind.needsChanges => AppColors.amberText,
          AssessmentAttentionKind.pendingReview => AppColors.primaryBlue,
          AssessmentAttentionKind.processingFailed => AppColors.redText,
          AssessmentAttentionKind.incompleteRequirement => AppColors.amberText,
        };
        return Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: FlSurfaceCard(
            onTap: () => onOpen(item),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(icon, color: color, size: 22),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(item.title, style: TextStyle(fontSize: scale.scale(14), fontWeight: FontWeight.w700)),
                      const SizedBox(height: 2),
                      Text(item.detail, style: TextStyle(fontSize: scale.scale(13), color: AppColors.textMuted, height: 1.35)),
                    ],
                  ),
                ),
                const Icon(Icons.chevron_right, color: AppColors.textMuted),
              ],
            ),
          ),
        );
      }).toList(),
    );
  }
}

class _AchievementMiniRow extends StatelessWidget {
  final Map<String, dynamic> achievement;
  final VoidCallback onTap;

  const _AchievementMiniRow({required this.achievement, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final scale = MediaQuery.textScalerOf(context);
    final title = achievement['title']?.toString() ?? 'Untitled';
    final status = achievementStatusLabel(achievement);
    final claimed = achievement['claimedPoints'];
    final verified = achievement['reviewerVerifiedPoints'];
    final remarks = achievement['reviewRemarks']?.toString().trim();
    final scoreBits = <String>[
      if (claimed != null) 'Claimed $claimed',
      if (verified != null) 'Verified $verified',
      status,
    ];

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(14, 4, 12, 8),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Padding(
                padding: EdgeInsets.only(top: 2),
                child: Icon(Icons.workspace_premium_outlined, size: 18, color: AppColors.primaryBlue),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(title, style: TextStyle(fontSize: scale.scale(14), fontWeight: FontWeight.w600, height: 1.3)),
                    Text(scoreBits.join(' · '), style: TextStyle(fontSize: scale.scale(12), color: AppColors.textMuted, height: 1.35)),
                    if (remarks != null && remarks.isNotEmpty)
                      Text('Reviewer: $remarks', style: TextStyle(fontSize: scale.scale(12), color: AppColors.amberText, height: 1.35)),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right, size: 18, color: AppColors.textMuted),
            ],
          ),
        ),
      ),
    );
  }
}
