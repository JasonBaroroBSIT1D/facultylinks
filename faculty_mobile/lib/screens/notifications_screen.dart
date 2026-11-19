import 'package:flutter/material.dart';

import '../repositories/mock_repository.dart';
import '../services/notification_navigation.dart';
import '../theme/app_spacing.dart';
import '../theme/app_theme.dart';

class NotificationsScreen extends StatefulWidget {
  final MockRepository repo;
  final bool embedInTab;
  final Future<void> Function()? onRefresh;

  const NotificationsScreen({super.key, required this.repo, this.embedInTab = false, this.onRefresh});

  @override
  State<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends State<NotificationsScreen> {
  Widget _body(Widget list) {
    if (widget.onRefresh == null) return list;
    return RefreshIndicator(
      color: AppColors.primaryBlue,
      onRefresh: widget.onRefresh!,
      child: list is ListView
          ? list
          : ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              children: [
                SizedBox(
                  height: 240,
                  child: Center(child: list),
                ),
              ],
            ),
    );
  }

  Future<void> _openNote(BuildContext context, n) async {
    await openFacultyNotification(
      context,
      note: n,
      repo: widget.repo,
      onRefresh: widget.onRefresh ?? () async {},
    );
    if (mounted) setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    final scale = MediaQuery.textScalerOf(context);
    final repo = widget.repo;

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
        : ListView.builder(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: FlLayout.pagePadding,
            itemCount: repo.notifications.length,
            itemBuilder: (context, index) {
              final n = repo.notifications[index];
              final unread = !n.read;
              final subtitle = n.subtitleLine;
              return Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: FlSurfaceCard(
                  onTap: () => _openNote(context, n),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Icon(
                        unread ? Icons.mark_email_unread_outlined : Icons.notifications_outlined,
                        color: unread ? AppColors.primaryBlue : AppColors.textMuted,
                        size: 28,
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              n.title,
                              style: TextStyle(
                                fontSize: scale.scale(17),
                                fontWeight: unread ? FontWeight.w800 : FontWeight.w600,
                                color: AppColors.navyDeep,
                              ),
                            ),
                            if (subtitle.isNotEmpty) ...[
                              const SizedBox(height: 4),
                              Text(
                                subtitle,
                                style: TextStyle(fontSize: scale.scale(14), color: AppColors.primaryBlue),
                              ),
                            ],
                            if (n.actorName != null && n.actorName!.isNotEmpty) ...[
                              const SizedBox(height: 4),
                              Text(
                                'From ${n.actorName}',
                                style: TextStyle(fontSize: scale.scale(14), color: AppColors.textMuted),
                              ),
                            ],
                            const SizedBox(height: 6),
                            Text(
                              n.body,
                              style: TextStyle(fontSize: scale.scale(15), color: AppColors.textMuted, height: 1.45),
                            ),
                            if (n.atManila != null) ...[
                              const SizedBox(height: 8),
                              Text(
                                n.atManila!,
                                style: TextStyle(fontSize: scale.scale(13), color: AppColors.textMuted),
                              ),
                            ],
                          ],
                        ),
                      ),
                      Icon(Icons.chevron_right, color: AppColors.textMuted, size: 26),
                    ],
                  ),
                ),
              );
            },
          );

    final body = _body(list);

    if (widget.embedInTab) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const FlPageHeader(
            title: 'Notifications',
            subtitle: 'Reviewer decisions and messages about your submissions.',
          ),
          Expanded(child: body),
        ],
      );
    }
    return Scaffold(appBar: AppBar(title: const Text('Notifications')), body: body);
  }
}