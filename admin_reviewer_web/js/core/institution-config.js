import {
  computeEvaluationPeriodStatus,
  reviewerAvailabilityDetail,
} from './evaluation-period-service.js';
import { DEFAULT_RANK_LADDER, DEFAULT_RANK_SIMULATION } from './rank-simulation-config.js';

/** Institution simulation & evaluation period settings (demo web localStorage; mobile uses matching local demo). */

export const DEFAULT_INSTITUTION_CONFIG = () => ({
  preparationPeriod: {
    start: '2026-01-15',
    end: '2026-06-30',
    reviewerAvailableFrom: '2026-02-01',
  },
  /** Rank labels for selectors only; thresholds set in rankRequirements by admin. */
  rankOptions: DEFAULT_RANK_LADDER(),
  rankSimulation: DEFAULT_RANK_SIMULATION(),
  /**
   * targetRank -> { minWeightedTotal?: number, notes?: string }
   * Empty until configured — no invented NBC thresholds.
   */
  rankRequirements: {},
  rankMappingStatus: 'pending',
});

export function preparationStatus(cfg, now = new Date()) {
  return computeEvaluationPeriodStatus(cfg.preparationPeriod, now);
}

export function reviewerAvailable(cfg, now = new Date()) {
  const rev = reviewerAvailabilityDetail(cfg.preparationPeriod, now);
  return { available: rev.available, label: rev.shortLabel };
}

export function evaluateRankEligibility(cfg, currentRank, targetRank, weightedTotal) {
  if (cfg.rankMappingStatus !== 'configured') {
    return {
      potentialRank: 'Pending configuration',
      readinessPercent: null,
      readinessLabel: 'Not available',
      simulationStatus: 'Rank mapping pending configuration',
      unmet: ['Institution has not published rank requirement thresholds.'],
    };
  }
  const req = cfg.rankRequirements[targetRank];
  if (!req?.minWeightedTotal) {
    return {
      potentialRank: 'Requirements to be confirmed',
      readinessPercent: null,
      readinessLabel: 'Not available',
      simulationStatus: 'Target rank requirements not configured',
      unmet: [`No minimum weighted total configured for ${targetRank}.`],
    };
  }
  const min = req.minWeightedTotal;
  const met = weightedTotal >= min;
  const readinessPercent = met ? 100 : Math.min(99, Math.round((weightedTotal / min) * 100));
  return {
    potentialRank: met ? targetRank : `${targetRank} (not yet eligible)`,
    readinessPercent: met ? 100 : readinessPercent,
    readinessLabel: met ? '100% toward configured minimum' : `${readinessPercent}% of configured minimum`,
    simulationStatus: met ? 'Meets configured minimum (preparation only)' : 'Below configured minimum',
    unmet: met ? [] : [`Weighted total ${weightedTotal.toFixed(2)} is below configured minimum ${min} for ${targetRank}.`],
  };
}
