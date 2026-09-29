import { describe, expect, it } from 'vitest'

import {
  formatCompactMoney,
  formatMetricValue,
  formatPercent,
  formatPrice,
  formatRatio,
} from '../format'

const MINUS = '−' // U+2212, not the hyphen on the keyboard

describe('formatPercent', () => {
  it('shows a fraction as a percentage with one decimal place', () => {
    expect(formatPercent(0.123)).toBe('12.3%')
    expect(formatPercent(0)).toBe('0.0%')
    expect(formatPercent(1.5)).toBe('150.0%')
  })

  it('uses a true minus sign for losses', () => {
    expect(formatPercent(-0.004)).toBe(`${MINUS}0.4%`)
  })

  it('marks gains with a plus only when asked', () => {
    expect(formatPercent(0.012)).toBe('1.2%')
    expect(formatPercent(0.012, { showPlus: true })).toBe('+1.2%')
    expect(formatPercent(-0.012, { showPlus: true })).toBe(`${MINUS}1.2%`)
  })

  it('never puts a sign on a value that rounds to zero', () => {
    expect(formatPercent(-0.0004)).toBe('0.0%')
    expect(formatPercent(0.0004, { showPlus: true })).toBe('0.0%')
  })
})

describe('formatPrice', () => {
  it('shows dollars and cents with thousands separators', () => {
    expect(formatPrice(185.2)).toBe('$185.20')
    expect(formatPrice(1234.567)).toBe('$1,234.57')
  })
})

describe('formatCompactMoney', () => {
  it('shortens large amounts to three significant figures', () => {
    expect(formatCompactMoney(4_961_438_000_000)).toBe('$4.96T')
    expect(formatCompactMoney(375_612_000_000)).toBe('$376B')
    expect(formatCompactMoney(12_340_000_000)).toBe('$12.3B')
    expect(formatCompactMoney(850_000_000)).toBe('$850M')
  })
})

describe('formatRatio', () => {
  it('shows a multiple with two decimal places', () => {
    expect(formatRatio(1.05)).toBe('1.05×')
    expect(formatRatio(1234.5)).toBe('1,234.50×')
    expect(formatRatio(-0.3)).toBe(`${MINUS}0.30×`)
  })
})

describe('formatMetricValue', () => {
  const VOLATILITY = { unit: 'percent', signed: false } as const
  const BETA = { unit: 'ratio', signed: false } as const
  const RETURN = { unit: 'percent', signed: true } as const

  it('formats by the metric unit from the catalogue', () => {
    expect(formatMetricValue(0.1, VOLATILITY)).toBe('10.0%')
    expect(formatMetricValue(1.2, BETA)).toBe('1.20×')
  })

  it('marks gains with a plus only on signed metrics', () => {
    expect(formatMetricValue(0.1, RETURN)).toBe('+10.0%')
    expect(formatMetricValue(-0.1, RETURN)).toBe(`${MINUS}10.0%`)
    expect(formatMetricValue(0.1, VOLATILITY)).toBe('10.0%')
  })

  it('shows a dash when the position has no value for the metric', () => {
    expect(formatMetricValue(null, VOLATILITY)).toBe('—')
  })
})
