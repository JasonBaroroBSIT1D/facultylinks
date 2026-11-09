import 'package:flutter/material.dart';

import '../data/assessment_catalog.dart';
import '../repositories/mock_repository.dart';
import '../services/simulation_engine.dart';
import '../theme/app_spacing.dart';
import '../theme/app_theme.dart';

class HomeKraGrid extends StatelessWidget {
  final MockRepository repo;
  final VoidCallback onOpenAssessment;

  const HomeKraGrid({super.key, required this.repo, required this.onOpenAssessment});

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

  @override
  Widget build(BuildContext context) {
    final snapshot = SimulationEngine.compute(repo);
    final scale = MediaQuery.textScalerOf(context);
    final width = MediaQuery.sizeOf(context).width;
    final singleColumn = width < 340 || scale.scale(1) > 1.15;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const FlSectionTitle('Assessment areas'),
        LayoutBuilder(
          builder: (context, constraints) {
            final cardWidth = singleColumn ? constraints.maxWidth : (constraints.maxWidth - 10) / 2;
            return Wrap(
              spacing: 10,
              runSpacing: 10,
              children: assessmentKras.map((kra) {
                final line = snapshot.kras.where((k) => k.kraId == kra.id).firstOrNull;
                final pts = line == null
                    ? '0.00'
                    : line.rawIncomplete
                        ? 'Incomplete'
                        : line.weightedContribution.toStringAsFixed(2);
                return SizedBox(
                  width: cardWidth,
                  child: FlSurfaceCard(
                    onTap: onOpenAssessment,
                    padding: const EdgeInsets.all(14),
                    child: Row(
                      children: [
                        Container(
                          width: 48,
                          height: 48,
                          decoration: BoxDecoration(
                            color: _iconColor(kra.id).withValues(alpha: 0.12),
                            borderRadius: BorderRadius.circular(14),
                          ),
                          child: Icon(_iconFor(kra.id), color: _iconColor(kra.id)),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                kra.shortDropdownLabel,
                                style: TextStyle(
                                  fontSize: scale.scale(16),
                                  fontWeight: FontWeight.w700,
                                  color: AppColors.textMain,
                                ),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                'Est. $pts pts',
                                style: TextStyle(fontSize: scale.scale(15), color: AppColors.textMuted),
                              ),
                            ],
                          ),
                        ),
                        const Icon(Icons.chevron_right, color: AppColors.textMuted),
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
