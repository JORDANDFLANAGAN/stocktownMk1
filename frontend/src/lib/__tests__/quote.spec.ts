import { describe, expect, it } from 'vitest'

import type { Position } from '@/api/client'
import type { LiveBar } from '@/api/live'
import { headlineQuote } from '../quote'

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
