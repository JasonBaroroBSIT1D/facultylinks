import 'package:flutter/material.dart';

import '../../core/scoring.dart';
import '../../data/assessment_catalog.dart';
import '../../repositories/mock_repository.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_theme.dart';
import '../indicator_entries_screen.dart';
import '../set_sef_screen.dart';

class AssessmentTab extends StatelessWidget {
  final MockRepository repo;
  final VoidCallback onSave;
  const AssessmentTab({super.key, required this.repo, required this.onSave});

  @override
  Widget build(BuildContext context) {
    final set = computeSetSef(repo.setRatings, 'SET');
    final sef = computeSetSef(repo.sefRatings, 'SEF');
    return Scaffold(
      appBar: AppBar(
        title: const Text('My Assessment'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          tooltip: 'Back',
          onPressed: () => Navigator.maybePop(context),
        ),
      ),
      body: ListView(
        padding: FlLayout.pagePadding,
        children: [
          Text(
            'Fill in your points and open each indicator when you are ready.',
            style: TextStyle(
              fontSize: MediaQuery.textScalerOf(context).scale(17),
              color: AppColors.textMuted,
              height: 1.45,
            ),
          ),
          const SizedBox(height: 12),
          FlSurfaceCard(
            onTap: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => SetSefScreen(repo: repo, onSave: onSave)),
            ),
            child: Row(
              children: [
                Icon(Icons.school_outlined, color: AppColors.primaryBlue, size: 28),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('SET & SEF', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
                      Text(
                        'KRA I · Instruction — Teaching effectiveness',
                        style: TextStyle(fontSize: 15, color: AppColors.textMuted, height: 1.35),
                      ),
                      Text(
                        'Combined raw ${(set.raw + sef.raw).toStringAsFixed(2)} / 60 max',
                        style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
                      ),
                    ],
                  ),
                ),
                const Icon(Icons.chevron_right, color: AppColors.textMuted),
              ],
            ),
          ),
          const SizedBox(height: 8),
          ...assessmentKras.map((kra) => Card(
                margin: const EdgeInsets.only(bottom: 10),
                clipBehavior: Clip.antiAlias,
                child: ExpansionTile(
                  title: Text(kra.shortDropdownLabel, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 17)),
                  subtitle: Text(kra.name, style: const TextStyle(fontSize: 15, color: AppColors.textMuted, height: 1.35)),
                  children: kra.criteria
                      .map(
                        (c) => Material(
                          color: Colors.transparent,
                          child: ExpansionTile(
                            title: Text(c.name, style: const TextStyle(fontSize: 14)),
                            children: c.indicators
                                .where((i) => i.type != 'set_sef')
                                .map(
                                  (ind) => Material(
                                    color: Colors.transparent,
                                    child: ListTile(
                                      title: Text(ind.name),
                                      subtitle: Text(
                                        ind.maxPoints != null ? 'Max ${ind.maxPoints} pts' : 'See guidelines',
                                      ),
                                      trailing: const Icon(Icons.chevron_right),
                                      onTap: () => Navigator.push(
                                        context,
                                        MaterialPageRoute(
                                          builder: (_) => IndicatorEntriesScreen(
                                            repo: repo,
                                            indicator: ind,
                                            kraId: kra.id,
                                            onSave: onSave,
                                          ),
                                        ),
                                      ),
                                    ),
                                  ),
                                )
                                .toList(),
                          ),
                        ),
                      )
                      .toList(),
                ),
              )),
          const Padding(
            padding: EdgeInsets.all(8),
            child: Text(
              'Full indicator list matches web catalog (assessment-definitions.js). Creative works & extension sub-indicators follow workbook rows.',
              style: TextStyle(fontSize: 12, color: Colors.grey),
            ),
          ),
        ],
      ),
    );
  }
}
