import { ASSESSMENT_CATALOG, KRA_WEIGHTS, isSupportingEvidenceIndicator } from './assessment-definitions.js';
import { findIndicatorInCatalog } from '../repositories/config-repository.js';

export function computeSetSefPoints(ratings, type, factorOverride = null) {
  const filled = ratings.filter((r) => r != null && !Number.isNaN(r));
  if (filled.length === 0) return { raw: 0, estimated: 0, breakdown: 'No ratings entered' };
  const avg = filled.reduce((a, b) => a + b, 0) / filled.length;
  const factor = factorOverride ?? (type === 'SET' ? 0.36 : 0.24);
  const raw = avg * factor;
  return {
    raw,
    estimated: raw,
    breakdown: `avg(${filled.map((r) => r.toFixed(1)).join(', ')}) = ${avg.toFixed(2)} × ${factor} = ${raw.toFixed(2)}`,
    average: avg,
  };
}

export function computeTeachingEffectiveness(setRaw, sefRaw, critMax = 60) {
  return {
    raw: setRaw + sefRaw,
    max: critMax,
    breakdown: `SET ${setRaw.toFixed(2)} + SEF ${sefRaw.toFixed(2)} = ${(setRaw + sefRaw).toFixed(2)} (Criterion A max ${critMax})`,
  };
}

export function capPoints(sum, cap) {
  if (cap == null || Number.isNaN(cap)) return sum;
  return Math.min(sum, cap);
}

export function applyContribution(basePoints, contributionPercent = 100) {
  return (basePoints * contributionPercent) / 100;
}

/** @param {object} catalog */
export function estimateEntryPoints(indicatorId, entry, catalog = ASSESSMENT_CATALOG) {
  const found = findIndicatorInCatalog(catalog, indicatorId);
  if (!found) return 0;
  const { ind } = found;

  if (isSupportingEvidenceIndicator(ind)) return 0;
  if (ind.type === 'set_sef' && entry.rating != null) return 0;

  const calc = ind.calculation || {};
  if (calc.kind === 'role_matrix' && calc.matrix && entry.thesisType && entry.role) {
    const matrix = calc.matrix[entry.role] || ind.matrix?.[entry.role];
    if (matrix) return (matrix[entry.thesisType] || 0) * (entry.quantity || 1);
  }

  const points = calc.points || ind.points;
  if (points && typeof points === 'object' && !Array.isArray(points)) {
    const key = entry.subType || entry.tier || entry.scope;
    if (key && points[key] != null) return applyContribution(points[key], entry.contributionPercent ?? ind.contributionAllocation?.defaultPercent ?? 100);
  }

  const alloc = ind.contributionAllocation || {};
  if (alloc.mode === 'lead_contributor') {
    if (entry.role === 'contributor' && (alloc.contributorPoints != null || ind.contributorPoints != null)) {
      return alloc.contributorPoints ?? ind.contributorPoints;
    }
    if (entry.role === 'lead' && (alloc.leadPoints != null || ind.maxPoints != null)) {
      return alloc.leadPoints ?? ind.maxPoints;
    }
  }

  let base = ind.maxPoints ?? calc.maxPoints ?? ind.perService ?? 0;
  if (ind.perService) base = ind.perService * (entry.quantity || 1);

  return applyContribution(base, entry.contributionPercent ?? alloc.defaultPercent ?? 100);
}

/**
 * @param {object} state entries grouped by indicatorId
 * @param {object} catalog
 * @param {object} kraWeights
 */
export function computeKraSummaries(state, catalog = ASSESSMENT_CATALOG, kraWeights = KRA_WEIGHTS) {
  const summaries = {};
  for (const kra of catalog.kras) {
    let rawSum = 0;
    const criterionTotals = [];
    const weight = kraWeights[kra.id] ?? kra.weight ?? 0;

    for (const crit of kra.criteria) {
      let critSum = 0;
      const critCap = crit.capMaxPoints ?? crit.maxPoints ?? parseCap(crit.capNote);

      if (crit.id === 'kra-I-A' || crit.indicators?.some((i) => i.type === 'set_sef')) {
        const setRatings = state.setSef?.SET || [];
        const sefRatings = state.setSef?.SEF || [];
        const setInd = crit.indicators.find((i) => i.subType === 'SET' || i.id?.includes('set'));
        const sefInd = crit.indicators.find((i) => i.subType === 'SEF' || i.id?.includes('sef'));
        const setFactor = setInd?.calculation?.factor ?? 0.36;
        const sefFactor = sefInd?.calculation?.factor ?? 0.24;
        const setPts = computeSetSefPoints(setRatings, 'SET', setFactor).raw;
        const sefPts = computeSetSefPoints(sefRatings, 'SEF', sefFactor).raw;
        const hasSet = setRatings.some((r) => r != null && !Number.isNaN(r));
        const hasSef = sefRatings.some((r) => r != null && !Number.isNaN(r));
        if (hasSet && hasSef) critSum = capPoints(setPts + sefPts, critCap);
        else if (hasSet) critSum = capPoints(setPts, critCap);
        else if (hasSef) critSum = capPoints(sefPts, critCap);
        criterionTotals.push({ id: crit.id, raw: critSum, teachingEffectiveness: computeTeachingEffectiveness(setPts, sefPts, critCap) });
      } else {
        for (const ind of crit.indicators) {
          const entries = state.entries?.[ind.id] || [];
          let indSum = 0;
          if (ind.type === 'set_sef') continue;
          if (isSupportingEvidenceIndicator(ind)) continue;
          for (const e of entries) {
            const est = e.reviewerVerifiedPoints ?? e.estimatedPoints ?? estimateEntryPoints(ind.id, e, catalog);
            indSum += est;
          }
          const indCap = ind.maxPoints ?? null;
          indSum = capPoints(indSum, indCap);
          critSum += indSum;
        }
        critSum = capPoints(critSum, critCap);
        criterionTotals.push({ id: crit.id, raw: critSum });
      }
      rawSum += critSum;
    }

    const weighted = rawSum * weight;
    summaries[kra.id] = {
      kraId: kra.id,
      name: kra.name,
      rawTotal: rawSum,
      weightedContribution: weighted,
      weight,
      criteria: criterionTotals,
    };
  }

  const overallWeighted = Object.values(summaries).reduce((a, s) => a + s.weightedContribution, 0);
  return { byKra: summaries, overallWeighted };
}

function parseCap(note) {
  if (!note) return null;
  const m = /Max\s*=\s*(\d+)/i.exec(note);
  return m ? Number(m[1]) : null;
}

export function computeVerifiedTotals(facultyState, catalog, kraWeights) {
  const est = computeKraSummaries(facultyState, catalog, kraWeights);
  const verified = computeKraSummaries(
    {
      ...facultyState,
      entries: mapVerifiedEntries(facultyState.entries),
    },
    catalog,
    kraWeights
  );
  return { estimated: est, verified };
}

function mapVerifiedEntries(entries = {}) {
  const out = {};
  for (const [k, list] of Object.entries(entries)) {
    out[k] = list.map((e) => ({
      ...e,
      estimatedPoints: e.reviewerVerifiedPoints ?? e.estimatedPoints,
    }));
  }
  return out;
}
