import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../core/ui_strings.dart';
import '../data/assessment_catalog.dart';
import '../repositories/mock_repository.dart';
import '../theme/app_spacing.dart';
import '../theme/app_theme.dart';

class UploadEvidenceScreen extends StatefulWidget {
  final MockRepository repo;
  final VoidCallback onSave;
  const UploadEvidenceScreen({super.key, required this.repo, required this.onSave});

  @override
  State<UploadEvidenceScreen> createState() => _UploadEvidenceScreenState();
}

class _UploadEvidenceScreenState extends State<UploadEvidenceScreen> {
  int _step = 0;
  KraNode? _kra;
  CriterionNode? _crit;
  IndicatorNode? _ind;
  String? _fileName;
  final _title = TextEditingController();
  final _year = TextEditingController();
  final _sem = TextEditingController();

  @override
  void dispose() {
    _title.dispose();
    _year.dispose();
    _sem.dispose();
    super.dispose();
  }

  void _next() {
    if (_step < 3) setState(() => _step++);
  }

  void _back() {
    if (_step > 0) setState(() => _step--);
  }

  bool _validateStep(int step) {
    switch (step) {
      case 0:
        if (_kra == null) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Choose a KRA to continue.')),
          );
          return false;
        }
        return true;
      case 1:
        if (_crit == null || _ind == null) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Choose a criterion and indicator.')),
          );
          return false;
        }
        return true;
      case 2:
        if (_fileName == null) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Choose a file to continue.')),
          );
          return false;
        }
        if ((_ind?.subType == 'SET' || _ind?.subType == 'SEF') && _year.text.trim().isEmpty) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Enter an academic year.')),
          );
          return false;
        }
        return true;
      default:
        return true;
    }
  }

  void _continue() {
    if (!_validateStep(_step)) return;
    _next();
  }

  String get _breadcrumb {
    if (_ind == null) return 'Add document';
    return 'My Documents → ${_kra?.shortDropdownLabel ?? ''} → ${_crit?.name ?? ''} → ${_ind!.name}';
  }

  Future<void> _submit() async {
    if (_ind == null || _fileName == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Choose an indicator and add a file first.')),
      );
      return;
    }
    if (_ind!.subType == 'SET' || _ind!.subType == 'SEF') {
      if (_year.text.trim().isEmpty) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Choose an academic year.')),
        );
        return;
      }
    }
    widget.repo.documents.add(FacultyDocument(
      id: 'd-${DateTime.now().millisecondsSinceEpoch}',
      indicatorId: _ind!.id,
      kraId: _kra!.id,
      fileName: _fileName!,
      folder: _ind!.subType,
      academicYear: _year.text.isEmpty ? null : _year.text,
      semester: _sem.text.isEmpty ? null : _sem.text,
      reviewStatus: 'pending',
      ocrText: 'SIMULATED OCR — demonstration only until server upload',
    ));
    await widget.repo.save();
    widget.onSave();
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Your document was sent for review.')),
    );
    Navigator.pop(context);
  }

  Widget _dropdownLabel(String text) {
    return Text(
      text,
      overflow: TextOverflow.ellipsis,
      maxLines: 3,
      softWrap: true,
    );
  }

  @override
  Widget build(BuildContext context) {
    final textScale = MediaQuery.textScalerOf(context);
    return Scaffold(
      appBar: AppBar(
        title: const Text('Add document'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          tooltip: 'Back',
          onPressed: () => Navigator.maybePop(context),
        ),
      ),
      body: ListView(
        padding: FlLayout.pagePadding,
        children: [
          Text(
            'Add proof for your assessment',
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  fontSize: textScale.scale(26),
                  fontWeight: FontWeight.w700,
                  color: AppColors.textNavy,
                ),
          ),
          const SizedBox(height: 6),
          Text(
            'Follow the steps below. Your answers stay on this screen when you go back.',
            style: TextStyle(fontSize: textScale.scale(17), color: AppColors.textMuted, height: 1.5),
          ),
          const SizedBox(height: 12),
          Text(
            'Step ${_step + 1} of 4',
            style: TextStyle(
              fontSize: textScale.scale(16),
              fontWeight: FontWeight.w700,
              color: AppColors.primaryBlue,
            ),
          ),
          const SizedBox(height: 6),
          ClipRRect(
            borderRadius: BorderRadius.circular(8),
            child: LinearProgressIndicator(
              value: (_step + 1) / 4,
              minHeight: 8,
              backgroundColor: AppColors.border,
              color: AppColors.primaryBlue,
            ),
          ),
          const SizedBox(height: 16),
          Stepper(
            type: StepperType.vertical,
            currentStep: _step,
            onStepContinue: _step < 3 ? _continue : null,
            onStepCancel: _step > 0 ? _back : null,
            controlsBuilder: (context, details) {
              return Padding(
                padding: const EdgeInsets.only(top: 12),
                child: Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    if (details.stepIndex > 0)
                      TextButton(onPressed: details.onStepCancel, child: const Text('Back')),
                    if (details.stepIndex < 3)
                      FilledButton(onPressed: details.onStepContinue, child: const Text('Next')),
                    if (details.stepIndex == 3)
                      FilledButton(onPressed: _submit, child: const Text('Send for review')),
                  ],
                ),
              );
            },
            steps: [
              Step(
                title: Text(
                  'Choose assessment area (KRA)',
                  softWrap: true,
                ),
                subtitle: Text(UiStrings.kraHelp, softWrap: true),
                isActive: _step >= 0,
                state: _step > 0 ? StepState.complete : StepState.indexed,
                content: SizedBox(
                  width: double.infinity,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      DropdownButtonFormField<KraNode>(
                        isExpanded: true,
                        value: _kra,
                        decoration: const InputDecoration(labelText: 'KRA (Key Result Area)'),
                        items: assessmentKras
                            .map(
                              (k) => DropdownMenuItem(
                                value: k,
                                child: _dropdownLabel(k.shortDropdownLabel),
                              ),
                            )
                            .toList(),
                        selectedItemBuilder: (context) => assessmentKras
                            .map(
                              (k) => Align(
                                alignment: AlignmentDirectional.centerStart,
                                child: Text(
                                  k.shortDropdownLabel,
                                  overflow: TextOverflow.ellipsis,
                                  maxLines: 2,
                                ),
                              ),
                            )
                            .toList(),
                        onChanged: (v) => setState(() {
                          _kra = v;
                          _crit = null;
                          _ind = null;
                        }),
                      ),
                      if (_kra != null) ...[
                        const SizedBox(height: 8),
                        Text(
                          _kra!.name,
                          style: TextStyle(fontSize: textScale.scale(14), color: Colors.grey.shade700, height: 1.45),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
              Step(
                title: Text('Choose criterion and indicator', softWrap: true),
                isActive: _step >= 1,
                state: _step > 1 ? StepState.complete : StepState.indexed,
                content: SizedBox(
                  width: double.infinity,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      if (_kra == null) const Text('Go back and choose a KRA first.'),
                      if (_kra != null)
                        DropdownButtonFormField<CriterionNode>(
                          isExpanded: true,
                          value: _crit,
                          decoration: const InputDecoration(labelText: 'Criterion'),
                          items: _kra!.criteria
                              .map(
                                (c) => DropdownMenuItem(
                                  value: c,
                                  child: _dropdownLabel(c.name),
                                ),
                              )
                              .toList(),
                          onChanged: (v) => setState(() {
                            _crit = v;
                            _ind = null;
                          }),
                        ),
                      if (_crit != null) ...[
                        const SizedBox(height: 8),
                        DropdownButtonFormField<IndicatorNode>(
                          isExpanded: true,
                          value: _ind,
                          decoration: const InputDecoration(labelText: 'Indicator'),
                          items: _crit!.indicators
                              .map(
                                (i) => DropdownMenuItem(
                                  value: i,
                                  child: _dropdownLabel(i.name),
                                ),
                              )
                              .toList(),
                          onChanged: (v) => setState(() => _ind = v),
                        ),
                      ],
                      if (_ind != null)
                        Card(
                          margin: const EdgeInsets.only(top: 12),
                          child: Padding(
                            padding: const EdgeInsets.all(12),
                            child: Text(
                              _ind!.maxPoints != null
                                  ? 'This indicator can earn up to ${_ind!.maxPoints} points when verified.'
                                  : 'Point rules for this indicator follow the official guidelines.',
                              style: TextStyle(fontSize: textScale.scale(15), height: 1.45),
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
              ),
              Step(
                title: Text('Add your file and details', softWrap: true),
                isActive: _step >= 2,
                state: _step > 2 ? StepState.complete : StepState.indexed,
                content: SizedBox(
                  width: double.infinity,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Semantics(
                        button: true,
                        label: 'Choose file from device',
                        child: OutlinedButton.icon(
                          onPressed: () async {
                            final r = await FilePicker.platform.pickFiles(
                              type: FileType.custom,
                              allowedExtensions: ['pdf', 'png', 'jpg'],
                            );
                            if (r != null && r.files.single.name.isNotEmpty) {
                              setState(() => _fileName = r.files.single.name);
                            }
                          },
                          icon: const Icon(Icons.attach_file),
                          label: Text(
                            _fileName ?? 'Choose file',
                            overflow: TextOverflow.ellipsis,
                            maxLines: 2,
                            softWrap: true,
                          ),
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(UiStrings.uploadDemoNote, style: TextStyle(fontSize: 13, color: Colors.grey.shade600)),
                      const SizedBox(height: 12),
                      TextField(
                        controller: _title,
                        decoration: const InputDecoration(labelText: 'Title or short description'),
                      ),
                      if (_ind?.subType == 'SET' || _ind?.subType == 'SEF') ...[
                        TextField(
                          controller: _year,
                          decoration: const InputDecoration(labelText: 'Academic year (required)'),
                        ),
                        TextField(
                          controller: _sem,
                          decoration: const InputDecoration(labelText: 'Semester (example: 1st Sem)'),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
              Step(
                title: Text('Check and send', softWrap: true),
                isActive: _step >= 3,
                content: SizedBox(
                  width: double.infinity,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(_breadcrumb, style: const TextStyle(fontWeight: FontWeight.w600)),
                      const SizedBox(height: 8),
                      Text('File: ${_fileName ?? "—"}'),
                      Text('Description: ${_title.text.isEmpty ? "—" : _title.text}'),
                      const SizedBox(height: 12),
                      Text(
                        'Your reviewer will check this document. OCR help text is demonstration-only.',
                        style: TextStyle(fontSize: textScale.scale(15), height: 1.45),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
