import 'package:flutter/material.dart';

import '../core/scoring.dart';
import '../repositories/mock_repository.dart';

class SetSefScreen extends StatefulWidget {
  final MockRepository repo;
  final VoidCallback onSave;
  const SetSefScreen({super.key, required this.repo, required this.onSave});

  @override
  State<SetSefScreen> createState() => _SetSefScreenState();
}

class _SetSefScreenState extends State<SetSefScreen> with SingleTickerProviderStateMixin {
  late TabController _tabs;
  bool _dirty = false;

  @override
  void initState() {
    super.initState();
    _tabs = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _tabs.dispose();
    super.dispose();
  }

  Future<bool> _onWillPop() async {
    if (!_dirty) return true;
    final leave = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Unsaved changes'),
        content: const Text('You have unsaved rating edits. Discard?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Stay')),
          FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Discard')),
        ],
      ),
    );
    return leave ?? false;
  }

  @override
  Widget build(BuildContext context) {
    final years = widget.repo.academicYears;
    final semesters = ['1st Sem', '2nd Sem'];
    final set = computeSetSef(widget.repo.setRatings, 'SET');
    final sef = computeSetSef(widget.repo.sefRatings, 'SEF');

    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, result) async {
        if (didPop) return;
        if (await _onWillPop() && context.mounted) Navigator.pop(context);
      },
      child: Scaffold(
        appBar: AppBar(
          title: const Text('SET / SEF'),
          bottom: TabBar(
            controller: _tabs,
            tabs: const [Tab(text: 'SET'), Tab(text: 'SEF')],
          ),
        ),
        body: TabBarView(
          controller: _tabs,
          children: [
            _grid(years, semesters, widget.repo.setRatings, 'SET', set),
            _grid(years, semesters, widget.repo.sefRatings, 'SEF', sef),
          ],
        ),
        bottomNavigationBar: Padding(
          padding: const EdgeInsets.all(16),
          child: FilledButton(
            onPressed: () async {
              await widget.repo.save();
              setState(() => _dirty = false);
              widget.onSave();
              if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Draft saved locally')));
            },
            child: const Text('Save draft'),
          ),
        ),
      ),
    );
  }

  Widget _grid(List<String> years, List<String> semesters, List<double?> ratings, String type, SetSefResult result) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text('Points estimate: ${result.raw.toStringAsFixed(2)} — ${result.breakdown}', style: const TextStyle(fontWeight: FontWeight.w600)),
        const SizedBox(height: 12),
        ...List.generate(6, (i) {
          final year = years[i ~/ 2];
          final sem = semesters[i % 2];
          return Card(
            child: ListTile(
              title: Text('$year · $sem'),
              subtitle: TextField(
                keyboardType: const TextInputType.numberWithOptions(decimal: true),
                decoration: InputDecoration(hintText: 'Rating %', suffixText: ratings[i]?.toStringAsFixed(0) ?? ''),
                onChanged: (v) {
                  setState(() {
                    ratings[i] = double.tryParse(v);
                    _dirty = true;
                  });
                },
              ),
            ),
          );
        }),
      ],
    );
  }
}
