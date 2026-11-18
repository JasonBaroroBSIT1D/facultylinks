import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../core/ui_strings.dart';
import '../data/assessment_catalog.dart';
import '../repositories/mock_repository.dart';
import '../services/camera_document_capture.dart';
import '../services/document_api.dart';
import '../services/selected_upload_file.dart';
import 'kra_i_achievement_screen.dart';
import '../theme/app_spacing.dart';
import '../theme/app_theme.dart';

enum _CriterionADocChoice { setSef, special }

class UploadEvidenceScreen extends StatefulWidget {
  final MockRepository repo;
  final Future<void> Function() onSave;
  final String? initialKraId;
  final String? initialCriterionId;
  final String? initialIndicatorId;

  const UploadEvidenceScreen({
    super.key,
    required this.repo,
    required this.onSave,
    this.initialKraId,
    this.initialCriterionId,
    this.initialIndicatorId,
  });

  @override
  State<UploadEvidenceScreen> createState() => _UploadEvidenceScreenState();
}

class _UploadEvidenceScreenState extends State<UploadEvidenceScreen> {
  int _step = 0;
  KraNode? _kra;
  CriterionNode? _crit;
  IndicatorNode? _ind;
  _CriterionADocChoice? _criterionAChoice;
  SelectedUploadFile? _selectedFile;
  bool _pickingFile = false;
  bool _capturingPhoto = false;
  bool _uploading = false;
  final _cameraCapture = CameraDocumentCapture();
  final _title = TextEditingController();
  final _year = TextEditingController();
  final _sem = TextEditingController();
  final _scrollController = ScrollController();

  String? get _fileName => _selectedFile?.filename;
  bool get _hasReadableFile => _selectedFile?.isReadable == true;

  /// Explicit SET/SEF shortcut from My Assessment (preselect Criterion A only).
  bool get _preselectCriterionA =>
      widget.initialKraId == 'kra-I' && widget.initialCriterionId == 'kra-I-A';

  bool get _skipKraCriterionSteps => _preselectCriterionA;

  bool get _isTeachingCriterionA => _kra?.id == 'kra-I' && _crit?.id == 'kra-I-A';

  bool get _isAchievementCriterion =>
      _kra != null && _crit != null && isAchievementCriterion(_kra!.id, _crit!.id);

  CriterionNode? _criterionById(String id) {
    for (final k in widget.repo.catalogKras) {
      if (k.id != 'kra-I') continue;
      for (final c in k.criteria) {
        if (c.id == id) return c;
      }
    }
    return null;
  }

  bool get _publishedCatalogMissingKraIBc {
    if (!widget.repo.catalogLoadedFromApi) return true;
    return _criterionById('kra-I-B') == null || _criterionById('kra-I-C') == null;
  }

  int get _stepCount {
    if (_preselectCriterionA) return 3;
    return 4;
  }

  int get _reviewStepIndex => _stepCount - 1;
  int get _fileStepIndex => _stepCount - 2;

  @override
  void initState() {
    super.initState();
    _applyInitialSelection();
  }

