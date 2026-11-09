import 'package:flutter/material.dart';

import '../../core/scoring.dart';
import '../../data/assessment_catalog.dart';
import '../../repositories/mock_repository.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_theme.dart';
import '../indicator_entries_screen.dart';
import '../kra_i_achievement_screen.dart';
import '../set_sef_screen.dart';
import '../upload_evidence_screen.dart';

class AssessmentTab extends StatelessWidget {
  final MockRepository repo;
  final Future<void> Function() onSave;
  const AssessmentTab({super.key, required this.repo, required this.onSave});

  @override
  Widget build(BuildContext context) {
    final caEst = repo.criterionAEstimatedLine();
    final caVer = repo.criterionAVerifiedLine();
    final set = computeSetSef(repo.setRatings, 'SET');
    final sef = computeSetSef(repo.sefRatings, 'SEF');
    final kras = repo.catalogKras;
    final kraIBcReady = repo.catalogLoadedFromApi &&
        kras.any((k) =>
            k.id == 'kra-I' &&
            k.criteria.any((c) => c.id == 'kra-I-B') &&
            k.criteria.any((c) => c.id == 'kra-I-C'));
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
              MaterialPageRoute(
                builder: (_) => UploadEvidenceScreen(
                  repo: repo,
                  onSave: onSave,
                  initialKraId: 'kra-I',
                  initialCriterionId: 'kra-I-A',
                ),
              ),
            ),
            child: Row(
              children: const [
                Icon(Icons.upload_file, color: AppColors.primaryBlue, size: 28),
                SizedBox(width: 12),
                Expanded(
                  child: Text(
                    'Upload SET / SEF evaluation',
                    style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
                  ),
                ),
                Icon(Icons.chevron_right, color: AppColors.textMuted),
              ],
            ),
          ),
          const SizedBox(height: 8),
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
                      if (caEst.isNotEmpty || caVer.isNotEmpty) ...[
                        if (caEst.isNotEmpty) Text(caEst, style: const TextStyle(fontSize: 15)),
                        if (caVer.isNotEmpty) Text(caVer, style: const TextStyle(fontSize: 15)),
                      ] else
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
          if (!repo.catalogLoadedFromApi)
            const Padding(
              padding: EdgeInsets.only(bottom: 8),
              child: FlSurfaceCard(
                child: Text(
                  'Published assessment rules are not loaded. Pull to refresh or sign in again before self-assessing Criterion B or C.',
                  style: TextStyle(fontSize: 15, color: AppColors.textMuted, height: 1.4),
                ),
              ),
            ),
          if (repo.catalogLoadedFromApi && !kraIBcReady)
            const Padding(
              padding: EdgeInsets.only(bottom: 8),
              child: FlSurfaceCard(
                child: Text(
                  'Published catalog is missing KRA I Criterion B or Criterion C. Contact an administrator to publish the full configuration.',
                  style: TextStyle(fontSize: 15, color: AppColors.textMuted, height: 1.4),
                ),
              ),
            ),
          const SizedBox(height: 8),
          ...kras.map((kra) => Card(
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
                            children: scoringIndicatorsForCriterion(c)
                                .where((i) => i.type != 'set_sef')
                                .where((i) => i.id != criterionASpecialIndicatorId)
                                .map(
                                  (ind) => Material(
                                    color: Colors.transparent,
                                    child: ListTile(
                                      title: Text(ind.name),
                                      subtitle: Text(
                                        ind.maxPoints != null ? 'Max ${ind.maxPoints} pts' : 'See guidelines',
                                      ),
                                      trailing: const Icon(Icons.chevron_right),
                                      onTap: () {
                                        final wantsAch = isAchievementCriterion(kra.id, c.id);
                                        final isAch = repo.catalogLoadedFromApi && wantsAch;
                                        if (wantsAch && !repo.catalogLoadedFromApi) {
                                          ScaffoldMessenger.of(context).showSnackBar(
                                            const SnackBar(
                                              content: Text(
                                                'Self-assessment achievements require the published catalog to be loaded.',
                                              ),
                                            ),
                                          );
                                          return;
                                        }
                                        Navigator.push(
                                          context,
                                          MaterialPageRoute(
                                            builder: (_) => isAch
                                                ? KraIAchievementScreen(
                                                    repo: repo,
                                                    criterion: c,
                                                    indicator: ind,
                                                    onSave: onSave,
                                                  )
                                                : IndicatorEntriesScreen(
                                                    repo: repo,
                                                    indicator: ind,
                                                    kraId: kra.id,
                                                    onSave: onSave,
                                                  ),
                                          ),
                                        );
                                      },
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
