import 'dart:async';

import 'package:flutter/foundation.dart';

import '../repositories/mock_repository.dart';

/// Data domains synchronized from the faculty API.
enum FacultyRefreshScope {
  profile,
  assessment,
  catalog,
  scores,
  documents,
  notifications,
}

class FacultyRefreshScopes {
  FacultyRefreshScopes._();

  static const Duration staleAfter = Duration(seconds: 30);
  static const Duration periodicInterval = Duration(seconds: 30);
  static const Duration processingPollInterval = Duration(seconds: 4);

  static Set<FacultyRefreshScope> get all => FacultyRefreshScope.values.toSet();

  static Set<FacultyRefreshScope> forTab(int index) {
    switch (index) {
      case 0:
        return {
          FacultyRefreshScope.profile,
          FacultyRefreshScope.scores,
          FacultyRefreshScope.documents,
          FacultyRefreshScope.notifications,
          FacultyRefreshScope.assessment,
        };
      case 1:
        return {
          FacultyRefreshScope.documents,
          FacultyRefreshScope.scores,
          FacultyRefreshScope.assessment,
        };
      case 2:
        return {
          FacultyRefreshScope.scores,
          FacultyRefreshScope.catalog,
          FacultyRefreshScope.assessment,
        };
      case 3:
        return {FacultyRefreshScope.notifications};
      case 4:
        return {FacultyRefreshScope.profile};
      default:
        return all;
    }
  }
}

typedef FacultyRefreshCallback = Future<void> Function({
  Set<FacultyRefreshScope>? scopes,
  bool force,
});

/// Coordinates background refresh, polling, and stale-response discard for faculty data.
class FacultyRefreshCoordinator {
  FacultyRefreshCoordinator({
    required this.repo,
    required this.onUpdated,
  });

  final MockRepository repo;
  final VoidCallback onUpdated;

  int _generation = 0;
  bool _refreshing = false;
  bool _pending = false;
  bool _foreground = true;
  int _tabIndex = 0;
  bool _disposed = false;

  Timer? _periodicTimer;
  Timer? _processingTimer;

  String? lastError;
  DateTime? lastSuccessAt;

  final Map<FacultyRefreshScope, DateTime> _lastFetched = {};

  void start() {
    _scheduleTimers();
  }

  void dispose() {
    _disposed = true;
    _periodicTimer?.cancel();
    _processingTimer?.cancel();
    _periodicTimer = null;
    _processingTimer = null;
  }

  void onAppLifecycle(bool foreground) {
    _foreground = foreground;
    if (foreground) {
      unawaited(refresh(scopes: FacultyRefreshScopes.forTab(_tabIndex), force: true));
    }
    _scheduleTimers();
  }

  void onTabSelected(int index) {
    _tabIndex = index;
    final scopes = FacultyRefreshScopes.forTab(index);
    if (_isStale(scopes)) {
      unawaited(refresh(scopes: scopes));
    }
    _scheduleTimers();
  }

  bool _isStale(Set<FacultyRefreshScope> scopes) {
    final now = DateTime.now();
    for (final s in scopes) {
      final t = _lastFetched[s];
      if (t == null || now.difference(t) > FacultyRefreshScopes.staleAfter) {
        return true;
      }
    }
    return false;
  }

  Future<void> refresh({
    Set<FacultyRefreshScope>? scopes,
    bool force = false,
  }) async {
    if (_disposed) return;
    if (_refreshing) {
      _pending = true;
      return;
    }
    final activeScopes = scopes ?? FacultyRefreshScopes.all;
    if (!force && !_isStale(activeScopes)) return;

    _refreshing = true;
    try {
      do {
        _pending = false;
        final requestGen = ++_generation;
        final result = await repo.refreshFromApi(
          scopes: activeScopes,
          expectedGeneration: requestGen,
        );
        if (_disposed || requestGen != _generation) return;
        if (result.applied) {
          final now = DateTime.now();
          for (final s in activeScopes) {
            _lastFetched[s] = now;
          }
          lastSuccessAt = now;
          lastError = result.errorMessage;
          repo.syncError = result.errorMessage;
          _scheduleTimers();
          onUpdated();
        } else if (result.errorMessage != null) {
          lastError = result.errorMessage;
          repo.syncError = result.errorMessage;
          onUpdated();
        }
      } while (_pending && !_disposed);
    } finally {
      _refreshing = false;
    }
  }

  void _scheduleTimers() {
    _periodicTimer?.cancel();
    _processingTimer?.cancel();
    if (_disposed || !_foreground) return;

    final tabPollsData = _tabIndex <= 2;
    if (tabPollsData) {
      _periodicTimer = Timer.periodic(FacultyRefreshScopes.periodicInterval, (_) {
        if (_disposed || !_foreground || _tabIndex > 2) return;
        unawaited(refresh(scopes: FacultyRefreshScopes.forTab(_tabIndex)));
      });
    }

    if (tabPollsData && repo.hasActiveDocumentProcessing) {
      _processingTimer = Timer.periodic(FacultyRefreshScopes.processingPollInterval, (_) {
        if (_disposed || !_foreground || _tabIndex > 2) return;
        if (!repo.hasActiveDocumentProcessing) {
          _processingTimer?.cancel();
          _processingTimer = null;
          return;
        }
        unawaited(
          refresh(
            scopes: {
              FacultyRefreshScope.documents,
              FacultyRefreshScope.scores,
              FacultyRefreshScope.assessment,
            },
          ),
        );
      });
    }
  }

  void notifyRepoMutated() {
    _scheduleTimers();
  }
}

class FacultySession {
  FacultySession._();

  static FacultyRefreshCoordinator? active;

  static void attach(FacultyRefreshCoordinator coordinator) {
    active?.dispose();
    active = coordinator;
  }

  static Future<void> reset() async {
    active?.dispose();
    active = null;
    await MockRepository.clearUserScope();
  }
}
