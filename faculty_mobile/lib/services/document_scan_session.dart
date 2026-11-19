import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:image/image.dart' as img;

import '../theme/app_theme.dart';
import 'camera_document_capture.dart';
import 'selected_upload_file.dart';

/// Ordered camera pages for one document upload (SET/SEF or general evidence).
class DocumentScanSession {
  DocumentScanSession({CameraDocumentCapture? camera})
      : _camera = camera ?? CameraDocumentCapture();

  final CameraDocumentCapture _camera;
  final List<SelectedUploadFile> pages = [];

  bool get isEmpty => pages.isEmpty;
  int get length => pages.length;

  Future<void> captureAndAdd(BuildContext context) async {
    while (context.mounted) {
      final captured = await _camera.captureDocumentPhoto();
      if (!context.mounted) return;
      if (captured == null) return; // cancelled

      final confirmed = await showScanPagePreview(
        context,
        bytes: Uint8List.fromList(captured.bytes),
        filename: captured.filename,
        pageNumber: pages.length + 1,
      );
      if (!context.mounted) return;
      if (confirmed == null) return; // dismissed
      if (confirmed.retake) continue;

      pages.add(
        SelectedUploadFile(
          filename: captured.filename,
          bytes: confirmed.bytes,
          mimeType: 'image/jpeg',
          source: UploadFileSource.camera,
        ),
      );
      return;
    }
  }

  void removeAt(int index) {
    if (index < 0 || index >= pages.length) return;
    pages.removeAt(index);
  }

  void reorder(int oldIndex, int newIndex) {
    if (oldIndex < 0 || oldIndex >= pages.length) return;
    if (newIndex < 0 || newIndex > pages.length) return;
    var target = newIndex;
    if (target > oldIndex) target -= 1;
    final item = pages.removeAt(oldIndex);
    pages.insert(target, item);
  }

  Future<void> rotateAt(int index, {int quarterTurns = 1}) async {
    if (index < 0 || index >= pages.length) return;
    final page = pages[index];
    final decoded = img.decodeImage(Uint8List.fromList(page.bytes));
    if (decoded == null) {
      throw CameraCaptureException('Could not rotate this page. Try retaking it.');
    }
    var rotated = decoded;
    for (var i = 0; i < quarterTurns; i++) {
      rotated = img.copyRotate(rotated, angle: 90);
    }
    final encoded = img.encodeJpg(rotated, quality: 88);
    pages[index] = SelectedUploadFile(
      filename: page.filename,
      bytes: encoded,
      mimeType: 'image/jpeg',
      source: UploadFileSource.camera,
    );
  }

  /// Single file when one page; otherwise multi-page camera scan.
  SelectedUploadFile? asSingleFileOrNull() {
    if (pages.isEmpty) return null;
    if (pages.length == 1) return pages.first;
    return null;
  }
}

class ScanPreviewResult {
  final bool retake;
  final List<int> bytes;
  const ScanPreviewResult({required this.retake, required this.bytes});
}

/// Preview with rotate / retake / use page.
Future<ScanPreviewResult?> showScanPagePreview(
  BuildContext context, {
  required Uint8List bytes,
  required String filename,
  required int pageNumber,
}) {
  return showDialog<ScanPreviewResult>(
    context: context,
    barrierDismissible: false,
    builder: (ctx) => _ScanPagePreviewDialog(
      initialBytes: bytes,
      filename: filename,
      pageNumber: pageNumber,
    ),
  );
}

class _ScanPagePreviewDialog extends StatefulWidget {
  final Uint8List initialBytes;
  final String filename;
  final int pageNumber;

  const _ScanPagePreviewDialog({
    required this.initialBytes,
    required this.filename,
    required this.pageNumber,
  });

  @override
  State<_ScanPagePreviewDialog> createState() => _ScanPagePreviewDialogState();
}

class _ScanPagePreviewDialogState extends State<_ScanPagePreviewDialog> {
  late Uint8List _bytes;
  int _turns = 0;

  @override
  void initState() {
    super.initState();
    _bytes = widget.initialBytes;
  }

