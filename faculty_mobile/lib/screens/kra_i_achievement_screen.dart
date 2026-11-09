import 'dart:typed_data';

import 'package:flutter/material.dart';

import '../data/assessment_catalog.dart';
import '../repositories/mock_repository.dart';
import '../services/achievement_api.dart';
import '../services/achievement_attachment_upload.dart';
import '../services/faculty_refresh.dart';
import '../theme/app_theme.dart';
import '../widgets/achievement_attachments_panel.dart';

class KraIAchievementScreen extends StatefulWidget {
  final MockRepository repo;
  final CriterionNode criterion;
  final IndicatorNode? indicator;
  final Future<void> Function() onSave;

  const KraIAchievementScreen({
    super.key,
    required this.repo,
    required this.criterion,
    this.indicator,
    required this.onSave,
  });

  @override
  State<KraIAchievementScreen> createState() => _KraIAchievementScreenState();
}

class _KraIAchievementScreenState extends State<KraIAchievementScreen> {
  List<Map<String, dynamic>> items = [];
  String? loadError;
  bool loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      loading = true;
      loadError = null;
    });
    try {
      items = await AchievementApi.list(
        criterionId: widget.criterion.id,
        indicatorId: widget.indicator?.id,
      );
    } catch (e) {
      loadError = e.toString();
    }
    if (mounted) setState(() => loading = false);
  }

  Future<void> _openEditor([Map<String, dynamic>? existing]) async {
    final ind = widget.indicator;
    if (ind == null) return;
    final saved = await Navigator.push<bool>(
      context,
      MaterialPageRoute(
        builder: (_) => _AchievementEditor(
          repo: widget.repo,
          criterion: widget.criterion,
          indicator: ind,
          existing: existing,
        ),
      ),
    );
    if (saved == true) {
      await _load();
      await widget.onSave();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.indicator?.name ?? widget.criterion.name)),
      floatingActionButton: widget.indicator == null
          ? null
          : FloatingActionButton(
              onPressed: () => _openEditor(),
              child: const Icon(Icons.add),
            ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text(
              _criterionCapHint(),
              style: const TextStyle(color: AppColors.textMuted),
            ),
            if (loading) const LinearProgressIndicator(),
            if (loadError != null) Text(loadError!, style: const TextStyle(color: Colors.red)),
            ...items.map((a) {
              final claimed = a['claimedPoints'];
              final verified = a['reviewerVerifiedPoints'];
              return Card(
                child: ListTile(
                  title: Text(a['title']?.toString() ?? 'Untitled'),
                  subtitle: Text(
                    'Claimed $claimed · ${_achievementStatusLabel(a)}'
                    '${verified != null ? " · verified $verified" : ""}'
                    '${a['submittedAt'] != null ? "\nSubmitted ${a['submittedAt']}" : ""}'
                    '${a['reviewRemarks'] != null ? "\n${a['reviewRemarks']}" : ""}',
                  ),
                  onTap: _achievementStatusLabel(a).startsWith('Draft') ||
                          a['reviewStatus'] == 'correction_requested'
                      ? () => _openEditor(a)
                      : null,
                ),
              );
            }),
            if (!loading && items.isEmpty)
              const Padding(
                padding: EdgeInsets.only(top: 24),
                child: Text('No achievements yet. Add evidence-backed self-assessment entries.'),
              ),
          ],
        ),
      ),
    );
  }

  String _criterionCapHint() {
    switch (widget.criterion.id) {
      case 'kra-I-B':
        return 'Criterion B cap: 30 points. Claims require supporting documents.';
      case 'kra-I-C':
        return 'Criterion C cap: 10 points. Claims require supporting documents.';
      case 'kra-II-A':
      case 'kra-II-B':
      case 'kra-II-C':
        return 'Criterion cap: 100 points (KRA II). Claims require supporting documents.';
      case 'kra-III-A':
        return 'Criterion A cap: 30 points. Claims require supporting documents.';
      case 'kra-III-B':
        return 'Criterion B cap: 50 points (ISR subgroup max 30). Claims require supporting documents.';
      case 'kra-III-C':
        return 'Criterion C cap: 20 points. Link ISR project from Criterion B. Claims require supporting documents.';
      case 'kra-III-D':
        return 'Bonus Criterion D cap: 20 points. Claims require supporting documents.';
      case 'kra-IV-A':
        return 'Criterion A cap: 20 points (5 per membership). Claims require supporting documents.';
      case 'kra-IV-B':
        return 'Criterion B cap: 60 points. Attendance and presentations share max-10 subcaps. Claims require supporting documents.';
      case 'kra-IV-C':
        return 'Criterion C cap: 20 points. Claims require supporting documents.';
      case 'kra-IV-D':
        return 'Criterion D cap: 20 combined. Newly appointed eligibility required. Claims require supporting documents.';
      default:
        return 'Claims require supporting documents.';
    }
  }

  String _achievementStatusLabel(Map<String, dynamic> a) {
    final sub = a['submissionStatus']?.toString() ?? 'draft';
    final rev = a['reviewStatus']?.toString();
    if (sub == 'submitted' && (rev == 'pending' || rev == null || rev.isEmpty)) {
      return 'Submitted · Pending review';
    }
    if (sub == 'submitted' && rev == 'approved') return 'Submitted · Approved';
    if (sub == 'submitted' && rev == 'rejected') return 'Submitted · Rejected';
    if (sub == 'submitted' && rev == 'correction_requested') return 'Submitted · Changes requested';
    return 'Draft';
  }
}

