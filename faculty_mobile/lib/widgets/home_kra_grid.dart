import 'package:flutter/material.dart';

import '../data/assessment_catalog.dart';
import '../repositories/mock_repository.dart';
import '../services/simulation_engine.dart';
import '../theme/app_spacing.dart';
import '../theme/app_theme.dart';

class HomeKraGrid extends StatelessWidget {
  final MockRepository repo;

  /// Opens the selected assessment area. Passes the stable catalog id
  /// (`kra-I` … `kra-IV`) — never display labels.
  final ValueChanged<String> onOpenKra;

  const HomeKraGrid({super.key, required this.repo, required this.onOpenKra});

  static IconData _iconFor(String id) {
    switch (id) {
      case 'kra-I':
        return Icons.menu_book_outlined;
      case 'kra-II':
        return Icons.science_outlined;
      case 'kra-III':
        return Icons.groups_outlined;
      case 'kra-IV':
        return Icons.workspace_premium_outlined;
      default:
        return Icons.folder_outlined;
    }
  }

  static Color _iconColor(String id) {
    switch (id) {
      case 'kra-I':
        return AppColors.primaryBlue;
      case 'kra-II':
        return const Color(0xFF6B4BC8);
      case 'kra-III':
        return const Color(0xFF2D8C6E);
      case 'kra-IV':
        return const Color(0xFFC97A16);
      default:
        return AppColors.primaryBlue;
    }
  }

  static String _kraCode(String id) {
    switch (id) {
      case 'kra-I':
        return 'KRA I';
      case 'kra-II':
        return 'KRA II';
      case 'kra-III':
        return 'KRA III';
      case 'kra-IV':
        return 'KRA IV';
      default:
        return id;
    }
  }

  /// Short area title — never hyphenated mid-word; wraps between words only.
  static String _areaTitle(String id) {
    switch (id) {
      case 'kra-I':
        return 'Instruction';
      case 'kra-II':
        return 'Research';
      case 'kra-III':
        return 'Extension';
      case 'kra-IV':
        return 'Professional Development';
      default:
        return id;
    }
  }

  String _scoreLabel(SimulationSnapshot snapshot, String kraId) {
    if (!repo.scoresConfigured) return 'Est. — pts';
    final line = snapshot.kras.where((k) => k.kraId == kraId).firstOrNull;
    if (line == null) return 'Est. — pts';
    if (line.rawIncomplete) return 'Est. Incomplete';
    return 'Est. ${line.weightedContribution.toStringAsFixed(2)} pts';
  }

  @override
  Widget build(BuildContext context) {
    final snapshot = SimulationEngine.compute(repo);
    final scale = MediaQuery.textScalerOf(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const FlSectionTitle('Assessment areas'),
        LayoutBuilder(
          builder: (context, constraints) {
            final singleColumn = constraints.maxWidth < 340 || scale.scale(1) > 1.2;
            final gap = 10.0;
            final cardWidth = singleColumn ? constraints.maxWidth : (constraints.maxWidth - gap) / 2;

            return Wrap(
              spacing: gap,
              runSpacing: gap,
              children: assessmentKras.map((kra) {
                final color = _iconColor(kra.id);
                return SizedBox(
                  width: cardWidth,
                  child: FlSurfaceCard(
                    onTap: () => onOpenKra(kra.id),
                    padding: const EdgeInsets.fromLTRB(14, 12, 12, 14),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Container(
                              width: 40,
                              height: 40,
                              decoration: BoxDecoration(
                                color: color.withValues(alpha: 0.12),
                                borderRadius: BorderRadius.circular(12),
                              ),
                              child: Icon(_iconFor(kra.id), color: color, size: 22),
                            ),
                            const Spacer(),
                            Icon(Icons.chevron_right, color: AppColors.textMuted, size: scale.scale(22)),
                          ],
                        ),
                        const SizedBox(height: 10),
                        Text(
                          _kraCode(kra.id),
                          style: TextStyle(
                            fontSize: scale.scale(13),
                            fontWeight: FontWeight.w600,
                            color: AppColors.textMuted,
                            height: 1.2,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          _areaTitle(kra.id),
                          softWrap: true,
                          style: TextStyle(
                            fontSize: scale.scale(16),
                            fontWeight: FontWeight.w700,
                            color: AppColors.textMain,
                            height: 1.3,
                          ),
                        ),
                        const SizedBox(height: 10),
                        Text(
                          _scoreLabel(snapshot, kra.id),
                          style: TextStyle(
                            fontSize: scale.scale(14),
                            color: AppColors.textMuted,
                            height: 1.3,
                          ),
                        ),
                      ],
                    ),
                  ),
                );
              }).toList(),
            );
          },
        ),
      ],
    );
  }
}
