import { scaleLinear, scaleLog } from 'd3-scale'
import { interpolatePlasma, interpolateRdBu } from 'd3-scale-chromatic'

import type { MetricInfo } from '@/api/client'

export const MIN_HEIGHT = 1
export const MAX_HEIGHT = 20
/** Neutral grey (zinc-400): the position has no value for this metric. */
export const MISSING_COLOUR = '#a1a1aa'

// RdBu's darkest ends are hard to tell apart on screen, so gains and losses use its inner 80%.
const DIVERGING_START = 0.1
const DIVERGING_END = 0.9
// Signed colours saturate at this share of the largest moves, so one outlier doesn't wash the
// rest of the city out to white.
const SIGNED_SATURATION_PERCENTILE = 0.95

type MetricValue = number | null

/**
 * Building height for each value of a metric, relative to the universe on screen (a value can be
 * tall in a portfolio and average in the S&P). Missing values get the lowest height.
 */
export function heightScale(
  metric: Pick<MetricInfo, 'scale'>,
  values: MetricValue[],
): (value: MetricValue) => number {
  const position = relativePosition(metric, present(values))
  return (value) =>
    value === null ? MIN_HEIGHT : MIN_HEIGHT + position(value) * (MAX_HEIGHT - MIN_HEIGHT)
}

/**
 * Building colour for each value of a metric. Signed metrics (gains vs losses) diverge from white
 * at 0 (red losses, blue gains); the rest run along plasma, by the metric's scale. Missing: grey.
 */
export function colourScale(
  metric: Pick<MetricInfo, 'scale' | 'signed'>,
  values: MetricValue[],
): (value: MetricValue) => string {
  if (metric.signed) {
    const saturatesAt = saturationBound(present(values))
    return (value) => (value === null ? MISSING_COLOUR : divergingColour(value, saturatesAt))
  }
  const position = relativePosition(metric, present(values))
  return (value) => (value === null ? MISSING_COLOUR : interpolatePlasma(position(value)))
}

function present(values: MetricValue[]): number[] {
  return values.filter((value): value is number => value !== null)
}

/** Where a value sits among the universe's values, 0 (lowest) to 1 (highest), per the metric's scale. */
function relativePosition(
  metric: Pick<MetricInfo, 'scale'>,
  values: number[],
): (value: number) => number {
  if (values.length === 0) {
    return () => 0.5
  }
  switch (metric.scale) {
    case 'percentile':
      return (value) => percentileRank(values, value)
    case 'log':
      // a log scale can't take zero or negative values: those universes fall back to linear
      return values.every((value) => value > 0)
        ? spanScale(scaleLog(), values)
        : spanScale(scaleLinear(), values)
    case 'linear':
      return spanScale(scaleLinear(), values)
  }
}

/** Lowest value → 0, highest → 1. When every value is equal, d3 puts them all at 0.5. */
function spanScale(
  scale: ReturnType<typeof scaleLinear<number>> | ReturnType<typeof scaleLog<number>>,
  values: number[],
): (value: number) => number {
  const fitted = scale
    .domain([Math.min(...values), Math.max(...values)])
    .range([0, 1])
    .clamp(true)
  return (value) => fitted(value)
}

/**
 * Share of the universe below the value, 0 to 1. Ties share the middle of their ranks, so equal
 * values get equal heights. Linear in the universe size, which is fine for hundreds of positions.
 */
function percentileRank(values: number[], value: number): number {
  if (values.length === 1) {
    return 0.5
  }
  const below = values.filter((other) => other < value).length
  const equal = values.filter((other) => other === value).length
  const rank = below + Math.max(equal - 1, 0) / 2
  return rank / (values.length - 1)
}

/** The size of move at which signed colours reach full strength. */
function saturationBound(values: number[]): number {
  const sizes = values.map(Math.abs).sort((a, b) => a - b)
  if (sizes.length === 0) {
    return 0
  }
  return sizes[Math.floor(SIGNED_SATURATION_PERCENTILE * (sizes.length - 1))]!
}

function divergingColour(value: number, saturatesAt: number): string {
  const strength = saturatesAt === 0 ? 0 : Math.max(-1, Math.min(1, value / saturatesAt))
  const along = (strength + 1) / 2 // -1 → 0 (loss), 0 → 0.5 (white), 1 → 1 (gain)
  return interpolateRdBu(DIVERGING_START + along * (DIVERGING_END - DIVERGING_START))
}