class _AchievementEditor extends StatefulWidget {
  final MockRepository repo;
  final CriterionNode criterion;
  final IndicatorNode indicator;
  final Map<String, dynamic>? existing;

  const _AchievementEditor({
    required this.repo,
    required this.criterion,
    required this.indicator,
    this.existing,
  });

  @override
  State<_AchievementEditor> createState() => _AchievementEditorState();
}

class _AchievementEditorState extends State<_AchievementEditor> {
  final _title = TextEditingController();
  final _date = TextEditingController();
  final _period = TextEditingController();
  final _desc = TextEditingController();
  final _claimed = TextEditingController();
  final _explanation = TextEditingController();
  String? _role;
  String? _thesisType;
  String? _patentStage;
  String? _commercializationScope;
  String? _softwareVersionType;
  String? _incomeRole;
  String? _incomeTier;
  final _incomeAmount = TextEditingController();
  String? _serviceScope;
  String? _judgeServiceType;
  String? _extensionRole;
  final _hours = TextEditingController();
  String? _linkedIsrProjectId;
  final _clientSatisfaction = TextEditingController();
  String? _designationLevel;
  String? _designationRole;
  String? _qualificationType;
  String? _attendanceScope;
  String? _awardLevel;
  String? _academicServiceRole;
  String? _industryCategory;
  final _serviceYears = TextEditingController();
  bool _newlyAppointedEligible = false;
  List<Map<String, dynamic>> _isrProjects = [];
  final _qty = TextEditingController(text: '1');
  List<AchievementAttachment> _attachments = [];
  Map<String, dynamic>? rulePreview;
  int _rulePreviewGeneration = 0;
  String? _rulePreviewIndicatorId;
  String? error;
  bool saving = false;

  @override
  void initState() {
    super.initState();
    final e = widget.existing;
    if (e != null) {
      _title.text = e['title']?.toString() ?? '';
      _date.text = e['achievementDate']?.toString() ?? '';
      _period.text = e['academicPeriod']?.toString() ?? '';
      _desc.text = e['description']?.toString() ?? '';
      _claimed.text = e['claimedPoints']?.toString() ?? '';
      _explanation.text = e['claimExplanation']?.toString() ?? '';
      _role = e['role']?.toString();
      _thesisType = e['thesisType']?.toString();
      _patentStage = e['patentStage']?.toString();
      _commercializationScope = e['commercializationScope']?.toString();
      _softwareVersionType = e['softwareVersionType']?.toString();
      _incomeRole = e['incomeRole']?.toString();
      _incomeTier = e['incomeTier']?.toString();
      _incomeAmount.text = e['incomeAmount']?.toString() ?? '';
      _serviceScope = e['serviceScope']?.toString();
      _judgeServiceType = e['judgeServiceType']?.toString();
      _extensionRole = e['extensionRole']?.toString();
      _hours.text = e['hours']?.toString() ?? '';
      _linkedIsrProjectId = e['linkedIsrProjectId']?.toString();
      _clientSatisfaction.text = e['clientSatisfactionRating']?.toString() ?? '';
      _designationLevel = e['designationLevel']?.toString();
      _designationRole = e['designationRole']?.toString();
      _qualificationType = e['qualificationType']?.toString();
      _attendanceScope = e['attendanceScope']?.toString();
      _awardLevel = e['awardLevel']?.toString();
      _academicServiceRole = e['academicServiceRole']?.toString();
      _industryCategory = e['industryCategory']?.toString();
      _serviceYears.text = e['serviceYears']?.toString() ?? '';
      _newlyAppointedEligible = e['newlyAppointedEligible'] == true;
      _qty.text = (e['quantity'] ?? 1).toString();
      final ids = List<String>.from(e['documentIds'] as List? ?? []);
      _attachments = ids.map((id) {
        final doc = widget.repo.documentById(id);
        return AchievementAttachment(
          localKey: id,
          filename: doc?.fileName ?? id,
          sizeBytes: doc?.sizeBytes ?? 0,
          bytes: Uint8List(0),
          mimeType: 'application/octet-stream',
          status: AchievementAttachmentStatus.uploaded,
          documentPublicId: id,
          progress: 1,
        );
      }).toList();
    }
    _refreshRule();
    if (widget.indicator.id == 'kra-III-C-1') {
      _loadIsrProjects();
    }
  }

