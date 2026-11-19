import '../data/assessment_catalog.dart';
import '../repositories/mock_repository.dart';

class CatalogContextLabels {
  final String? kraLabel;
  final String? criterionLabel;
  final String? indicatorLabel;

  const CatalogContextLabels({this.kraLabel, this.criterionLabel, this.indicatorLabel});

  String get compactLine {
    final parts = <String>[
      if (kraLabel != null && kraLabel!.isNotEmpty) kraLabel!,
      if (criterionLabel != null && criterionLabel!.isNotEmpty) criterionLabel!,
      if (indicatorLabel != null && indicatorLabel!.isNotEmpty) indicatorLabel!,
    ];
    if (parts.isNotEmpty) return parts.join(' · ');
    return '';
  }
}

CatalogContextLabels resolveCatalogLabels(
  MockRepository? repo, {
  required String? indicatorId,
  String? kraId,
  String? criterionId,
}) {
  if (indicatorId == null || indicatorId.isEmpty) {
    return const CatalogContextLabels();
  }
  final kras = repo?.catalogKras ?? const <KraNode>[];
  KraNode? kra;
  CriterionNode? crit;
  IndicatorNode? ind;
  for (final k in kras) {
    for (final c in k.criteria) {
      for (final i in c.indicators) {
        if (i.id == indicatorId) {
          kra = k;
          crit = c;
          ind = i;
          break;
        }
      }
    }
  }
  if (kra == null && kraId != null) {
    kra = kras.where((k) => k.id == kraId).firstOrNull;
  }
  if (crit == null && criterionId != null && kra != null) {
    crit = kra.criteria.where((c) => c.id == criterionId).firstOrNull;
  }
  return CatalogContextLabels(
    kraLabel: kra?.name ?? kraId,
    criterionLabel: crit?.name ?? criterionId,
    indicatorLabel: ind?.name ?? indicatorId,
  );
}