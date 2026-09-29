import type { MetricInfo } from '@/api/client'

const LOCALE = 'en-US'
const MINUS_SIGN = '−' // typographic minus: same width as "+", so columns line up
const NO_VALUE = '—'

const PRICE_FORMAT = new Intl.NumberFormat(LOCALE, { style: 'currency', currency: 'USD' })

/** 185.2 → "$185.20" */
export function formatPrice(dollars: number): string {
  return PRICE_FORMAT.format(dollars)
}

const COMPACT_MONEY_FORMAT = new Intl.NumberFormat(LOCALE, {
  style: 'currency',
  currency: 'USD',
  notation: 'compact',
  maximumSignificantDigits: 3,
})

/** 4_961_438_000_000 → "$4.96T", 375_612_000_000 → "$376B" */
export function formatCompactMoney(dollars: number): string {
  return COMPACT_MONEY_FORMAT.format(dollars)
}

/** 0.123 → "12.3%". `showPlus` marks gains ("+1.2%"). */
export function formatPercent(fraction: number, { digits = 1, showPlus = false } = {}): string {
  const options: Intl.NumberFormatOptions = {
    style: 'percent',
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }
  return formatWithSign(fraction, options, showPlus)
}

/** 1.05 → "1.05×" */
export function formatRatio(value: number, digits = 2): string {
  const options: Intl.NumberFormatOptions = {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }
  return `${formatWithSign(value, options, false)}×`
}

/**
 * Formats a metric value by its catalogue entry: its unit, and a "+" on gains when the metric is
 * signed. "—" when the metric has no value for this position.
 */
export function formatMetricValue(
  value: number | null,
  metric: Pick<MetricInfo, 'unit' | 'signed'>,
): string {
  return formatOrDash(value, (present) =>
    metric.unit === 'percent'
      ? formatPercent(present, { showPlus: metric.signed })
      : formatRatio(present),
  )
}

/** Formats a value that may be missing; missing shows as "—". */
export function formatOrDash(value: number | null, format: (value: number) => string): string {
  return value === null ? NO_VALUE : format(value)
}

/** Uses a typographic minus, and never puts a sign on a value that rounds to zero. */
function formatWithSign(
  value: number,
  options: Intl.NumberFormatOptions,
  showPlus: boolean,
): string {
  const text = new Intl.NumberFormat(LOCALE, { ...options, signDisplay: 'exceptZero' })
    .format(value)
    .replace('-', MINUS_SIGN)
  return showPlus ? text : text.replace('+', '')
}