  Future<void> _loadIsrProjects() async {
    try {
      final list = await AchievementApi.list(indicatorId: 'kra-III-B-2-1');
      if (mounted) setState(() => _isrProjects = list);
    } catch (_) {}
  }

  String get _kraId {
    final fromCatalog = kraIdFromPublishedCatalog(
      widget.repo.catalogKras,
      widget.indicator.id,
    );
    return fromCatalog ??
        kraIdFromIndicator(
          widget.indicator.id,
          criterionId: widget.criterion.id,
        );
  }

  Map<String, dynamic> _fields() => {
        'indicatorId': widget.indicator.id,
        'criterionId': widget.criterion.id,
        'kraId': _kraId,
        'title': _title.text,
        'achievementDate': _date.text,
        'academicPeriod': _period.text,
        'description': _desc.text,
        if (_role != null) 'role': _role,
        if (_thesisType != null) 'thesisType': _thesisType,
        if (_patentStage != null) 'patentStage': _patentStage,
        if (_commercializationScope != null) 'commercializationScope': _commercializationScope,
        if (_softwareVersionType != null) 'softwareVersionType': _softwareVersionType,
        if (_incomeRole != null) 'incomeRole': _incomeRole,
        if (_incomeTier != null) 'incomeTier': _incomeTier,
        if (_incomeAmount.text.isNotEmpty) 'incomeAmount': double.tryParse(_incomeAmount.text),
        if (_serviceScope != null) 'serviceScope': _serviceScope,
        if (_judgeServiceType != null) 'judgeServiceType': _judgeServiceType,
        if (_extensionRole != null) 'extensionRole': _extensionRole,
        if (_hours.text.isNotEmpty) 'hours': double.tryParse(_hours.text),
        if (_linkedIsrProjectId != null) 'linkedIsrProjectId': _linkedIsrProjectId,
        if (_clientSatisfaction.text.isNotEmpty) 'clientSatisfactionRating': _clientSatisfaction.text,
        if (_designationLevel != null) 'designationLevel': _designationLevel,
        if (_designationRole != null) 'designationRole': _designationRole,
        if (_qualificationType != null) 'qualificationType': _qualificationType,
        if (_attendanceScope != null) 'attendanceScope': _attendanceScope,
        if (_awardLevel != null) 'awardLevel': _awardLevel,
        if (_academicServiceRole != null) 'academicServiceRole': _academicServiceRole,
        if (_industryCategory != null) 'industryCategory': _industryCategory,
        if (_serviceYears.text.isNotEmpty) 'serviceYears': double.tryParse(_serviceYears.text),
        if (widget.indicator.id.startsWith('kra-IV-D')) 'newlyAppointedEligible': _newlyAppointedEligible,
        'quantity': int.tryParse(_qty.text) ?? 1,
      };

  Future<void> _refreshRule() async {
    final generation = ++_rulePreviewGeneration;
    final indicatorId = widget.indicator.id;
    final fields = _fields();
    try {
      final result = await AchievementApi.previewRule(fields);
      if (!mounted) return;
      if (generation != _rulePreviewGeneration) return;
      if (indicatorId != widget.indicator.id) return;
      if ((fields['indicatorId']?.toString() ?? '') != indicatorId) return;
      setState(() {
        rulePreview = result;
        _rulePreviewIndicatorId = indicatorId;
        if (result['ruleExpectedPoints'] != null && _claimed.text.isEmpty) {
          _claimed.text = result['ruleExpectedPoints'].toString();
        }
      });
    } catch (_) {}
  }

  List<String> get _documentIds =>
      _attachments.where((a) => a.documentPublicId != null).map((a) => a.documentPublicId!).toList();

  num? _numFromMap(Map? m, String key) {
    if (m == null) return null;
    final v = m[key];
    if (v is num) return v;
    return num.tryParse(v?.toString() ?? '');
  }

  Map<String, num> _stageMap() {
    final calc = widget.indicator.calculation;
    final stages = calc?['stages'] ?? widget.indicator.points;
    if (stages is! Map) return {};
    final out = <String, num>{};
    for (final e in stages.entries) {
      final k = e.key.toString().toUpperCase();
      final n = _numFromMap(stages, e.key.toString());
      if (n != null) out[k] = n;
    }
    return out;
  }

