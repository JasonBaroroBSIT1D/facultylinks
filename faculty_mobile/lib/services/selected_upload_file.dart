import 'package:file_picker/file_picker.dart';

import 'achievement_attachment_upload.dart';

/// One selected file used by both the review summary and multipart upload.
class SelectedUploadFile {
  final String filename;
  final List<int> bytes;
  final String mimeType;

  const SelectedUploadFile({
    required this.filename,
    required this.bytes,
    required this.mimeType,
  });

  bool get isReadable => bytes.isNotEmpty;

  int get sizeBytes => bytes.length;
}

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
  );
}
