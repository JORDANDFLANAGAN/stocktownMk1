import { scaleLinear, scaleLog } from 'd3-scale'

import type { MetricInfo } from '@/api/client'

export const MIN_HEIGHT = 1
export const MAX_HEIGHT = 20

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