  Map<String, num> _tierOptions() {
    final calc = widget.indicator.calculation;
    final opts = calc?['options'] ?? widget.indicator.points;
    if (opts is! Map) return {};
    final out = <String, num>{};
    for (final e in opts.entries) {
      final n = _numFromMap(opts, e.key.toString());
      if (n != null) out[e.key.toString()] = n;
    }
    return out;
  }

  String get _claimedMaxHint {
    final pm = rulePreview?['permittedMax'];
    if (pm is num) return pm.toString();
    final exp = rulePreview?['ruleExpectedPoints'];
    if (exp is num) return exp.toString();
    final indMax = widget.indicator.maxPoints;
    if (indMax != null) return indMax.toString();
    return 'per rule';
  }

  String get _rulePreviewLine {
    if (rulePreview == null) return '';
    if (_rulePreviewIndicatorId != null && _rulePreviewIndicatorId != widget.indicator.id) {
      return 'Updating rule preview…';
    }
    final unresolved = rulePreview!['unresolved'];
    if (unresolved != null && unresolved.toString().isNotEmpty) {
      return unresolved.toString();
    }
    final exp = rulePreview!['ruleExpectedPoints'];
    final max = rulePreview!['permittedMax'] ?? widget.indicator.maxPoints;
    final expStr = exp != null ? exp.toString() : '—';
    final maxStr = max != null ? max.toString() : '—';
    return 'Expected: $expStr · Max $maxStr';
  }

  List<DropdownMenuItem<String>> _patentStageItems() {
    const names = {'A': 'Acceptance', 'P': 'Publication', 'G': 'Grant'};
    final st = _stageMap();
    if (st.isEmpty) {
      return const [
        DropdownMenuItem(value: 'A', child: Text('A — Acceptance (10 pts)')),
        DropdownMenuItem(value: 'P', child: Text('P — Publication (20 pts)')),
        DropdownMenuItem(value: 'G', child: Text('G — Grant (80 pts)')),
      ];
    }
    return ['A', 'P', 'G']
        .where(st.containsKey)
        .map(
          (s) => DropdownMenuItem(
            value: s,
            child: Text('$s — ${names[s]} (${st[s]} pts)'),
          ),
        )
        .toList();
  }

  List<DropdownMenuItem<String>> _commercialItems() {
    final opts = _tierOptions();
    final local = opts['local'];
    final intl = opts['international'];
    if (local == null && intl == null) {
      return const [
        DropdownMenuItem(value: 'local', child: Text('Local (5 pts, tier max 20)')),
        DropdownMenuItem(value: 'international', child: Text('International (10 pts, tier max 30)')),
      ];
    }
    final items = <DropdownMenuItem<String>>[];
    if (local != null) {
      items.add(DropdownMenuItem(value: 'local', child: Text('Local ($local pts)')));
    }
    if (intl != null) {
      items.add(DropdownMenuItem(value: 'international', child: Text('International ($intl pts)')));
    }
    return items;
  }

  Map<String, num> _hourlyRates() {
    final calc = widget.indicator.calculation;
    final rates = calc?['rates'] ?? widget.indicator.points;
    if (rates is! Map) return {};
    final out = <String, num>{};
    for (final e in rates.entries) {
      final n = _numFromMap(rates, e.key.toString());
      if (n != null) out[e.key.toString()] = n;
    }
    return out;
  }

  List<DropdownMenuItem<String>> _scopeTierItems() {
    final opts = _tierOptions();
    if (opts.isEmpty) {
      return const [
        DropdownMenuItem(value: 'local', child: Text('Local')),
        DropdownMenuItem(value: 'international', child: Text('International')),
      ];
    }
    return opts.entries
        .map((e) => DropdownMenuItem(value: e.key, child: Text('${e.key} (${e.value} pts)')))
        .toList();
  }

  List<DropdownMenuItem<String>> _judgeTierItems() {
    final opts = _tierOptions();
    if (opts.isEmpty) {
      return const [
        DropdownMenuItem(value: 'research_award', child: Text('research_award')),
        DropdownMenuItem(value: 'academic_competition', child: Text('academic_competition')),
      ];
    }
    return opts.entries
        .map((e) => DropdownMenuItem(value: e.key, child: Text('${e.key} (${e.value} pts)')))
        .toList();
  }

  List<DropdownMenuItem<String>> _extensionRoleItems() {
    final opts = _tierOptions();
    if (opts.isEmpty) {
      return const [
        DropdownMenuItem(value: 'lead', child: Text('lead')),
        DropdownMenuItem(value: 'participant', child: Text('participant')),
      ];
    }
    return opts.entries
        .map((e) => DropdownMenuItem(value: e.key, child: Text('${e.key} (${e.value} pts)')))
        .toList();
  }

