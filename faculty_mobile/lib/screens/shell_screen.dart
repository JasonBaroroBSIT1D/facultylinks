import 'package:flutter/material.dart';

import '../models/institution_config.dart';
import '../repositories/auth_repository.dart';
import '../repositories/institution_config_repository.dart';
import '../repositories/mock_repository.dart';
import '../services/simulation_engine.dart';
import '../theme/app_theme.dart';
import 'notifications_screen.dart';
import 'tabs/documents_tab.dart';
import 'tabs/home_tab.dart';
import 'tabs/profile_tab.dart';
import 'tabs/simulation_tab.dart';

class ShellScreen extends StatefulWidget {
  const ShellScreen({super.key});

  @override
  State<ShellScreen> createState() => _ShellScreenState();
}

class _ShellScreenState extends State<ShellScreen> {
  int _index = 0;
  MockRepository? _repo;
  InstitutionConfig? _institutionConfig;
  WhatIfScenario _whatIf = WhatIfScenario.empty;

  @override
  void initState() {
    super.initState();
    _guardSession();
    _load();
  }

  Future<void> _guardSession() async {
    final mustChange = await AuthRepository.mustChangePassword();
    if (!mounted) return;
    if (mustChange) {
      Navigator.pushReplacementNamed(context, '/change-password');
    }
  }

  Future<void> _load() async {
    final repo = await MockRepository.load();
    final cfg = await InstitutionConfigRepository.load();
    setState(() {
      _repo = repo;
      _institutionConfig = cfg;
    });
  }

  void _goToSimulation() => setState(() => _index = 2);

  @override
  Widget build(BuildContext context) {
    if (_repo == null || _institutionConfig == null) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    final repo = _repo!;
    final cfg = _institutionConfig!;
    final notifCount = repo.notifications.length;

    final pages = [
      HomeTab(
        repo: repo,
        institutionConfig: cfg,
        whatIf: _whatIf,
        onRefresh: _load,
        onOpenSimulation: _goToSimulation,
        onOpenNotifications: () => setState(() => _index = 3),
      ),
      DocumentsTab(repo: repo, onSave: _load),
      SimulationTab(
        repo: repo,
        institutionConfig: cfg,
        whatIf: _whatIf,
        onWhatIfChanged: (w) => setState(() => _whatIf = w),
      ),
      NotificationsScreen(repo: repo, embedInTab: true),
      ProfileTab(repo: repo, onSave: _load, onLogout: () async {
        await AuthRepository.logout();
        if (!context.mounted) return;
        Navigator.pushReplacementNamed(context, '/login');
      }),
    ];

    return Scaffold(
      backgroundColor: AppColors.bgLight,
      body: SafeArea(
        bottom: false,
        child: IndexedStack(index: _index, children: pages),
      ),
      bottomNavigationBar: SafeArea(
        child: NavigationBar(
          selectedIndex: _index,
          onDestinationSelected: (i) => setState(() => _index = i),
          destinations: [
            const NavigationDestination(
              icon: Icon(Icons.home_outlined),
              selectedIcon: Icon(Icons.home),
              label: 'Home',
            ),
            const NavigationDestination(
              icon: Icon(Icons.folder_outlined),
              selectedIcon: Icon(Icons.folder),
              label: 'Documents',
            ),
            const NavigationDestination(
              icon: Icon(Icons.insights_outlined),
              selectedIcon: Icon(Icons.insights),
              label: 'Simulation',
            ),
            NavigationDestination(
              icon: _badgedIcon(Icons.notifications_outlined, notifCount),
              selectedIcon: _badgedIcon(Icons.notifications, notifCount),
              label: 'Notifications',
            ),
            const NavigationDestination(
              icon: Icon(Icons.person_outline),
              selectedIcon: Icon(Icons.person),
              label: 'Profile',
            ),
          ],
        ),
      ),
    );
  }

  Widget _badgedIcon(IconData icon, int count) {
    if (count <= 0) return Icon(icon);
    return Badge(
      label: Text('$count'),
      child: Icon(icon),
    );
  }
}
