import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:image_picker/image_picker.dart';

import 'achievement_attachment_upload.dart';
import 'selected_upload_file.dart';

/// Camera capture for document photos (not a document scanner — no auto-crop).
class CameraDocumentCapture {
  CameraDocumentCapture({ImagePicker? picker}) : _picker = picker ?? ImagePicker();

  final ImagePicker _picker;

  /// Opens the device camera. Returns null when the user cancels.
  ///
  /// Uses moderate JPEG compression and a max width so photos stay readable
  /// for OCR without exceeding upload limits. Orientation is applied by
  /// [image_picker] when reading image bytes.
  Future<SelectedUploadFile?> captureDocumentPhoto() async {
    try {
      final shot = await _picker.pickImage(
        source: ImageSource.camera,
        preferredCameraDevice: CameraDevice.rear,
        imageQuality: 85,
        maxWidth: 2500,
        requestFullMetadata: true,
      );
      if (shot == null) return null;

      final bytes = await shot.readAsBytes();
      if (bytes.isEmpty) {
        throw CameraCaptureException('The camera photo could not be read. Please try again.');
      }

      final rawName = shot.name.trim().isNotEmpty ? shot.name.trim() : 'document_photo.jpg';
      final filename = _ensureJpegName(rawName);
      final err = validatePickedFile(
        filename: filename,
        size: bytes.length,
        extension: 'jpg',
      );
      if (err != null) {
        throw CameraCaptureException(err);
      }

      return SelectedUploadFile(
        filename: filename,
        bytes: bytes,
        mimeType: 'image/jpeg',
        source: UploadFileSource.camera,
      );
    } on CameraCaptureException {
      rethrow;
    } on PlatformException catch (e) {
      final code = (e.code).toLowerCase();
      if (code.contains('camera') && (code.contains('denied') || code.contains('permission'))) {
        throw CameraCaptureException(
          'Camera permission is required to take a photo. Enable it in system settings, then try again.',
        );
      }
      if (code.contains('photo') && (code.contains('access') || code.contains('denied') || code.contains('permission'))) {
        throw CameraCaptureException(
          'Camera permission is required to take a photo. Enable it in system settings, then try again.',
        );
      }
      throw CameraCaptureException(
        e.message?.trim().isNotEmpty == true
            ? e.message!.trim()
            : 'Could not open the camera. Please try again.',
      );
    } catch (e) {
      if (e is CameraCaptureException) rethrow;
      throw CameraCaptureException('Could not capture a photo. Please try again.');
    }
  }
}

class CameraCaptureException implements Exception {
  CameraCaptureException(this.message);
  final String message;

  @override
  String toString() => message;
}

String _ensureJpegName(String name) {
  final lower = name.toLowerCase();
  if (lower.endsWith('.jpg') || lower.endsWith('.jpeg')) return name;
  final stamp = DateTime.now().toIso8601String().replaceAll(':', '').replaceAll('.', '');
  return 'document_photo_$stamp.jpg';
}

/// Preview dialog: Retake / Use photo. Returns true to keep, false to retake, null if dismissed.
Future<bool?> showCapturedPhotoPreview(
  BuildContext context, {
  required Uint8List bytes,
  required String filename,
}) {
  return showDialog<bool>(
    context: context,
    barrierDismissible: false,
    builder: (ctx) {
      return AlertDialog(
        title: const Text('Use this photo?'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: Image.memory(
                  bytes,
                  fit: BoxFit.contain,
                  height: 280,
                  errorBuilder: (context, error, stackTrace) => const SizedBox(
                    height: 120,
                    child: Center(child: Text('Could not preview image')),
                  ),
                ),
              ),
              const SizedBox(height: 12),
              Text(
                filename,
                style: const TextStyle(fontSize: 13, color: Colors.black54),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
              const SizedBox(height: 8),
              const Text(
                'This is a camera photo of your document, not an automatic scan with edge detection or crop.',
                style: TextStyle(fontSize: 13, height: 1.35),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Retake'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Use photo'),
          ),
        ],
      );
    },
  );
}
