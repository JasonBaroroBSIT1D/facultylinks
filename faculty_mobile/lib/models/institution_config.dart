import '../core/evaluation_period_service.dart';

class InstitutionConfig {
  final PreparationPeriod preparationPeriod;
  final List<String> rankOptions;
  final Map<String, RankRequirement> rankRequirements;
  final String rankMappingStatus;
  final ReviewWindow? reviewWindow;

  InstitutionConfig({
    required this.preparationPeriod,
    required this.rankOptions,
    required this.rankRequirements,
    required this.rankMappingStatus,
    this.reviewWindow,
  });

  factory InstitutionConfig.defaults() => InstitutionConfig(
        preparationPeriod: PreparationPeriod(
          start: DateTime(2026, 1, 15),
          end: DateTime(2026, 6, 30),
          reviewerAvailableFrom: DateTime(2026, 2, 1),
        ),
        rankOptions: const [
          'Instructor I',
          'Instructor II',
          'Instructor III',
          'Assistant Professor I',
          'Assistant Professor II',
          'Assistant Professor III',
          'Associate Professor I',
          'Associate Professor II',
          'Associate Professor III',
          'Professor I',
          'Professor II',
          'Professor III',
        ],
        rankRequirements: const {},
        rankMappingStatus: 'pending',
      );

  Map<String, dynamic> toJson() => {
        'preparationPeriod': preparationPeriod.toJson(),
        'rankOptions': rankOptions,
        'rankRequirements': rankRequirements.map((k, v) => MapEntry(k, v.toJson())),
        'rankMappingStatus': rankMappingStatus,
        if (reviewWindow != null) 'reviewWindow': {
          'allowed': reviewWindow!.allowed,
          'state': reviewWindow!.state,
          'message': reviewWindow!.message,
          'opensOn': reviewWindow!.opensOn,
          'endsOn': reviewWindow!.endsOn,
        },
      };

  factory InstitutionConfig.fromJson(Map<String, dynamic> j) => InstitutionConfig(
        preparationPeriod: PreparationPeriod.fromJson(j['preparationPeriod'] as Map<String, dynamic>),
        rankOptions: (j['rankOptions'] as List).cast<String>(),
        rankRequirements: (j['rankRequirements'] as Map<String, dynamic>? ?? {}).map(
          (k, v) => MapEntry(k, RankRequirement.fromJson(v as Map<String, dynamic>)),
        ),
        rankMappingStatus: j['rankMappingStatus'] as String? ?? 'pending',
        reviewWindow: j['reviewWindow'] != null
            ? ReviewWindow.fromJson(j['reviewWindow'] as Map<String, dynamic>)
            : null,
      );
}

class PreparationPeriod {
  final DateTime start;
  final DateTime end;
  final DateTime? reviewerAvailableFrom;

  PreparationPeriod({required this.start, required this.end, this.reviewerAvailableFrom});

  String preparationStatus([DateTime? now]) =>
      EvaluationPeriodService.computeStatus(start: start, end: end, now: now);

  String evaluationStatus([DateTime? now]) => preparationStatus(now);

  bool reviewerIsAvailable({DateTime? now, ReviewWindow? reviewWindow}) {
    final win = EvaluationPeriodService.resolveReviewWindow(
      start: start,
      end: end,
      reviewerAvailableFrom: reviewerAvailableFrom,
      serverWindow: reviewWindow,
      now: now,
    );
    return win.allowed;
  }

  Map<String, dynamic> toJson() => {
        'start': start.toIso8601String().split('T').first,
        'end': end.toIso8601String().split('T').first,
        'reviewerAvailableFrom': reviewerAvailableFrom?.toIso8601String().split('T').first,
      };

  factory PreparationPeriod.fromJson(Map<String, dynamic> j) => PreparationPeriod(
        start: DateTime.parse(j['start'] as String),
        end: DateTime.parse(j['end'] as String),
        reviewerAvailableFrom: j['reviewerAvailableFrom'] != null ? DateTime.parse(j['reviewerAvailableFrom'] as String) : null,
      );
}

class RankRequirement {
  final double? minWeightedTotal;
  final String? notes;

  RankRequirement({this.minWeightedTotal, this.notes});

  Map<String, dynamic> toJson() => {'minWeightedTotal': minWeightedTotal, 'notes': notes};

  factory RankRequirement.fromJson(Map<String, dynamic> j) => RankRequirement(
        minWeightedTotal: (j['minWeightedTotal'] as num?)?.toDouble(),
        notes: j['notes'] as String?,
      );
}