  void _applyInitialSelection() {
    final kraId = widget.initialKraId;
    if (kraId == null) return;
    KraNode? kra;
    for (final k in widget.repo.catalogKras) {
      if (k.id == kraId) {
        kra = k;
        break;
      }
    }
    if (kra == null) return;
    CriterionNode? crit;
    for (final c in kra.criteria) {
      if (widget.initialCriterionId == null || c.id == widget.initialCriterionId) {
        crit = c;
        break;
      }
    }
    IndicatorNode? ind;
    if (crit != null && widget.initialIndicatorId != null) {
      ind = indicatorById(widget.repo.catalogKras, widget.initialIndicatorId!);
    }
    setState(() {
      _kra = kra;
      _crit = crit;
      _ind = ind;
      _step = 0;
    });
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_skipKraCriterionSteps && _kra == null) {
      for (final k in widget.repo.catalogKras) {
        if (k.id == 'kra-I') {
          for (final c in k.criteria) {
            if (c.id == 'kra-I-A') {
              setState(() {
                _kra = k;
                _crit = c;
              });
              break;
            }
          }
          break;
        }
      }
    }
  }

  @override
  void dispose() {
    _scrollController.dispose();
    _title.dispose();
    _year.dispose();
    _sem.dispose();
    super.dispose();
  }

  void _scrollActiveStepToTop() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || !_scrollController.hasClients) return;
      _scrollController.jumpTo(0);
    });
  }

  void _goToStep(int step) {
    setState(() => _step = step);
    _scrollActiveStepToTop();
  }

  bool get _isSetSefOcrPdf {
    final t = _ind?.type;
    return t == 'set_sef_unified_pdf' ||
        t == 'set_sef_combined_pdf' ||
        t == 'set_sef_set_pdf' ||
        t == 'set_sef_sef_pdf';
  }

  IndicatorNode? _resolveSetSefEvalIndicator() {
    return indicatorById(widget.repo.catalogKras, criterionASetSefEvalIndicatorId) ??
        indicatorById(widget.repo.catalogKras, 'kra-I-A-setsef-combined');
  }

  void _selectCriterionAChoice(_CriterionADocChoice choice) {
    setState(() {
      _criterionAChoice = choice;
      if (choice == _CriterionADocChoice.setSef) {
        _ind = _resolveSetSefEvalIndicator();
      } else {
        _ind = indicatorById(widget.repo.catalogKras, criterionASpecialIndicatorId);
      }
    });
  }

  void _next() {
    if (_step < _reviewStepIndex) _goToStep(_step + 1);
  }

  void _back() {
    if (_step > 0) _goToStep(_step - 1);
  }

  bool _validateStep(int step) {
    if (_isTeachingCriterionA) {
      final categoryStep = _skipKraCriterionSteps ? 0 : 1;
      final fileStep = _fileStepIndex;
      if (step == categoryStep) {
        if (_criterionAChoice == null || _ind == null) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Tap SET / SEF Evaluation or Special Status to continue.')),
          );
          return false;
        }
        return true;
      }
      if (step == 0 && !_skipKraCriterionSteps) {
        if (_kra == null || _crit == null) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Choose KRA and Criterion A to continue.')),
          );
          return false;
        }
        return true;
      }
      if (step == fileStep) {
        if (!_hasReadableFile) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Choose a file to continue.')),
          );
          return false;
        }
        if (_isSetSefOcrPdf && _selectedFile!.mimeType != 'application/pdf') {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Please choose a PDF file.')),
          );
          return false;
        }
        return true;
      }
      return true;
    }

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
        if (_kra?.id == 'kra-I' && _crit == null) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Choose Criterion A, B, or C for KRA I.')),
          );
          return false;
        }
        if (_isTeachingCriterionA) {
          if (_criterionAChoice == null || _ind == null) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('Tap SET / SEF Evaluation or Special Status to continue.')),
            );
            return false;
          }
          return true;
        }
        if (_isAchievementCriterion) {
          if (_ind == null) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('Choose an indicator for this criterion.')),
            );
            return false;
          }
          return true;
        }
        if (_crit == null || _ind == null) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Choose a criterion and indicator.')),
          );
          return false;
        }
        return true;
      case 2:
        if (_isAchievementCriterion) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Use Open achievement on the previous step for Criterion B or C.')),
          );
          return false;
        }
        if (!_hasReadableFile) {
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
    if (_isAchievementCriterion && _step == 1) {
      _openAchievementFlow();
      return;
    }
    if (_isTeachingCriterionA &&
        _criterionAChoice == _CriterionADocChoice.setSef &&
        _step == (_skipKraCriterionSteps ? 0 : 1)) {
      _goToStep(_fileStepIndex);
      return;
    }
    _next();
  }

  Future<void> _openAchievementFlow() async {
    if (_crit == null || _ind == null) return;
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => KraIAchievementScreen(
          repo: widget.repo,
          criterion: _crit!,
          indicator: _ind,
          onSave: widget.onSave,
        ),
      ),
    );
  }

  String get _documentCategoryLabel {
    if (_criterionAChoice == _CriterionADocChoice.setSef) return UiStrings.setSefEvalCardTitle;
    if (_criterionAChoice == _CriterionADocChoice.special) return UiStrings.specialStatusCardTitle;
    return _ind?.name ?? 'Document';
  }

  String get _breadcrumb {
    if (_isTeachingCriterionA && _criterionAChoice != null) {
      return 'My Documents → KRA I · Instruction → Criterion A → $_documentCategoryLabel';
    }
    if (_ind == null) return 'Add document';
    return 'My Documents → ${_kra?.shortDropdownLabel ?? ''} → ${_crit?.name ?? ''} → ${_ind!.name}';
  }

  Future<void> _submit() async {
    if (_uploading) return;
    if (_ind == null || _kra == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Choose a document type and add a file first.')),
      );
      return;
    }
    if (!_hasReadableFile) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            _fileName == null
                ? 'Choose a file to continue.'
                : 'The selected file could not be read. Please select it again.',
          ),
        ),
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
    setState(() => _uploading = true);
    try {
      final file = _selectedFile!;
      final body = await DocumentApi.upload(
        bytes: file.bytes,
        filename: file.filename,
        mimeType: file.mimeType,
        indicatorId: _ind!.id,
        kraId: _kra!.id,
        title: _title.text.trim().isEmpty ? file.filename : _title.text.trim(),
      );
      final publicId = DocumentApi.publicIdFromUploadResponse(body);
      if (publicId == null || publicId.isEmpty) {
        throw Exception('Upload succeeded but no document ID was returned.');
      }
    } catch (e) {
      if (!mounted) return;
      setState(() => _uploading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString().replaceFirst('Exception: ', ''))),
      );
      return;
    }
    // Clear only after a successful upload.
    _selectedFile = null;
    await widget.repo.save();
    await widget.onSave();
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          _isSetSefOcrPdf
              ? 'Your PDF was received. We will read the semesters and your reviewer will verify the results.'
              : 'Your document was sent for review.',
        ),
      ),
    );
    Navigator.pop(context);
  }

  Future<void> _pickFile() async {
    if (_pickingFile || _capturingPhoto || _uploading) return;
    final previous = _selectedFile;
    final pdfOnly = _isSetSefOcrPdf;
    setState(() => _pickingFile = true);
    try {
      final r = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: pdfOnly ? ['pdf'] : ['pdf', 'png', 'jpg', 'jpeg', 'webp'],
        withData: true,
      );
      if (!mounted) return;
      // Cancel / dismiss: keep prior selection.
      if (r == null || r.files.isEmpty) {
        setState(() => _pickingFile = false);
        return;
      }
      final picked = r.files.single;
      final loaded = await readPlatformFileForUpload(picked);
      if (!mounted) return;
      if (loaded == null || !loaded.isReadable) {
        setState(() {
          _pickingFile = false;
          _selectedFile = previous;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('The selected file could not be read. Please select it again.'),
          ),
        );
        return;
      }
      if (pdfOnly && loaded.mimeType != 'application/pdf') {
        setState(() {
          _pickingFile = false;
          _selectedFile = previous;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text(UiStrings.setSefCameraNotSupported)),
        );
        return;
      }
      setState(() {
        _selectedFile = loaded;
        _pickingFile = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _pickingFile = false;
        _selectedFile = previous;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('The selected file could not be read. Please select it again.'),
        ),
      );
    }
  }

  Future<void> _takePhoto() async {
    if (_pickingFile || _capturingPhoto || _uploading) return;
    if (_isSetSefOcrPdf) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text(UiStrings.setSefCameraNotSupported)),
      );
      return;
    }
    final previous = _selectedFile;
    setState(() => _capturingPhoto = true);
    try {
      while (mounted) {
        final captured = await _cameraCapture.captureDocumentPhoto();
        if (!mounted) return;
        // Cancel: keep prior selection through submit/retry.
        if (captured == null) {
          setState(() {
            _capturingPhoto = false;
            _selectedFile = previous;
          });
          return;
        }
        final keep = await showCapturedPhotoPreview(
          context,
          bytes: Uint8List.fromList(captured.bytes),
          filename: captured.filename,
        );
        if (!mounted) return;
        if (keep == true) {
          setState(() {
            _selectedFile = captured;
            _capturingPhoto = false;
          });
          return;
        }
        // Retake or dialog dismiss without Use photo: loop camera again
        // but still preserve [previous] until a photo is accepted.
        if (keep == null) {
          setState(() {
            _capturingPhoto = false;
            _selectedFile = previous;
          });
          return;
        }
      }
    } on CameraCaptureException catch (e) {
      if (!mounted) return;
      setState(() {
        _capturingPhoto = false;
        _selectedFile = previous;
      });
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _capturingPhoto = false;
        _selectedFile = previous;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Could not capture a photo. Please try again.')),
      );
    }
  }

  Widget _bigChoiceCard({
    required String title,
    required String body,
    required IconData icon,
    required bool selected,
    required VoidCallback onTap,
    required TextScaler textScale,
  }) {
    return Material(
      color: selected ? AppColors.primaryBlue.withValues(alpha: 0.08) : Colors.white,
      elevation: selected ? 2 : 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(
          color: selected ? AppColors.primaryBlue : AppColors.border,
          width: selected ? 2 : 1,
        ),
      ),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 20),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(icon, size: textScale.scale(36), color: AppColors.primaryBlue),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: TextStyle(
                        fontSize: textScale.scale(20),
                        fontWeight: FontWeight.w700,
                        height: 1.3,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      body,
                      style: TextStyle(
                        fontSize: textScale.scale(17),
                        color: AppColors.textMuted,
                        height: 1.45,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildKraIVCriterionPicker(TextScaler textScale) {
    CriterionNode? byId(String id) {
      for (final c in _kra!.criteria) {
        if (c.id == id) return c;
      }
      return null;
    }

    void pick(CriterionNode c) {
      setState(() {
        _crit = c;
        _ind = null;
      });
    }

    final a = byId('kra-IV-A');
    final b = byId('kra-IV-B');
    final c = byId('kra-IV-C');
    final d = byId('kra-IV-D');
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (a != null)
          _bigChoiceCard(
            title: 'A. Professional organizations',
            body: 'Membership and participation (max 20 pts).',
            icon: Icons.groups_2_outlined,
            selected: _crit?.id == 'kra-IV-A',
            onTap: () => pick(a),
            textScale: textScale,
          ),
        if (a != null) const SizedBox(height: 10),
        if (b != null)
          _bigChoiceCard(
            title: 'B. Continuing development',
            body: 'Qualifications, attendance, presentations (max 60 pts).',
            icon: Icons.school_outlined,
            selected: _crit?.id == 'kra-IV-B',
            onTap: () => pick(b),
            textScale: textScale,
          ),
        if (b != null) const SizedBox(height: 10),
        if (c != null)
          _bigChoiceCard(
            title: 'C. Awards and recognition',
            body: 'Institutional, local/regional, national (max 20 pts).',
            icon: Icons.emoji_events_outlined,
            selected: _crit?.id == 'kra-IV-C',
            onTap: () => pick(c),
            textScale: textScale,
          ),
        if (c != null) const SizedBox(height: 10),
        if (d != null)
          _bigChoiceCard(
            title: 'D. Newly appointed faculty',
            body: 'Prior academic and industry service (max 20 pts).',
            icon: Icons.work_history_outlined,
            selected: _crit?.id == 'kra-IV-D',
            onTap: () => pick(d),
            textScale: textScale,
          ),
      ],
    );
  }

  Widget _buildKraIIICriterionPicker(TextScaler textScale) {
    CriterionNode? byId(String id) {
      for (final c in _kra!.criteria) {
        if (c.id == id) return c;
      }
      return null;
    }

    void pick(CriterionNode c) {
      setState(() {
        _crit = c;
        _ind = null;
      });
    }

    final a = byId('kra-III-A');
    final b = byId('kra-III-B');
    final c = byId('kra-III-C');
    final d = byId('kra-III-D');
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (a != null)
          _bigChoiceCard(
            title: 'A. Service to the Institution',
            body: 'Linkages and income generation (max 30 pts).',
            icon: Icons.apartment_outlined,
            selected: _crit?.id == 'kra-III-A',
            onTap: () => pick(a),
            textScale: textScale,
          ),
        if (a != null) const SizedBox(height: 10),
        if (b != null)
          _bigChoiceCard(
            title: 'B. Service to the Community',
            body: 'QA, media, training, ISR projects (max 50 pts).',
            icon: Icons.groups_outlined,
            selected: _crit?.id == 'kra-III-B',
            onTap: () => pick(b),
            textScale: textScale,
          ),
        if (b != null) const SizedBox(height: 10),
        if (c != null)
          _bigChoiceCard(
            title: 'C. Relevance and Quality',
            body: 'Client satisfaction linked to ISR projects (max 20 pts).',
            icon: Icons.star_outline,
            selected: _crit?.id == 'kra-III-C',
            onTap: () => pick(c),
            textScale: textScale,
          ),
        if (c != null) const SizedBox(height: 10),
        if (d != null)
          _bigChoiceCard(
            title: 'D. Bonus — Administrative Designations',
            body: 'Institutional and college/department roles (max 20 pts).',
            icon: Icons.badge_outlined,
            selected: _crit?.id == 'kra-III-D',
            onTap: () => pick(d),
            textScale: textScale,
          ),
      ],
    );
  }

  Widget _buildKraIICriterionPicker(TextScaler textScale) {
    CriterionNode? byId(String id) {
      for (final c in _kra!.criteria) {
        if (c.id == id) return c;
      }
      return null;
    }

    void pick(CriterionNode c) {
      setState(() {
        _crit = c;
        _ind = null;
      });
    }

    final a = byId('kra-II-A');
    final b = byId('kra-II-B');
    final c = byId('kra-II-C');
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (a != null)
          _bigChoiceCard(
            title: 'A. Research Outputs Published',
            body: 'Books, articles, translations, citations (max 100 pts).',
            icon: Icons.article_outlined,
            selected: _crit?.id == 'kra-II-A',
            onTap: () => pick(a),
            textScale: textScale,
          ),
        if (a != null) const SizedBox(height: 10),
        if (b != null)
          _bigChoiceCard(
            title: 'B. Inventions',
            body: 'Patents, commercialization, software, varieties (max 100 pts).',
            icon: Icons.lightbulb_outline,
            selected: _crit?.id == 'kra-II-B',
            onTap: () => pick(b),
            textScale: textScale,
          ),
        if (b != null) const SizedBox(height: 10),
        if (c != null)
          _bigChoiceCard(
            title: 'C. Creative Works',
            body: 'Performing/visual arts, film, literary works (max 100 pts).',
            icon: Icons.palette_outlined,
            selected: _crit?.id == 'kra-II-C',
            onTap: () => pick(c),
            textScale: textScale,
          ),
      ],
    );
  }

  Widget _buildKraICriterionPicker(TextScaler textScale) {
    if (_publishedCatalogMissingKraIBc) {
      return FlSurfaceCard(
        child: Text(
          widget.repo.catalogLoadedFromApi
              ? 'Published configuration is missing KRA I Criterion B or Criterion C. Ask an administrator to publish the full JC3 catalog.'
              : 'Assessment rules are not loaded from the server. Pull to refresh on My Assessment or try again after signing in.',
          style: TextStyle(fontSize: textScale.scale(16), color: AppColors.textMuted, height: 1.45),
        ),
      );
    }
    final critA = _criterionById('kra-I-A');
    final critB = _criterionById('kra-I-B');
    final critC = _criterionById('kra-I-C');
    void pick(CriterionNode c) {
      setState(() {
        _crit = c;
        _ind = null;
        _criterionAChoice = null;
      });
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (critA != null)
          _bigChoiceCard(
            title: 'A. Teaching Effectiveness',
            body: 'SET/SEF evaluation PDFs or special-status supporting documents.',
            icon: Icons.school_outlined,
            selected: _crit?.id == 'kra-I-A',
            onTap: () => pick(critA),
            textScale: textScale,
          ),
        if (critA != null) const SizedBox(height: 10),
        if (critB != null)
          _bigChoiceCard(
            title: 'B. Instructional Materials Development',
            body: 'Self-assessment achievements with evidence (max 30 pts).',
            icon: Icons.menu_book_outlined,
            selected: _crit?.id == 'kra-I-B',
            onTap: () => pick(critB),
            textScale: textScale,
          ),
        if (critB != null) const SizedBox(height: 10),
        if (critC != null)
          _bigChoiceCard(
            title: 'C. Research Advising and Mentorship',
            body: 'Advising, panel, and mentorship achievements (max 10 pts).',
            icon: Icons.groups_outlined,
            selected: _crit?.id == 'kra-I-C',
            onTap: () => pick(critC),
            textScale: textScale,
          ),
      ],
    );
  }

  Widget _buildCriterionAChoices(TextScaler textScale) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          'What are you uploading?',
          style: TextStyle(fontSize: textScale.scale(18), fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 12),
        _bigChoiceCard(
          title: UiStrings.setSefEvalCardTitle,
          body: UiStrings.setSefEvalCardBody,
          icon: Icons.picture_as_pdf_outlined,
          selected: _criterionAChoice == _CriterionADocChoice.setSef,
          onTap: () => _selectCriterionAChoice(_CriterionADocChoice.setSef),
          textScale: textScale,
        ),
        const SizedBox(height: 12),
        _bigChoiceCard(
          title: UiStrings.specialStatusCardTitle,
          body: UiStrings.specialStatusCardBody,
          icon: Icons.folder_open_outlined,
          selected: _criterionAChoice == _CriterionADocChoice.special,
          onTap: () => _selectCriterionAChoice(_CriterionADocChoice.special),
          textScale: textScale,
        ),
      ],
    );
  }

  String get _compactStepLabel {
    if (_isTeachingCriterionA && _skipKraCriterionSteps) {
      switch (_step) {
        case 0:
          return 'Document type';
        case 1:
          return 'Add file';
        default:
          return 'Check and send';
      }
    }
    if (_isTeachingCriterionA && !_skipKraCriterionSteps) {
      switch (_step) {
        case 0:
          return 'Assessment area';
        case 1:
          return 'Document type';
        case 2:
          return 'Add file';
        default:
          return 'Check and send';
      }
    }
    switch (_step) {
      case 0:
        return 'Assessment area';
      case 1:
        return 'Criterion & indicator';
      case 2:
        return _isAchievementCriterion ? 'Achievement' : 'Add file';
      default:
        return 'Check and send';
    }
  }

  Widget _activeStepBody(TextScaler textScale) {
    if (_isTeachingCriterionA && _skipKraCriterionSteps) {
      if (_step == 0) return _buildCriterionAChoices(textScale);
      if (_step == _fileStepIndex) return _fileStepContent(textScale);
      return _reviewStepContent(textScale);
    }
    if (_isTeachingCriterionA && !_skipKraCriterionSteps) {
      if (_step == 0) return _kraStepContent(textScale);
      if (_step == 1) {
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (_kra != null)
              Text(
                _crit?.name ?? 'Criterion A – Teaching Effectiveness',
                style: TextStyle(fontSize: textScale.scale(16), fontWeight: FontWeight.w600),
              ),
            const SizedBox(height: 12),
            _buildCriterionAChoices(textScale),
          ],
        );
      }
      if (_step == _fileStepIndex) return _fileStepContent(textScale);
      return _reviewStepContent(textScale);
    }
    if (_step == 0) return _kraStepContent(textScale);
    if (_step == 1) return _criterionIndicatorStep(textScale);
    if (_step == _fileStepIndex) return _fileStepContent(textScale);
    return _reviewStepContent(textScale);
  }

  Widget _kraStepContent(TextScaler textScale) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        DropdownButtonFormField<KraNode>(
          isExpanded: true,
          value: _kra,
          decoration: const InputDecoration(labelText: 'KRA (Key Result Area)'),
          items: widget.repo.catalogKras
              .map((k) => DropdownMenuItem(value: k, child: Text(k.shortDropdownLabel, softWrap: true)))
              .toList(),
          onChanged: (v) {
            setState(() {
              _kra = v;
              _crit = null;
              _ind = null;
              _criterionAChoice = null;
            });
            _scrollActiveStepToTop();
          },
        ),
      ],
    );
  }

  Widget _criterionIndicatorStep(TextScaler textScale) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (_kra == null) const Text('Go back and choose a KRA first.'),
        if (_kra != null && _kra!.id == 'kra-I') ...[
          _buildKraICriterionPicker(textScale),
          if (_isTeachingCriterionA) ...[
            const SizedBox(height: 16),
            _buildCriterionAChoices(textScale),
          ],
          if (_isAchievementCriterion && _crit != null) ...[
            const SizedBox(height: 16),
            DropdownButtonFormField<IndicatorNode>(
              isExpanded: true,
              initialValue: _ind,
              decoration: const InputDecoration(labelText: 'Indicator'),
              items: scoringIndicatorsForCriterion(_crit!)
                  .where((i) => i.type != 'set_sef')
                  .map((i) => DropdownMenuItem(value: i, child: Text(i.name, softWrap: true)))
                  .toList(),
              onChanged: (v) => setState(() => _ind = v),
            ),
            const SizedBox(height: 8),
            Text(
              'Opens the achievement form: upload evidence there so files stay linked to your claim.',
              style: TextStyle(fontSize: textScale.scale(15), color: AppColors.textMuted, height: 1.45),
            ),
          ],
        ] else if (_kra != null && _kra!.id == 'kra-II') ...[
          _buildKraIICriterionPicker(textScale),
          if (_isAchievementCriterion && _crit != null) ...[
            const SizedBox(height: 16),
            DropdownButtonFormField<IndicatorNode>(
              isExpanded: true,
              initialValue: _ind,
              decoration: const InputDecoration(labelText: 'Indicator'),
              items: scoringIndicatorsForCriterion(_crit!)
                  .map((i) => DropdownMenuItem(value: i, child: Text(i.name, softWrap: true)))
                  .toList(),
              onChanged: (v) => setState(() => _ind = v),
            ),
            const SizedBox(height: 8),
            Text(
              'Research, invention, and creative-work claims use the achievement form with supporting files.',
              style: TextStyle(fontSize: textScale.scale(15), color: AppColors.textMuted, height: 1.45),
            ),
          ],
        ] else if (_kra != null && _kra!.id == 'kra-IV') ...[
          _buildKraIVCriterionPicker(textScale),
          if (_isAchievementCriterion && _crit != null) ...[
            const SizedBox(height: 16),
            DropdownButtonFormField<IndicatorNode>(
              isExpanded: true,
              initialValue: _ind,
              decoration: const InputDecoration(labelText: 'Indicator'),
              items: scoringIndicatorsForCriterion(_crit!)
                  .map((i) => DropdownMenuItem(value: i, child: Text(i.name, softWrap: true)))
                  .toList(),
              onChanged: (v) => setState(() => _ind = v),
            ),
            const SizedBox(height: 8),
            Text(
              'Professional development claims use the achievement form with supporting files.',
              style: TextStyle(fontSize: textScale.scale(15), color: AppColors.textMuted, height: 1.45),
            ),
          ],
        ] else if (_kra != null && _kra!.id == 'kra-III') ...[
          _buildKraIIICriterionPicker(textScale),
          if (_isAchievementCriterion && _crit != null) ...[
            const SizedBox(height: 16),
            DropdownButtonFormField<IndicatorNode>(
              isExpanded: true,
              initialValue: _ind,
              decoration: const InputDecoration(labelText: 'Indicator'),
              items: scoringIndicatorsForCriterion(_crit!)
                  .map((i) => DropdownMenuItem(value: i, child: Text(i.name, softWrap: true)))
                  .toList(),
              onChanged: (v) => setState(() => _ind = v),
            ),
            const SizedBox(height: 8),
            Text(
              'Extension-service claims use the achievement form with supporting files.',
              style: TextStyle(fontSize: textScale.scale(15), color: AppColors.textMuted, height: 1.45),
            ),
          ],
        ] else if (_kra != null) ...[
          DropdownButtonFormField<CriterionNode>(
            isExpanded: true,
            initialValue: _crit,
            decoration: const InputDecoration(labelText: 'Criterion'),
            items: _kra!.criteria
                .map((c) => DropdownMenuItem(value: c, child: Text(c.name, softWrap: true)))
                .toList(),
            onChanged: (v) => setState(() {
              _crit = v;
              _ind = null;
              _criterionAChoice = null;
            }),
          ),
          if (_crit != null) ...[
            const SizedBox(height: 8),
            DropdownButtonFormField<IndicatorNode>(
              isExpanded: true,
              initialValue: _ind,
              decoration: const InputDecoration(labelText: 'Indicator'),
              items: _crit!.indicators
                  .where((i) => i.type != 'set_sef_combined_pdf' && i.type != 'set_sef_set_pdf' && i.type != 'set_sef_sef_pdf')
                  .map((i) => DropdownMenuItem(value: i, child: Text(i.name, softWrap: true)))
                  .toList(),
              onChanged: (v) => setState(() => _ind = v),
            ),
          ],
        ],
      ],
    );
  }

  Widget _fileStepContent(TextScaler textScale) {
    if (_isAchievementCriterion) {
      return Text(
        'Instructional materials and advising use the achievement form on step 2. Tap Back, then Open achievement.',
        style: TextStyle(fontSize: textScale.scale(16), color: AppColors.textMuted, height: 1.45),
      );
    }
    final pdfOnly = _isSetSefOcrPdf;
    final busy = _pickingFile || _capturingPhoto || _uploading;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (_isTeachingCriterionA)
          Text(
            _documentCategoryLabel,
            style: TextStyle(fontSize: textScale.scale(16), fontWeight: FontWeight.w600),
          ),
        const SizedBox(height: 12),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            Semantics(
              button: true,
              label: 'Choose file from device',
              child: SizedBox(
                height: 52,
                child: FilledButton.icon(
                  onPressed: busy ? null : _pickFile,
                  icon: _pickingFile
                      ? const SizedBox(
                          width: 22,
                          height: 22,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                        )
                      : const Icon(Icons.attach_file, size: 26),
                  label: Text(
                    _pickingFile
                        ? 'Reading file…'
                        : (_fileName != null && !_selectedFile!.fromCamera
                            ? _fileName!
                            : (pdfOnly ? 'Choose PDF' : UiStrings.chooseFileLabel)),
                    overflow: TextOverflow.ellipsis,
                    maxLines: 2,
                  ),
                ),
              ),
            ),
            if (!pdfOnly)
              Semantics(
                button: true,
                label: 'Take photo with camera',
                child: SizedBox(
                  height: 52,
                  child: OutlinedButton.icon(
                    onPressed: busy ? null : _takePhoto,
                    icon: _capturingPhoto
                        ? const SizedBox(
                            width: 22,
                            height: 22,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.photo_camera_outlined, size: 26),
                    label: Text(
                      _capturingPhoto
                          ? 'Opening camera…'
                          : (_selectedFile?.fromCamera == true ? (_fileName ?? UiStrings.takePhotoLabel) : UiStrings.takePhotoLabel),
                      overflow: TextOverflow.ellipsis,
                      maxLines: 2,
                    ),
                  ),
                ),
              ),
          ],
        ),
        if (pdfOnly) ...[
          const SizedBox(height: 8),
          Text(
            UiStrings.setSefCameraNotSupported,
            style: TextStyle(fontSize: textScale.scale(14), color: AppColors.textMuted, height: 1.4),
          ),
        ],
        if (_hasReadableFile) ...[
          const SizedBox(height: 8),
          if (_selectedFile!.isImage)
            ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: Image.memory(
                Uint8List.fromList(_selectedFile!.bytes),
                height: 140,
                fit: BoxFit.contain,
                errorBuilder: (context, error, stackTrace) => const SizedBox.shrink(),
              ),
            ),
          const SizedBox(height: 8),
          Text(
            '${_selectedFile!.fromCamera ? 'Photo ready' : 'Ready'} · '
            '${(_selectedFile!.sizeBytes / 1024).toStringAsFixed(1)} KB'
            '${_fileName != null ? ' · $_fileName' : ''}',
            style: TextStyle(fontSize: textScale.scale(14), color: AppColors.success, fontWeight: FontWeight.w600),
          ),
        ],
        const SizedBox(height: 12),
        Text(
          pdfOnly ? UiStrings.setSefUploadHint : UiStrings.uploadPdfServerNote,
          style: TextStyle(fontSize: textScale.scale(15), color: AppColors.textMuted, height: 1.45),
        ),
        const SizedBox(height: 16),
        TextField(
          controller: _title,
          decoration: const InputDecoration(
            labelText: 'Short description (optional)',
          ),
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
    );
  }

  Widget _reviewStepContent(TextScaler textScale) {
    if (_isAchievementCriterion) {
      return Text(
        'Complete draft or submit from the achievement screen.',
        style: TextStyle(fontSize: textScale.scale(16), color: AppColors.textMuted),
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(_breadcrumb, style: TextStyle(fontSize: textScale.scale(15), fontWeight: FontWeight.w600)),
        const SizedBox(height: 12),
        Text('Document type: $_documentCategoryLabel', style: TextStyle(fontSize: textScale.scale(16))),
        const SizedBox(height: 6),
        Text(
          'File: ${_hasReadableFile ? _fileName! : (_fileName ?? "—")}'
          '${_selectedFile?.fromCamera == true ? ' (camera photo)' : ''}',
          style: TextStyle(fontSize: textScale.scale(16)),
        ),
        if (_hasReadableFile)
          Text(
            'Size: ${(_selectedFile!.sizeBytes / 1024).toStringAsFixed(1)} KB',
            style: TextStyle(fontSize: textScale.scale(15), color: AppColors.textMuted),
          )
        else if (_fileName != null)
          Text(
            'The selected file could not be read. Please select it again.',
            style: TextStyle(fontSize: textScale.scale(15), color: AppColors.amberText, height: 1.4),
          ),
        Text(
          'Description: ${_title.text.isEmpty ? "—" : _title.text}',
          style: TextStyle(fontSize: textScale.scale(16)),
        ),
        const SizedBox(height: 12),
        Text(
          _isSetSefOcrPdf
              ? 'We will read semesters from your PDF. Your reviewer checks names and scores before they count toward your assessment.'
              : 'Your reviewer will check this document against the published rules.',
          style: TextStyle(fontSize: textScale.scale(15), height: 1.45, color: AppColors.textMuted),
        ),
      ],
    );
  }

  Widget _compactHeader(TextScaler textScale) {
    final kraLabel = _kra?.shortDropdownLabel;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (kraLabel != null)
          Text(
            kraLabel,
            style: TextStyle(
              fontSize: textScale.scale(15),
              fontWeight: FontWeight.w600,
              color: AppColors.textNavy,
            ),
          ),
        const SizedBox(height: 2),
        Text(
          'Step ${_step + 1} of $_stepCount · $_compactStepLabel',
          style: TextStyle(
            fontSize: textScale.scale(14),
            fontWeight: FontWeight.w700,
            color: AppColors.primaryBlue,
          ),
        ),
        const SizedBox(height: 8),
        ClipRRect(
          borderRadius: BorderRadius.circular(8),
          child: LinearProgressIndicator(
            value: (_step + 1) / _stepCount,
            minHeight: 6,
            backgroundColor: AppColors.border,
            color: AppColors.primaryBlue,
          ),
        ),
      ],
    );
  }

  Widget _stepControls() {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: [
        if (_step > 0)
          TextButton(onPressed: _uploading ? null : _back, child: const Text('Back')),
        if (_step < _reviewStepIndex)
          FilledButton(
            onPressed: _uploading ? null : _continue,
            child: Text(_isAchievementCriterion && _step == 1 ? 'Open achievement' : 'Continue'),
          ),
        if (_step == _reviewStepIndex && !_isAchievementCriterion)
          FilledButton(
            onPressed: (_uploading || !_hasReadableFile) ? null : _submit,
            child: _uploading
                ? const SizedBox(
                    width: 22,
                    height: 22,
                    child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                  )
                : const Text('Send for review'),
          ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    final textScale = MediaQuery.textScalerOf(context);
    final safeBottom = MediaQuery.paddingOf(context).bottom;
    final keyboard = MediaQuery.viewInsetsOf(context).bottom;

    return Scaffold(
      resizeToAvoidBottomInset: true,
      appBar: AppBar(
        title: const Text('Add document'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          tooltip: 'Back',
          onPressed: () => Navigator.maybePop(context),
        ),
      ),
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 10, 16, 8),
            child: _compactHeader(textScale),
          ),
          const Divider(height: 1),
          Expanded(
            child: SingleChildScrollView(
              controller: _scrollController,
              physics: const AlwaysScrollableScrollPhysics(),
              keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
              padding: EdgeInsets.fromLTRB(16, 12, 16, 24 + safeBottom + keyboard),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  _activeStepBody(textScale),
                  const SizedBox(height: 20),
                  _stepControls(),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
