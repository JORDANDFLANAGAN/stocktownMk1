const LOCALE = 'en-US'
const MINUS_SIGN = '−' // typographic minus: same width as "+", so columns line up
const NO_VALUE = '—'

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

/** Formats a metric value by its catalogue unit; "—" when the metric has no value for this position. */
export function formatMetricValue(value: number | null, unit: string): string {
  if (value === null) {
    return NO_VALUE
  }
  return unit === 'percent' ? formatPercent(value) : formatRatio(value)
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
