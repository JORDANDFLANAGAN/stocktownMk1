import { describe, expect, it } from 'vitest'

import type { Position } from '@/api/client'
import type { LiveBar } from '@/api/live'
import { headlineQuote, quoteTag, type Quote } from '../quote'

const FRIDAY = '2026-09-25' // the snapshot's session
const MONDAY = '2026-09-28'

const POSITION: Position = {
  ticker: 'AAA',
  name: 'Alpha Corp',
  asset_class: 'equity',
  sector: 'Technology',
  weight: 1,
  last_close: 100,
  metrics: { day_change: 0.012 },
}

function barFrom(sessionDate: string, close: number): LiveBar {
  return {
    type: 'bar',
    ticker: 'AAA',
    minute_utc: `${sessionDate}T19:59:00Z`,
    minute_market: `${sessionDate}T15:59:00-04:00`,
    session_date: sessionDate,
    open: close,
    high: close,
    low: close,
    close,
    volume: 100,
  }
}

describe('headlineQuote', () => {
  it('measures a live bar from a later session against the last close', () => {
    expect(headlineQuote(POSITION, barFrom(MONDAY, 102), FRIDAY)).toEqual({
      price: 102,
      change: expect.closeTo(0.02),
      source: 'live',
    })
  })

  it("shows the close and its day change while the market is closed on the snapshot's session", () => {
    expect(headlineQuote(POSITION, barFrom(FRIDAY, 100.5), FRIDAY)).toEqual({
      price: 100,
      change: 0.012,
      source: 'close',
    })
  })

  it('shows the close until the first live bar arrives', () => {
    expect(headlineQuote(POSITION, null, FRIDAY)).toEqual({
      price: 100,
      change: 0.012,
      source: 'close',
    })
  })

  it('shows a live price without a change when there is no previous close', () => {
    const newListing = { ...POSITION, last_close: null }

    expect(headlineQuote(newListing, barFrom(MONDAY, 102), FRIDAY)).toEqual({
      price: 102,
      change: null,
      source: 'live',
    })
  })
})

describe('quoteTag', () => {
  const LIVE: Quote = { price: 102, change: 0.02, source: 'live' }
  const CLOSE: Quote = { price: 100, change: 0.012, source: 'close' }
  const mondayBar = barFrom(MONDAY, 102)

  it('labels a live price with its minute on the market clock', () => {
    expect(quoteTag(LIVE, mondayBar, 'live', FRIDAY)).toBe('Live · 15:59 ET')
  })

  it('labels the close with its session, and says nothing while the first bar is on its way', () => {
    expect(quoteTag(CLOSE, null, 'connecting', FRIDAY)).toBe('Close, 2026-09-25')
  })

  it('says it is reconnecting after the stream drops, keeping the last minute it had', () => {
    expect(quoteTag(LIVE, mondayBar, 'connecting', FRIDAY)).toBe('15:59 ET · reconnecting…')
  })

  it('says live prices are unavailable when the provider is down or retries run out', () => {
    expect(quoteTag(CLOSE, null, 'unavailable', FRIDAY)).toBe(
      'Close, 2026-09-25 · live prices unavailable',
    )
    expect(quoteTag(LIVE, mondayBar, 'disconnected', FRIDAY)).toBe(
      '15:59 ET · live prices unavailable',
    )
  })

  it('says when the ticker has no live prices at all', () => {
    expect(quoteTag(CLOSE, null, 'unknown-ticker', FRIDAY)).toBe(
      'Close, 2026-09-25 · no live prices for this ticker',
    )
  })
})
