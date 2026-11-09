import 'dart:async';

import 'package:flutter/material.dart';

import '../models/institution_config.dart';
import '../repositories/auth_repository.dart';
import '../repositories/institution_config_repository.dart';
import '../repositories/mock_repository.dart';
import '../services/faculty_refresh.dart';
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

class _ShellScreenState extends State<ShellScreen> with WidgetsBindingObserver {
  int _index = 0;
  MockRepository? _repo;
  InstitutionConfig? _institutionConfig;
  WhatIfScenario _whatIf = WhatIfScenario.empty;
  FacultyRefreshCoordinator? _refresh;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    unawaited(_guardSession());
    unawaited(_initialLoad());
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _refresh?.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      _refresh?.onAppLifecycle(true);
    } else if (state == AppLifecycleState.paused || state == AppLifecycleState.inactive) {
      _refresh?.onAppLifecycle(false);
    }
  }

  Future<void> _guardSession() async {
    final mustChange = await AuthRepository.mustChangePassword();
    if (!mounted) return;
    if (mustChange) {
      Navigator.pushReplacementNamed(context, '/change-password');
    }
  }

  Future<void> _initialLoad() async {
    final repo = await MockRepository.load();
    final cfg = await InstitutionConfigRepository.load();
    if (!mounted) return;
    final coordinator = FacultyRefreshCoordinator(
      repo: repo,
      onUpdated: () {
        if (mounted) setState(() {});
      },
    );
    FacultySession.attach(coordinator);
    coordinator.start();
    setState(() {
      _repo = repo;
      _institutionConfig = cfg;
      _refresh = coordinator;
    });
  }

  Future<void> _softRefresh({Set<FacultyRefreshScope>? scopes, bool force = false}) async {
    await _refresh?.refresh(scopes: scopes, force: force);
  }

  void _goToSimulation() => setState(() => _index = 2);

  @override
  Widget build(BuildContext context) {
    if (_repo == null || _institutionConfig == null || _refresh == null) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    final repo = _repo!;
    final cfg = _institutionConfig!;
    final refresh = _refresh!;
    final notifCount = repo.notifications.length;
    final syncErr = refresh.lastError ?? repo.syncError;

    final pages = [
      HomeTab(
        repo: repo,
        institutionConfig: cfg,
        whatIf: _whatIf,
        onRefresh: () => _softRefresh(force: true),
        onOpenSimulation: _goToSimulation,
        onOpenNotifications: () => setState(() => _index = 3),
      ),
      DocumentsTab(
        repo: repo,
        onRefresh: ({scopes, force = false}) => _softRefresh(scopes: scopes, force: force),
      ),
      SimulationTab(
        repo: repo,
        institutionConfig: cfg,
        whatIf: _whatIf,
        onWhatIfChanged: (w) => setState(() => _whatIf = w),
        onRefresh: () => _softRefresh(
          scopes: {
            FacultyRefreshScope.scores,
            FacultyRefreshScope.catalog,
            FacultyRefreshScope.assessment,
          },
          force: true,
        ),
      ),
      NotificationsScreen(
        repo: repo,
        embedInTab: true,
        onRefresh: () => _softRefresh(scopes: {FacultyRefreshScope.notifications}, force: true),
      ),
      ProfileTab(
        repo: repo,
        onSave: () => _softRefresh(
          scopes: {FacultyRefreshScope.assessment, FacultyRefreshScope.scores},
          force: true,
        ),
        onLogout: () async {
          await FacultySession.reset();
          await AuthRepository.logout();
          if (!context.mounted) return;
          Navigator.pushReplacementNamed(context, '/login');
        },
      ),
    ];

    return Scaffold(
      backgroundColor: AppColors.bgLight,
      body: SafeArea(
        bottom: false,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (syncErr != null)
              Material(
                color: Colors.orange.shade50,
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  child: Row(
                    children: [
                      Icon(Icons.cloud_off_outlined, size: 18, color: Colors.orange.shade900),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          syncErr,
                          style: TextStyle(fontSize: 13, color: Colors.orange.shade900),
                        ),
                      ),
                      TextButton(
                        onPressed: () => _softRefresh(force: true),
                        child: const Text('Retry'),
                      ),
                    ],
                  ),
                ),
              ),
            Expanded(
              child: IndexedStack(index: _index, children: pages),
            ),
          ],
        ),
      ),
      bottomNavigationBar: SafeArea(
        child: NavigationBar(
          selectedIndex: _index,
          onDestinationSelected: (i) {
            setState(() => _index = i);
            _refresh?.onTabSelected(i);
          },
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
