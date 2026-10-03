import type { Brief, Instrument, MetricInfo, Universe } from '@/api/client'

/**
 * Deliberately not the S&P 500: an unclassified position and a non-equity
 * position, so code that quietly assumes SPY-shaped data fails a test.
 */
export const TEST_PORTFOLIO: Universe = {
  id: 'test-portfolio',
  name: 'Test Portfolio',
  session_date: '2026-09-25',
  positions: [
    {
      ticker: 'AAA',
      name: 'Alpha Corp',
      asset_class: 'equity',
      sector: 'Technology',
      weight: 0.5,
      last_close: 185.2,
      metrics: { day_change: 0.012, beta_1y: 1.3 },
    },
    {
      ticker: 'BBB',
      name: 'Beta Holdings',
      asset_class: 'equity',
      sector: null,
      weight: 0.3,
      last_close: 42.75,
      metrics: { day_change: -0.021, beta_1y: null },
    },
    {
      ticker: 'CCC',
      name: 'Gamma Bond Fund',
      asset_class: 'etf',
      sector: 'Fixed Income',
      weight: 0.2,
      last_close: 98.1,
      metrics: { day_change: null, beta_1y: 0.1 },
    },
  ],
}

/** A two-metric catalogue: one signed percent, one ratio. */
export const TEST_CATALOGUE: MetricInfo[] = [
  {
    key: 'day_change',
    label: 'Day change',
    unit: 'percent',
    scale: 'linear',
    refresh: 'daily',
    signed: true,
  },
  {
    key: 'beta_1y',
    label: 'Beta (1y)',
    unit: 'ratio',
    scale: 'linear',
    refresh: 'daily',
    signed: false,
  },
]

/** AAA's fundamentals, with round numbers so the formatted values are easy to check. */
export const TEST_INSTRUMENT: Instrument = {
  ticker: 'AAA',
  name: 'Alpha Corp',
  pe_ratio: 25,
  market_cap_usd: 1_500_000_000_000,
  dividend_yield: 0.005,
  earnings_yield: 0.04,
}

/** AAA's AI brief: two news points, each backed by a source. */
export const TEST_BRIEF: Brief = {
  ticker: 'AAA',
  about: 'Alpha Corp makes widgets and sells them to businesses.',
  news: ['Alpha Corp opened a new widget plant.', 'Alpha Corp named a new chief executive.'],
  sources: [
    {
      headline: 'Alpha Corp Opens Plant in Ohio',
      source: 'Yahoo',
      url: 'https://example.com/alpha-plant',
      published_at: '2026-10-02T14:00:00Z',
    },
    {
      headline: 'Alpha Corp Names New CEO',
      source: 'CNBC',
      url: 'https://example.com/alpha-ceo',
      published_at: '2026-10-01T18:30:00Z',
    },
  ],
  model: 'gemini-3.8-flash',
}
