import 'dart:convert';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../services/api_client.dart';
import '../services/document_api.dart';
import '../theme/app_theme.dart';

class UploadSetSefScreen extends StatefulWidget {
  const UploadSetSefScreen({super.key});

  @override
  State<UploadSetSefScreen> createState() => _UploadSetSefScreenState();
}

class _UploadSetSefScreenState extends State<UploadSetSefScreen> {
  bool _loading = false;
  String? _error;
  Map<String, dynamic>? _lastDoc;
  Map<String, dynamic>? _extraction;

  Future<void> _pickAndUpload() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: const ['pdf'],
        withData: true,
      );
      if (result == null || result.files.isEmpty) {
        setState(() => _loading = false);
        return;
      }
      final file = result.files.first;
      final bytes = file.bytes;
      if (bytes == null) {
        throw Exception('Could not read the PDF.');
      }
      final res = await DocumentApi.upload(
        bytes: bytes,
        filename: file.name,
        mimeType: 'application/pdf',
        indicatorId: 'kra-I-A-setsef-combined',
        kraId: 'kra-I-A',
        title: 'SET–SEF combined PDF',
      );
      final doc = res['document'] as Map<String, dynamic>?;
      setState(() {
        _lastDoc = doc;
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _loading = false;
        _error = e.toString().replaceFirst('Exception: ', '');
      });
    }
  }

  Future<void> _refreshStatus() async {
    final id = _lastDoc?['id'] as String?;
    if (id == null) return;
    setState(() => _loading = true);
    try {
      final res = await ApiClient.get('/api/documents/$id/set-sef');
      if (res.statusCode != 200) throw Exception('Could not load processing status.');
      final data = jsonDecode(res.body) as Map<String, dynamic>;
      setState(() {
        _extraction = data;
        _lastDoc = data['document'] as Map<String, dynamic>?;
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _loading = false;
        _error = e.toString();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final ocr = _lastDoc?['ocrStatus'] as String? ?? '';
    final proc = _lastDoc?['processingStatus'] as String? ?? '';
    final scoring = _extraction?['scoring'] as Map<String, dynamic>?;
    final est = scoring?['estimated'] as Map<String, dynamic>?;

    return Scaffold(
      appBar: AppBar(title: const Text('Upload SET–SEF PDF')),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text(
              'Upload one PDF that contains your combined Student Evaluation of Teachers (SET) '
              'and Supervisor’s Evaluation of Faculty (SEF). Processing runs in the background.',
              style: TextStyle(color: AppColors.textMuted, height: 1.4),
            ),
            const SizedBox(height: 16),
            FilledButton(
              onPressed: _loading ? null : _pickAndUpload,
              child: Text(_loading ? 'Working…' : 'Upload SET–SEF PDF'),
            ),
            if (_lastDoc != null) ...[
              const SizedBox(height: 16),
              Text('OCR: $ocr · Processing: $proc', style: const TextStyle(fontWeight: FontWeight.w600)),
              if (_lastDoc?['processingError'] != null && '${_lastDoc?['processingError']}'.isNotEmpty)
                Text('${_lastDoc?['processingError']}', style: const TextStyle(color: Color(0xFFC62828))),
              TextButton(onPressed: _refreshStatus, child: const Text('Refresh status')),
            ],
            if (est != null) ...[
              const SizedBox(height: 8),
              Text(
                est['incomplete'] == true
                    ? (est['incompleteReason'] as String? ?? 'Criterion A incomplete')
                    : 'Estimated Criterion A: ${est['criterionAPoints']} pts',
              ),
            ],
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(top: 12),
                child: Text(_error!, style: const TextStyle(color: Color(0xFFC62828))),
              ),
          ],
        ),
      ),
    );
  }
}
