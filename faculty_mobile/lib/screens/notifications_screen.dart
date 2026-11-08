import 'package:flutter/material.dart';

import '../repositories/mock_repository.dart';
import '../theme/app_spacing.dart';
import '../theme/app_theme.dart';

class NotificationsScreen extends StatelessWidget {
  final MockRepository repo;
  final bool embedInTab;

  const NotificationsScreen({super.key, required this.repo, this.embedInTab = false});

  @override
  Widget build(BuildContext context) {
    final scale = MediaQuery.textScalerOf(context);

    final list = repo.notifications.isEmpty
        ? Center(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Text(
                'No notifications yet. When your reviewer sends feedback, it will appear here.',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: scale.scale(17), height: 1.5, color: AppColors.textMuted),
              ),
            ),
          )
        : ListView(
            padding: FlLayout.pagePadding,
            children: repo.notifications
                .map(
                  (n) => Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: FlSurfaceCard(
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Icon(Icons.notifications_active_outlined, color: AppColors.primaryBlue, size: 28),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  n['title'] ?? '',
                                  style: TextStyle(fontSize: scale.scale(17), fontWeight: FontWeight.w700),
                                ),
                                const SizedBox(height: 6),
                                Text(
                                  n['body'] ?? '',
                                  style: TextStyle(fontSize: scale.scale(16), color: AppColors.textMuted, height: 1.45),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                )
                .toList(),
          );

    if (embedInTab) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const FlPageHeader(
            title: 'Notifications',
            subtitle: 'Messages from your reviewer about your documents.',
          ),
          Expanded(child: list),
        ],
      );
    }
    return Scaffold(appBar: AppBar(title: const Text('Notifications')), body: list);
  }
}
