import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import '../core/ui_strings.dart';
import '../services/achievement_attachment_upload.dart';
import '../services/camera_document_capture.dart';
import '../theme/app_theme.dart';

class AchievementAttachmentsPanel extends StatefulWidget {
  final List<AchievementAttachment> attachments;
  final void Function(List<AchievementAttachment>) onChanged;
  final String indicatorId;
  final String kraId;
  final String? titleHint;

  const AchievementAttachmentsPanel({
    super.key,
    required this.attachments,
    required this.onChanged,
    required this.indicatorId,
    required this.kraId,
    this.titleHint,
  });

  @override
  State<AchievementAttachmentsPanel> createState() => _AchievementAttachmentsPanelState();
}

class _AchievementAttachmentsPanelState extends State<AchievementAttachmentsPanel> {
  bool _busy = false;
  final _cameraCapture = CameraDocumentCapture();

  Future<void> _pickMore() async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      final pick = await FilePicker.platform.pickFiles(
        allowMultiple: true,
        withData: true,
        type: FileType.custom,
        allowedExtensions: kAllowedUploadExtensions.toList(),
      );
      if (pick == null || pick.files.isEmpty) return;
      final next = List<AchievementAttachment>.from(widget.attachments);
      for (final f in pick.files) {
        if (f.bytes == null) continue;
        final err = validatePickedFile(filename: f.name, size: f.size, extension: f.extension);
        if (err != null) {
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$err (${f.name})')));
          }
          continue;
        }
        final dup = next.any(
          (a) =>
              a.filename == f.name &&
              a.sizeBytes == f.size &&
              (a.status == AchievementAttachmentStatus.uploaded || a.bytes.length == f.bytes!.length),
        );
        if (dup) continue;
        next.add(
          AchievementAttachment(
            localKey: 'local-${DateTime.now().microsecondsSinceEpoch}-${f.name.hashCode}',
            filename: f.name,
            sizeBytes: f.size,
            bytes: f.bytes!,
            mimeType: mimeForExtension(f.extension),
          ),
        );
      }
      widget.onChanged(next);
      setState(() {});
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _takePhoto() async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      while (mounted) {
        final captured = await _cameraCapture.captureDocumentPhoto();
        if (!mounted) return;
        if (captured == null) return;
        final keep = await showCapturedPhotoPreview(
          context,
          bytes: Uint8List.fromList(captured.bytes),
          filename: captured.filename,
        );
        if (!mounted) return;
        if (keep == true) {
          final next = List<AchievementAttachment>.from(widget.attachments);
          next.add(
            AchievementAttachment(
              localKey: 'local-${DateTime.now().microsecondsSinceEpoch}-camera',
              filename: captured.filename,
              sizeBytes: captured.sizeBytes,
              bytes: Uint8List.fromList(captured.bytes),
              mimeType: captured.mimeType,
            ),
          );
          widget.onChanged(next);
          setState(() {});
          return;
        }
        if (keep == null) return;
      }
    } on CameraCaptureException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Could not capture a photo. Please try again.')),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _uploadOne(AchievementAttachment item) async {
    setState(() {});
    try {
      await uploadAchievementAttachment(
        item: item,
        indicatorId: widget.indicatorId,
        kraId: widget.kraId,
        title: widget.titleHint,
      );
    } catch (_) {
      // status set on item
    }
    widget.onChanged(List.from(widget.attachments));
    setState(() {});
  }

  bool get hasUnresolved =>
      widget.attachments.any((a) => a.blocksSubmit) || widget.attachments.isEmpty;

  List<String> get uploadedDocumentIds => widget.attachments
      .where((a) => a.documentPublicId != null)
      .map((a) => a.documentPublicId!)
      .toList();

  void _remove(AchievementAttachment item) {
    final next = widget.attachments.where((a) => a.localKey != item.localKey).toList();
    widget.onChanged(next);
    setState(() {});
  }

  String _statusLabel(AchievementAttachment a) {
    switch (a.status) {
      case AchievementAttachmentStatus.selected:
        return 'Not uploaded yet';
      case AchievementAttachmentStatus.uploading:
        return 'Uploading…';
      case AchievementAttachmentStatus.uploaded:
        return 'Uploaded';
      case AchievementAttachmentStatus.failed:
        return 'Failed';
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          'Supporting documents (${widget.attachments.length})',
          style: const TextStyle(fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 4),
        const Text(
          'All files attach to this one achievement. Points are not multiplied by file count.',
          style: TextStyle(fontSize: 14, color: AppColors.textMuted, height: 1.35),
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            OutlinedButton.icon(
              onPressed: _busy ? null : _pickMore,
              icon: const Icon(Icons.upload_file),
              label: Text(widget.attachments.isEmpty ? 'Choose files' : 'Add more files'),
            ),
            OutlinedButton.icon(
              onPressed: _busy ? null : _takePhoto,
              icon: const Icon(Icons.photo_camera_outlined),
              label: const Text(UiStrings.takePhotoLabel),
            ),
          ],
        ),
        const SizedBox(height: 8),
        ...widget.attachments.map(
          (a) => Card(
            margin: const EdgeInsets.only(bottom: 8),
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(a.filename, style: const TextStyle(fontWeight: FontWeight.w600)),
                  Text(
                    a.sizeLabel.isEmpty ? _statusLabel(a) : '${a.sizeLabel} · ${_statusLabel(a)}',
                  ),
                  if (a.status == AchievementAttachmentStatus.uploading)
                    Padding(
                      padding: const EdgeInsets.only(top: 6),
                      child: LinearProgressIndicator(value: a.progress > 0 ? a.progress : null),
                    ),
                  if (a.errorMessage != null)
                    Text(a.errorMessage!, style: const TextStyle(color: Colors.red, fontSize: 13)),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    children: [
                      if (a.status == AchievementAttachmentStatus.selected ||
                          a.status == AchievementAttachmentStatus.failed)
                        FilledButton.tonal(
                          onPressed: () => _uploadOne(a),
                          child: Text(a.status == AchievementAttachmentStatus.failed ? 'Retry' : 'Upload'),
                        ),
                      TextButton(onPressed: () => _remove(a), child: const Text('Remove')),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),
        if (widget.attachments.isEmpty)
          const Text('At least one supporting document is required before submit.', style: TextStyle(color: AppColors.textMuted)),
      ],
    );
  }
}
