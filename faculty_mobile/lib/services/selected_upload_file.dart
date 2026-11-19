import 'package:file_picker/file_picker.dart';

import 'achievement_attachment_upload.dart';

/// How the faculty selected the bytes retained for upload / retry.
enum UploadFileSource { filePicker, camera }

/// One selected file used by both the review summary and multipart upload.
class SelectedUploadFile {
  final String filename;
  final List<int> bytes;
  final String mimeType;
  final UploadFileSource source;

  const SelectedUploadFile({
    required this.filename,
    required this.bytes,
    required this.mimeType,
    this.source = UploadFileSource.filePicker,
  });

  bool get isReadable => bytes.isNotEmpty;

  int get sizeBytes => bytes.length;

  bool get isImage =>
      mimeType.startsWith('image/') ||
      filename.toLowerCase().endsWith('.jpg') ||
      filename.toLowerCase().endsWith('.jpeg') ||
      filename.toLowerCase().endsWith('.png') ||
      filename.toLowerCase().endsWith('.webp');

  bool get fromCamera => source == UploadFileSource.camera;
}

/// One document upload selection (single file or multi-page camera scan).
class PendingDocumentUpload {
  final List<SelectedUploadFile> pages;

  const PendingDocumentUpload(this.pages);

  factory PendingDocumentUpload.single(SelectedUploadFile file) =>
      PendingDocumentUpload([file]);

  factory PendingDocumentUpload.scanPages(List<SelectedUploadFile> pages) {
    assert(pages.isNotEmpty);
    return PendingDocumentUpload(List<SelectedUploadFile>.unmodifiable(pages));
  }

  bool get isEmpty => pages.isEmpty;
  bool get isReadable => pages.isNotEmpty && pages.every((p) => p.isReadable);
  bool get isMultiPage => pages.length > 1;
  bool get fromCamera => pages.isNotEmpty && pages.every((p) => p.fromCamera);
  bool get isImage => pages.length == 1 && pages.first.isImage;
  SelectedUploadFile get primary => pages.first;

  String get displayName {
    if (pages.isEmpty) return '';
    if (isMultiPage) return '${pages.length}-page scan';
    return pages.first.filename;
  }

  int get sizeBytes => pages.fold(0, (sum, p) => sum + p.sizeBytes);

  /// Multipart: one `file` when single page; repeated `pages` when multi-page scan.
  bool get uploadAsPagesField => isMultiPage;

  String get sizeLabel {
    if (sizeBytes <= 0) return '';
    if (sizeBytes < 1024) return '$sizeBytes B';
    if (sizeBytes < 1024 * 1024) return '${(sizeBytes / 1024).toStringAsFixed(1)} KB';
    return '${(sizeBytes / (1024 * 1024)).toStringAsFixed(2)} MB';
  }

  /// Rough duplicate check (name + size) for append-without-replace sessions.
  bool sameContentAs(PendingDocumentUpload other) {
    if (pages.length != other.pages.length) return false;
    if (sizeBytes != other.sizeBytes) return false;
    if (displayName != other.displayName) return false;
    return true;
  }
}

enum UploadSessionItemStatus { pending, uploading, uploaded, failed }

/// One document in a multi-file upload session (file or multi-page scan).
class UploadSessionItem {
  final String localKey;
  final PendingDocumentUpload document;
  UploadSessionItemStatus status;
  String? publicId;
  String? errorMessage;
  double progress;

  UploadSessionItem({
    required this.localKey,
    required this.document,
    this.status = UploadSessionItemStatus.pending,
    this.publicId,
    this.errorMessage,
    this.progress = 0,
  });

  bool get isReadable => document.isReadable;
  bool get needsUpload =>
      status == UploadSessionItemStatus.pending || status == UploadSessionItemStatus.failed;
  bool get isUploaded => status == UploadSessionItemStatus.uploaded && (publicId?.isNotEmpty ?? false);
}

String newUploadSessionLocalKey(String seed) =>
    'up-${DateTime.now().microsecondsSinceEpoch}-${seed.hashCode}';

/// Reads a [PlatformFile] for upload.
///
/// On Android, [PlatformFile.bytes] is often null unless `withData: true` was
/// passed to [FilePicker.platform.pickFiles]. Prefer that flag, then fall back
/// to [PlatformFile.xFile] (content URI / file-provider) without assuming a
/// filesystem path.
Future<SelectedUploadFile?> readPlatformFileForUpload(PlatformFile file) async {
  final name = file.name.trim();
  if (name.isEmpty) return null;

  List<int>? bytes = file.bytes;
  if (bytes == null || bytes.isEmpty) {
    try {
      bytes = await file.xFile.readAsBytes();
    } catch (_) {
      bytes = null;
    }
  }

  if (bytes == null || bytes.isEmpty) return null;

  return SelectedUploadFile(
    filename: name,
    bytes: bytes,
    mimeType: mimeForExtension(file.extension),
    source: UploadFileSource.filePicker,
  );
}
