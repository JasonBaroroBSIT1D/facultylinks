import 'package:flutter/material.dart';

import '../../core/ui_strings.dart';
import '../../repositories/mock_repository.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_theme.dart';
import '../document_detail_screen.dart';
import '../upload_evidence_screen.dart';

class DocumentsTab extends StatefulWidget {
  final MockRepository repo;
  final VoidCallback onSave;
  const DocumentsTab({super.key, required this.repo, required this.onSave});

  @override
  State<DocumentsTab> createState() => _DocumentsTabState();
}

class _DocumentsTabState extends State<DocumentsTab> {
  String _filter = 'all';

  @override
  Widget build(BuildContext context) {
    var docs = widget.repo.documents;
    if (_filter != 'all') docs = docs.where((d) => d.reviewStatus == _filter).toList();
    final scale = MediaQuery.textScalerOf(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        FlPageHeader(
          title: 'My Documents',
          subtitle: 'Keep proof files for each assessment item. Tap a document to read feedback.',
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 18),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: DropdownButtonFormField<String>(
                  isExpanded: true,
                  value: _filter,
                  decoration: const InputDecoration(labelText: 'Show'),
                  items: const [
                    DropdownMenuItem(value: 'all', child: Text('All documents')),
                    DropdownMenuItem(value: 'pending', child: Text('Waiting for review')),
                    DropdownMenuItem(value: 'approved', child: Text('Approved')),
                    DropdownMenuItem(value: 'correction_requested', child: Text('Needs changes')),
                  ],
                  onChanged: (v) => setState(() => _filter = v ?? 'all'),
                ),
              ),
              const SizedBox(width: 10),
              FilledButton.icon(
                onPressed: () => Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => UploadEvidenceScreen(repo: widget.repo, onSave: widget.onSave)),
                ),
                icon: const Icon(Icons.add),
                label: const Text('Add'),
              ),
            ],
          ),
        ),
        const SizedBox(height: 8),
        Expanded(
          child: docs.isEmpty
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Text(
                      UiStrings.emptyDocuments,
                      textAlign: TextAlign.center,
                      style: TextStyle(fontSize: scale.scale(17), height: 1.5, color: AppColors.textMuted),
                    ),
                  ),
                )
              : ListView.builder(
                  padding: const EdgeInsets.fromLTRB(18, 8, 18, 24),
                  itemCount: docs.length,
                  itemBuilder: (_, i) {
                    final d = docs[i];
                    final status = UiStrings.docStatusLabel(d.reviewStatus);
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: FlSurfaceCard(
                        onTap: () => Navigator.push(
                          context,
                          MaterialPageRoute(builder: (_) => DocumentDetailScreen(doc: d, onSave: widget.onSave)),
                        ),
                        child: Row(
                          children: [
                            CircleAvatar(
                              backgroundColor: AppColors.primarySoft,
                              child: Icon(Icons.description_outlined, color: AppColors.primaryBlue),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    d.fileName,
                                    style: TextStyle(fontSize: scale.scale(17), fontWeight: FontWeight.w700),
                                  ),
                                  const SizedBox(height: 4),
                                  FlStatusBadge(status),
                                  if (d.academicYear != null)
                                    Padding(
                                      padding: const EdgeInsets.only(top: 4),
                                      child: Text(
                                        '${d.academicYear}${d.semester != null ? " · ${d.semester}" : ""}',
                                        style: TextStyle(fontSize: scale.scale(14), color: AppColors.textMuted),
                                      ),
                                    ),
                                  Padding(
                                    padding: const EdgeInsets.only(top: 6),
                                    child: Text(
                                      'View document',
                                      style: TextStyle(
                                        fontSize: scale.scale(15),
                                        fontWeight: FontWeight.w600,
                                        color: AppColors.primaryBlue,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            const Icon(Icons.chevron_right, color: AppColors.textMuted),
                          ],
                        ),
                      ),
                    );
                  },
                ),
        ),
      ],
    );
  }
}