  List<DropdownMenuItem<String>> _softwareItems() {
    final opts = _tierOptions();
    final neu = opts['new'];
    final upd = opts['updated'];
    if (neu == null && upd == null) {
      return const [
        DropdownMenuItem(value: 'new', child: Text('New product (10 pts)')),
        DropdownMenuItem(value: 'updated', child: Text('Updated product (4 pts)')),
      ];
    }
    final items = <DropdownMenuItem<String>>[];
    if (neu != null) items.add(DropdownMenuItem(value: 'new', child: Text('New product ($neu pts)')));
    if (upd != null) items.add(DropdownMenuItem(value: 'updated', child: Text('Updated product ($upd pts)')));
    return items;
  }

  String? get _submitBlocker {
    if (_title.text.trim().isEmpty) return 'Title is required before submit.';
    if (double.tryParse(_claimed.text) == null) return 'Enter claimed points before submit.';
    if (_documentIds.isEmpty) return 'At least one uploaded supporting document is required.';
    if (_attachments.any((a) => a.blocksSubmit)) {
      return 'Finish uploading all supporting documents (or remove failed ones) before submitting.';
    }
    return null;
  }

  Future<void> _save({bool submit = false}) async {
    if (submit) {
      final blocker = _submitBlocker;
      if (blocker != null) {
        setState(() => error = blocker);
        return;
      }
    }
    setState(() {
      saving = true;
      error = null;
    });
    try {
      await uploadAllPendingAchievementAttachments(
        attachments: _attachments,
        indicatorId: widget.indicator.id,
        kraId: _kraId,
        title: _title.text.trim().isEmpty ? null : _title.text.trim(),
      );
      if (mounted) setState(() {});
      if (_attachments.any((a) => a.blocksSubmit)) {
        setState(() {
          error = submit
              ? 'Finish uploading all supporting documents (or remove failed ones) before submitting.'
              : 'Some files are not uploaded yet. Save draft after each upload succeeds, or retry failed files.';
          saving = false;
        });
        return;
      }
      final body = {
        ..._fields(),
        'claimedPoints': double.tryParse(_claimed.text),
        'claimExplanation': _explanation.text,
        'documentIds': _documentIds,
      };
      Map<String, dynamic> ach;
      final existingId = widget.existing?['id'] as String?;
      if (existingId != null) {
        if (submit) {
          ach = await AchievementApi.submit(existingId, body: body);
        } else {
          ach = await AchievementApi.update(existingId, body);
        }
      } else {
        ach = await AchievementApi.create(body);
        if (submit) {
          ach = await AchievementApi.submit(ach['id'] as String, body: body);
        }
      }
      if (submit && (ach['submissionStatus'] ?? '') != 'submitted') {
        throw Exception('Submission did not complete. Please try again.');
      }
      await widget.repo.refreshFromApi(
        scopes: {
          FacultyRefreshScope.documents,
          FacultyRefreshScope.scores,
        },
        expectedGeneration: 0,
      );
      if (mounted) Navigator.pop(context, true);
    } catch (e) {
      setState(() => error = e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final isMatrix = widget.indicator.id == 'kra-I-C-1';
    final isRoleB2 = widget.indicator.id == 'kra-I-B-2';
    final isPatent = widget.indicator.id == 'kra-II-B-1-1';
    final isCommercial = widget.indicator.id == 'kra-II-B-1-2';
    final isSoftware = widget.indicator.id == 'kra-II-B-2-1';
    final isIncome = widget.indicator.id == 'kra-III-A-2';
    final isScopeTier = {
      'kra-III-B-1-1',
      'kra-III-B-1-3',
      'kra-III-B-1-5',
    }.contains(widget.indicator.id);
    final isJudge = widget.indicator.id == 'kra-III-B-1-2';
    final isExtension = widget.indicator.id == 'kra-III-B-2-1';
    final isSatisfaction = widget.indicator.id == 'kra-III-C-1';
    final isDesignation = widget.indicator.id == 'kra-III-D-1';
    final isQual = widget.indicator.id == 'kra-IV-B-1';
    final isAttendance = widget.indicator.id == 'kra-IV-B-2';
    final isAward = widget.indicator.id == 'kra-IV-C-1';
    final isAcadService = widget.indicator.id == 'kra-IV-D-1';
    final isIndustry = widget.indicator.id == 'kra-IV-D-2';
    return Scaffold(
      appBar: AppBar(title: Text(widget.indicator.name)),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (rulePreview != null)
            Text(
              _rulePreviewLine,
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
          TextField(controller: _title, decoration: const InputDecoration(labelText: 'Title / description')),
          TextField(controller: _date, decoration: const InputDecoration(labelText: 'Relevant date')),
          TextField(controller: _period, decoration: const InputDecoration(labelText: 'Academic period')),
          TextField(controller: _desc, maxLines: 3, decoration: const InputDecoration(labelText: 'Details')),
          if (isRoleB2)
            DropdownButtonFormField<String>(
              value: _role,
              decoration: const InputDecoration(labelText: 'Role'),
              items: const [
                DropdownMenuItem(value: 'lead', child: Text('Lead developer')),
                DropdownMenuItem(value: 'contributor', child: Text('Contributor (5 pts)')),
              ],
              onChanged: (v) {
                setState(() => _role = v);
                _refreshRule();
              },
            ),
          if (isPatent)
            DropdownButtonFormField<String>(
              value: _patentStage,
              decoration: const InputDecoration(
                labelText: 'Patent stage (one per achievement)',
                helperText: 'A/P/G points do not accumulate across stages.',
              ),
              items: _patentStageItems(),
              onChanged: (v) {
                setState(() => _patentStage = v);
                _refreshRule();
              },
            ),
          if (isCommercial)
            DropdownButtonFormField<String>(
              value: _commercializationScope,
              decoration: const InputDecoration(labelText: 'Commercialization scope'),
              items: _commercialItems(),
              onChanged: (v) {
                setState(() => _commercializationScope = v);
                _refreshRule();
              },
            ),
          if (isIncome) ...[
            DropdownButtonFormField<String>(
              value: _incomeRole,
              decoration: const InputDecoration(labelText: 'Income role'),
              items: const [
                DropdownMenuItem(value: 'lead', child: Text('Lead')),
                DropdownMenuItem(value: 'contributor', child: Text('Contributor')),
              ],
              onChanged: (v) {
                setState(() => _incomeRole = v);
                _refreshRule();
              },
            ),
            DropdownButtonFormField<String>(
              value: _incomeTier,
              decoration: const InputDecoration(
                labelText: 'Income tier (optional if amount entered)',
                helperText: 'Tier t3 is ambiguous in the workbook until admin confirms bounds.',
              ),
              items: const [
                DropdownMenuItem(value: 't1', child: Text('t1 — up to 100,000')),
                DropdownMenuItem(value: 't2', child: Text('t2 — 100,001 to 500,000')),
                DropdownMenuItem(value: 't3', child: Text('t3 — ambiguous band (admin confirm)')),
                DropdownMenuItem(value: 't4', child: Text('t4 — 6,000,001 to 12,000,000')),
                DropdownMenuItem(value: 't5', child: Text('t5 — above 12,000,000')),
              ],
              onChanged: (v) {
                setState(() => _incomeTier = v);
                _refreshRule();
              },
            ),
            TextField(
              controller: _incomeAmount,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              decoration: const InputDecoration(labelText: 'Income amount (PHP)'),
              onChanged: (_) => _refreshRule(),
            ),
          ],
          if (isScopeTier)
            DropdownButtonFormField<String>(
              value: _serviceScope,
              decoration: InputDecoration(
                labelText: widget.indicator.id == 'kra-III-B-1-5' ? 'Scope (hourly rate)' : 'Scope',
                helperText: widget.indicator.id == 'kra-III-B-1-5'
                    ? _hourlyRates().entries.map((e) => '${e.key}: ${e.value} pts/hr').join(' · ')
                    : null,
              ),
              items: _scopeTierItems(),
              onChanged: (v) {
                setState(() => _serviceScope = v);
                _refreshRule();
              },
            ),
          if (widget.indicator.id == 'kra-III-B-1-5')
            TextField(
              controller: _hours,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              decoration: const InputDecoration(labelText: 'Hours'),
              onChanged: (_) => _refreshRule(),
            ),
          if (isJudge)
            DropdownButtonFormField<String>(
              value: _judgeServiceType,
              decoration: const InputDecoration(labelText: 'Service type'),
              items: _judgeTierItems(),
              onChanged: (v) {
                setState(() => _judgeServiceType = v);
                _refreshRule();
              },
            ),
          if (isExtension)
            DropdownButtonFormField<String>(
              value: _extensionRole,
              decoration: const InputDecoration(labelText: 'Extension role'),
              items: _extensionRoleItems(),
              onChanged: (v) {
                setState(() => _extensionRole = v);
                _refreshRule();
              },
            ),
          if (isSatisfaction) ...[
            DropdownButtonFormField<String>(
              value: _linkedIsrProjectId,
              decoration: const InputDecoration(
                labelText: 'Linked ISR extension project',
                helperText: 'Must match a kra-III-B-2-1 achievement in your assessment.',
              ),
              items: _isrProjects
                  .map(
                    (p) => DropdownMenuItem(
                      value: p['id'] as String?,
                      child: Text(p['title']?.toString() ?? p['id']?.toString() ?? 'Project'),
                    ),
                  )
                  .toList(),
              onChanged: (v) {
                setState(() => _linkedIsrProjectId = v);
                _refreshRule();
              },
            ),
            TextField(
              controller: _clientSatisfaction,
              decoration: const InputDecoration(
                labelText: 'Client satisfaction rating (evidence)',
                helperText: 'Points conversion is unresolved until configured.',
              ),
              onChanged: (_) => _refreshRule(),
            ),
          ],
          if (isQual)
            DropdownButtonFormField<String>(
              value: _qualificationType,
              decoration: const InputDecoration(
                labelText: 'Qualification type',
                helperText: 'Section 40 eligibility must be verified.',
              ),
              items: const [
                DropdownMenuItem(value: 'post_master_diploma', child: Text('Post-master diploma/certificate (10)')),
                DropdownMenuItem(value: 'post_doctorate_diploma', child: Text('Post-doctorate diploma/certificate (10)')),
                DropdownMenuItem(value: 'additional_masters', child: Text('Additional master’s degree (20)')),
                DropdownMenuItem(value: 'doctorate', child: Text('Doctorate or additional doctorate (40)')),
              ],
              onChanged: (v) {
                setState(() => _qualificationType = v);
                _refreshRule();
              },
            ),
          if (isAttendance)
            DropdownButtonFormField<String>(
              value: _attendanceScope,
              decoration: const InputDecoration(
                labelText: 'Attendance scope',
                helperText: 'Combined max 10 across all attendance achievements.',
              ),
              items: const [
                DropdownMenuItem(value: 'local', child: Text('Local (1 pt)')),
                DropdownMenuItem(value: 'international', child: Text('International (2 pts)')),
              ],
              onChanged: (v) {
                setState(() => _attendanceScope = v);
                _refreshRule();
              },
            ),
          if (isAward)
            DropdownButtonFormField<String>(
              value: _awardLevel,
              decoration: const InputDecoration(labelText: 'Award level'),
              items: const [
                DropdownMenuItem(value: 'institutional', child: Text('Institutional (2)')),
                DropdownMenuItem(value: 'local_regional', child: Text('Local / regional (3)')),
                DropdownMenuItem(value: 'national', child: Text('National (4)')),
              ],
              onChanged: (v) {
                setState(() => _awardLevel = v);
                _refreshRule();
              },
            ),
          if (isAcadService || isIndustry) ...[
            SwitchListTile(
              value: _newlyAppointedEligible,
              onChanged: (v) {
                setState(() => _newlyAppointedEligible = v);
                _refreshRule();
              },
              title: const Text('I am eligible as newly appointed faculty (Criterion D)'),
            ),
            if (isAcadService)
              DropdownButtonFormField<String>(
                value: _academicServiceRole,
                decoration: const InputDecoration(labelText: 'Academic service role'),
                items: const [
                  DropdownMenuItem(value: 'president', child: Text('President (5/yr)')),
                  DropdownMenuItem(value: 'vp_dean_director', child: Text('VP / Dean / Director (4/yr)')),
                  DropdownMenuItem(value: 'dept_program_head', child: Text('Dept / Program Head (3/yr)')),
                  DropdownMenuItem(value: 'faculty_member', child: Text('Faculty member (2/yr)')),
                ],
                onChanged: (v) {
                  setState(() => _academicServiceRole = v);
                  _refreshRule();
                },
              ),
            if (isIndustry)
              DropdownButtonFormField<String>(
                value: _industryCategory,
                decoration: const InputDecoration(labelText: 'Industry category'),
                items: const [
                  DropdownMenuItem(value: 'managerial_supervisory', child: Text('Managerial / supervisory (4/yr)')),
                  DropdownMenuItem(value: 'technical_skilled', child: Text('Technical and skilled (3/yr)')),
                  DropdownMenuItem(value: 'support_admin', child: Text('Support / administrative (2/yr)')),
                ],
                onChanged: (v) {
                  setState(() => _industryCategory = v);
                  _refreshRule();
                },
              ),
            TextField(
              controller: _serviceYears,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              decoration: const InputDecoration(
                labelText: 'Years of service',
                helperText: 'Whole years only until fractional-year policy is published.',
              ),
              onChanged: (_) => _refreshRule(),
            ),
          ],
          if (isDesignation) ...[
            DropdownButtonFormField<String>(
              value: _designationLevel,
              decoration: const InputDecoration(labelText: 'Designation level'),
              items: const [
                DropdownMenuItem(value: 'institutional', child: Text('Institutional level')),
                DropdownMenuItem(value: 'college_department', child: Text('College / department level')),
              ],
              onChanged: (v) {
                setState(() => _designationLevel = v);
                _refreshRule();
              },
            ),
            DropdownButtonFormField<String>(
              value: _designationRole,
              decoration: const InputDecoration(labelText: 'Designation role'),
              items: (_designationLevel == 'college_department'
                      ? const [
                          MapEntry('dean', 'Dean (6)'),
                          MapEntry('associate_dean', 'Associate dean (5)'),
                          MapEntry('college_secretary', 'College secretary (3)'),
                          MapEntry('department_head', 'Department head (4)'),
                          MapEntry('program_chair', 'Program chair (3)'),
                          MapEntry('dept_committee_chair', 'Dept committee chair (2)'),
                          MapEntry('dept_committee_member', 'Dept committee member (1)'),
                          MapEntry('dept_coordinator', 'Dept coordinator (1)'),
                        ]
                      : const [
                          MapEntry('president', 'President (20)'),
                          MapEntry('vice_president', 'Vice-president (15)'),
                          MapEntry('chancellor', 'Chancellor (10)'),
                          MapEntry('vice_chancellor', 'Vice-chancellor (8)'),
                          MapEntry('campus_director', 'Campus director (8)'),
                          MapEntry('faculty_trustee', 'Faculty trustee (8)'),
                          MapEntry('office_director', 'Office director (6)'),
                          MapEntry('university_secretary', 'University secretary (6)'),
                          MapEntry('project_head', 'Project head (4)'),
                          MapEntry('inst_committee_chair', 'Institution committee chair (3)'),
                          MapEntry('inst_committee_member', 'Institution committee member (2)'),
                          MapEntry('inst_coordinator', 'Institution coordinator (2)'),
                        ])
                  .map((e) => DropdownMenuItem(value: e.key, child: Text(e.value)))
                  .toList(),
              onChanged: (v) {
                setState(() => _designationRole = v);
                _refreshRule();
              },
            ),
          ],
          if (isSoftware)
            DropdownButtonFormField<String>(
              value: _softwareVersionType,
              decoration: const InputDecoration(labelText: 'Software version'),
              items: _softwareItems(),
              onChanged: (v) {
                setState(() => _softwareVersionType = v);
                _refreshRule();
              },
            ),
          if (isMatrix) ...[
            DropdownButtonFormField<String>(
              value: _role,
              decoration: const InputDecoration(labelText: 'Service role'),
              items: const [
                DropdownMenuItem(value: 'adviser', child: Text('Adviser')),
                DropdownMenuItem(value: 'panel', child: Text('Panel member')),
              ],
              onChanged: (v) {
                setState(() => _role = v);
                _refreshRule();
              },
            ),
            DropdownButtonFormField<String>(
              value: _thesisType,
              decoration: const InputDecoration(labelText: 'Thesis type'),
              items: const [
                DropdownMenuItem(value: 'SP_CP', child: Text('SP/CP')),
                DropdownMenuItem(value: 'UT', child: Text('Undergraduate thesis')),
                DropdownMenuItem(value: 'MT', child: Text('Master\'s thesis')),
                DropdownMenuItem(value: 'DD', child: Text('Dissertation')),
              ],
              onChanged: (v) {
                setState(() => _thesisType = v);
                _refreshRule();
              },
            ),
            TextField(
              controller: _qty,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(labelText: 'Quantity'),
              onChanged: (_) => _refreshRule(),
            ),
          ],
          TextField(
            controller: _claimed,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            decoration: InputDecoration(labelText: 'Claimed points (max $_claimedMaxHint)'),
          ),
          TextField(
            controller: _explanation,
            decoration: const InputDecoration(labelText: 'Claim explanation (optional)'),
          ),
          const SizedBox(height: 8),
          AchievementAttachmentsPanel(
            attachments: _attachments,
            indicatorId: widget.indicator.id,
            kraId: _kraId,
            titleHint: _title.text.trim().isEmpty ? null : _title.text.trim(),
            onChanged: (list) => setState(() => _attachments = list),
          ),
          if (error != null) Text(error!, style: const TextStyle(color: Colors.red)),
          const SizedBox(height: 16),
          FilledButton(
            onPressed: saving ? null : () => _save(),
            child: Text(saving ? 'Saving…' : 'Save draft'),
          ),
          const SizedBox(height: 8),
          FilledButton.tonal(
            onPressed: saving ? null : () => _save(submit: true),
            child: Text(saving ? 'Submitting…' : 'Submit to reviewer'),
          ),
        ],
      ),
    );
  }
}
