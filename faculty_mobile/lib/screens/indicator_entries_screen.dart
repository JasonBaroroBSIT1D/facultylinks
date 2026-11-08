import 'package:flutter/material.dart';

import '../data/assessment_catalog.dart';
import '../repositories/mock_repository.dart';

class IndicatorEntriesScreen extends StatefulWidget {
  final MockRepository repo;
  final IndicatorNode indicator;
  final String kraId;
  final VoidCallback onSave;
  const IndicatorEntriesScreen({super.key, required this.repo, required this.indicator, required this.kraId, required this.onSave});

  @override
  State<IndicatorEntriesScreen> createState() => _IndicatorEntriesScreenState();
}

class _IndicatorEntriesScreenState extends State<IndicatorEntriesScreen> {
  late List<AssessmentEntry> items;

  @override
  void initState() {
    super.initState();
    items = widget.repo.entries.where((e) => e.indicatorId == widget.indicator.id).toList();
  }

  void _addEntry() async {
    final title = TextEditingController();
    final date = TextEditingController();
    final contribution = TextEditingController(text: '100');
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('New entry'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(controller: title, decoration: const InputDecoration(labelText: 'Title')),
            TextField(controller: date, decoration: const InputDecoration(labelText: 'Date')),
            if (widget.indicator.id.contains('II'))
              TextField(controller: contribution, decoration: const InputDecoration(labelText: 'Contribution %')),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Save')),
        ],
      ),
    );
    if (ok != true || title.text.isEmpty) return;
    final est = widget.indicator.maxPoints?.toDouble() ?? 0;
    final pct = int.tryParse(contribution.text) ?? 100;
    final entry = AssessmentEntry(
      id: 'e-${DateTime.now().millisecondsSinceEpoch}',
      indicatorId: widget.indicator.id,
      title: title.text,
      date: date.text,
      contributionPercent: pct,
      estimatedPoints: est * pct / 100,
      reviewStatus: 'draft',
    );
    setState(() => items.add(entry));
    widget.repo.entries.add(entry);
    await widget.repo.save();
    widget.onSave();
  }

  Future<void> _submit(AssessmentEntry e) async {
    e.reviewStatus = 'submitted';
    await widget.repo.save();
    widget.onSave();
    setState(() {});
    if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Submitted for demonstration review')));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.indicator.name)),
      floatingActionButton: FloatingActionButton(onPressed: _addEntry, child: const Icon(Icons.add)),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text('Max reference: ${widget.indicator.maxPoints ?? "Pending configuration"}', style: const TextStyle(color: Colors.grey)),
          ...items.map((e) => Card(
                child: ListTile(
                  title: Text(e.title),
                  subtitle: Text('Est. ${e.estimatedPoints} pts · ${e.reviewStatus}'),
                  trailing: e.reviewStatus == 'draft'
                      ? TextButton(onPressed: () => _submit(e), child: const Text('Submit'))
                      : null,
                ),
              )),
          if (items.isEmpty) const Text('No entries yet. Tap + to add evidence-backed assessment data.'),
        ],
      ),
    );
  }
}
