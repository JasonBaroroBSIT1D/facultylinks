import 'package:flutter/material.dart';

import '../core/ui_strings.dart';
import '../repositories/mock_repository.dart';

class DocumentDetailScreen extends StatelessWidget {
  final FacultyDocument doc;
  final VoidCallback? onSave;
  const DocumentDetailScreen({super.key, required this.doc, this.onSave});

  @override
  Widget build(BuildContext context) {
    final status = UiStrings.docStatusLabel(doc.reviewStatus);
    return Scaffold(
      appBar: AppBar(
        title: const Text('Document details'),
        leading: BackButton(onPressed: () => Navigator.maybePop(context)),
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text(doc.fileName, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          Text('Status: $status', style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
          if (doc.reviewStatus == 'correction_requested')
            const Padding(
              padding: EdgeInsets.only(top: 8),
              child: Text(
                'Your reviewer requested changes. Read their comments below and upload an updated file.',
                style: TextStyle(fontSize: 15),
              ),
            ),
          if (doc.academicYear != null) Text('${doc.academicYear} ${doc.semester ?? ''}', style: const TextStyle(fontSize: 16)),
          const SizedBox(height: 20),
          Card(
            clipBehavior: Clip.antiAlias,
            child: ExpansionTile(
              title: const Text('Text read from file (demonstration)'),
              subtitle: const Text('This is simulated OCR help—not an approval.'),
              children: [
                Padding(
                  padding: const EdgeInsets.all(12),
                  child: Text(doc.ocrText, style: const TextStyle(fontSize: 14, height: 1.5)),
                ),
              ],
            ),
          ),
          if (doc.remarks != null) ...[
            const SizedBox(height: 12),
            const Text('Reviewer comments', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
            Text(doc.remarks!, style: const TextStyle(fontSize: 16, height: 1.5)),
          ],
        ],
      ),
    );
  }
}
