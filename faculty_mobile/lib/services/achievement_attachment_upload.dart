import 'dart:typed_data';

import '../services/document_api.dart';

/// Matches backend defaults (`MAX_UPLOAD_BYTES`, `ALLOWED_UPLOAD_MIME`).
const int kMaxUploadBytes = 20 * 1024 * 1024;
const kAllowedUploadExtensions = {'pdf', 'jpg', 'jpeg', 'png', 'webp'};

String mimeForExtension(String? ext) {
  switch (ext?.toLowerCase()) {
    case 'pdf':
      return 'application/pdf';
    case 'jpg':
    case 'jpeg':
      return 'image/jpeg';
    case 'png':
      return 'image/png';
    case 'webp':
      return 'image/webp';
    default:
      return 'application/octet-stream';
  }
}

String? validatePickedFile({required String filename, required int size, String? extension}) {
  final ext = (extension ?? filename.split('.').last).toLowerCase();
  if (!kAllowedUploadExtensions.contains(ext)) {
    return 'File type not allowed. Use PDF or image (JPEG, PNG, WebP).';
  }
  if (size <= 0) return 'File is empty.';
  if (size > kMaxUploadBytes) {
    return 'File exceeds ${(kMaxUploadBytes / (1024 * 1024)).toStringAsFixed(0)} MB limit.';
  }
  return null;
}

enum AchievementAttachmentStatus { selected, uploading, uploaded, failed }

class AchievementAttachment {
  final String localKey;
  final String filename;
  final int sizeBytes;
  final Uint8List bytes;
  final String mimeType;
  AchievementAttachmentStatus status;
  String? documentPublicId;
  String? errorMessage;
  double progress;

  AchievementAttachment({
    required this.localKey,
    required this.filename,
    required this.sizeBytes,
    required this.bytes,
    required this.mimeType,
    this.status = AchievementAttachmentStatus.selected,
    this.documentPublicId,
    this.errorMessage,
    this.progress = 0,
  });

  bool get isResolved => status == AchievementAttachmentStatus.uploaded;
  bool get blocksSubmit =>
      status == AchievementAttachmentStatus.selected ||
      status == AchievementAttachmentStatus.uploading ||
      status == AchievementAttachmentStatus.failed;

  String get sizeLabel {
    if (sizeBytes <= 0) return '';
    if (sizeBytes < 1024) return '$sizeBytes B';
    if (sizeBytes < 1024 * 1024) return '${(sizeBytes / 1024).toStringAsFixed(1)} KB';
    return '${(sizeBytes / (1024 * 1024)).toStringAsFixed(2)} MB';
  }
}

Future<void> uploadAllPendingAchievementAttachments({
  required List<AchievementAttachment> attachments,
  required String indicatorId,
  required String kraId,
  String? title,
}) async {
  for (final item in attachments) {
    if (item.status == AchievementAttachmentStatus.selected ||
        item.status == AchievementAttachmentStatus.failed) {
      await uploadAchievementAttachment(
        item: item,
        indicatorId: indicatorId,
        kraId: kraId,
        title: title,
      );
    }
  }
}

Future<void> uploadAchievementAttachment({
  required AchievementAttachment item,
  required String indicatorId,
  required String kraId,
  String? title,
}) async {
  item.status = AchievementAttachmentStatus.uploading;
  item.progress = 0.2;
  item.errorMessage = null;
  try {
    if (item.documentPublicId != null) {
      item.status = AchievementAttachmentStatus.uploaded;
      item.progress = 1;
      return;
    }
    final doc = await DocumentApi.upload(
      filename: item.filename,
      bytes: item.bytes,
      mimeType: item.mimeType,
      indicatorId: indicatorId,
      kraId: kraId,
      title: title,
    );
    item.progress = 0.85;
    var publicId = DocumentApi.publicIdFromUploadResponse(doc);
    publicId ??= await DocumentApi.reconcileStoredUpload(
      filename: item.filename,
      indicatorId: indicatorId,
      sizeBytes: item.sizeBytes,
    );
    if (publicId == null) {
      throw Exception('Upload succeeded but no document id returned.');
    }
    item.documentPublicId = publicId;
    item.status = AchievementAttachmentStatus.uploaded;
    item.progress = 1;
  } catch (e) {
    item.status = AchievementAttachmentStatus.failed;
    item.errorMessage = e.toString().replaceFirst('Exception: ', '');
    item.progress = 0;
    rethrow;
  }
}