  Future<void> _rotate() async {
    final decoded = img.decodeImage(_bytes);
    if (decoded == null) return;
    final rotated = img.copyRotate(decoded, angle: 90);
    setState(() {
      _bytes = Uint8List.fromList(img.encodeJpg(rotated, quality: 88));
      _turns = (_turns + 1) % 4;
    });
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text('Page ${widget.pageNumber}'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: Image.memory(
                _bytes,
                fit: BoxFit.contain,
                height: 280,
                errorBuilder: (context, error, stackTrace) => const SizedBox(
                  height: 120,
                  child: Center(child: Text('Could not preview image')),
                ),
              ),
            ),
            const SizedBox(height: 10),
            Text(
              widget.filename,
              style: const TextStyle(fontSize: 13, color: AppColors.textMuted),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 6),
            const Text(
              'Check that all text is clear and readable before continuing.',
              style: TextStyle(fontSize: 13, height: 1.35),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context, const ScanPreviewResult(retake: true, bytes: [])),
          child: const Text('Retake'),
        ),
        TextButton(
          onPressed: _rotate,
          child: Text(_turns == 0 ? 'Rotate' : 'Rotate (${_turns * 90}°)'),
        ),
        FilledButton(
          onPressed: () => Navigator.pop(
            context,
            ScanPreviewResult(retake: false, bytes: _bytes),
          ),
          child: const Text('Use page'),
        ),
      ],
    );
  }
}

/// Full-screen-ish sheet to review multi-page scan before upload.
Future<bool?> showScanSessionEditor(
  BuildContext context, {
  required DocumentScanSession session,
}) {
  return showModalBottomSheet<bool>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    builder: (ctx) {
      return StatefulBuilder(
        builder: (context, setModalState) {
          return Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  'Scanned pages (${session.length})',
                  style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 8),
                const Text(
                  'Add, remove, reorder, or rotate pages. All pages upload as one document.',
                  style: TextStyle(fontSize: 14, color: AppColors.textMuted, height: 1.4),
                ),
                const SizedBox(height: 12),
                SizedBox(
                  height: 220,
                  child: session.isEmpty
                      ? const Center(child: Text('No pages yet'))
                      : ReorderableListView.builder(
                          itemCount: session.length,
                          onReorder: (oldIndex, newIndex) {
                            setModalState(() => session.reorder(oldIndex, newIndex));
                          },
                          itemBuilder: (context, index) {
                            final page = session.pages[index];
                            return ListTile(
                              key: ValueKey('scan-page-$index-${page.filename}'),
                              leading: ClipRRect(
                                borderRadius: BorderRadius.circular(6),
                                child: Image.memory(
                                  Uint8List.fromList(page.bytes),
                                  width: 48,
                                  height: 48,
                                  fit: BoxFit.cover,
                                ),
                              ),
                              title: Text('Page ${index + 1}'),
                              subtitle: Text(page.filename, maxLines: 1, overflow: TextOverflow.ellipsis),
                              trailing: Wrap(
                                spacing: 0,
                                children: [
                                  IconButton(
                                    tooltip: 'Rotate',
                                    icon: const Icon(Icons.rotate_90_degrees_ccw),
                                    onPressed: () async {
                                      try {
                                        await session.rotateAt(index);
                                        setModalState(() {});
                                      } catch (e) {
                                        if (context.mounted) {
                                          ScaffoldMessenger.of(context).showSnackBar(
                                            SnackBar(content: Text('$e')),
                                          );
                                        }
                                      }
                                    },
                                  ),
                                  IconButton(
                                    tooltip: 'Remove',
                                    icon: const Icon(Icons.delete_outline),
                                    onPressed: () => setModalState(() => session.removeAt(index)),
                                  ),
                                  const Icon(Icons.drag_handle),
                                ],
                              ),
                            );
                          },
                        ),
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    OutlinedButton.icon(
                      onPressed: () async {
                        try {
                          await session.captureAndAdd(context);
                          setModalState(() {});
                        } on CameraCaptureException catch (e) {
                          if (context.mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
                          }
                        }
                      },
                      icon: const Icon(Icons.add_a_photo_outlined),
                      label: const Text('Add page'),
                    ),
                    TextButton(
                      onPressed: () => Navigator.pop(context, false),
                      child: const Text('Cancel'),
                    ),
                    FilledButton(
                      onPressed: session.isEmpty ? null : () => Navigator.pop(context, true),
                      child: const Text('Use scan'),
                    ),
                  ],
                ),
              ],
            ),
          );
        },
      );
    },
  );
}
