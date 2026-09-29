import { describe, expect, it } from 'vitest'

import type { Instrument } from '@/api/client'
import { fakeApi, piniaWith } from '@/__tests__/fakeApi'
import { useFundamentalsStore } from '../fundamentals'

function instrument(ticker: string): Instrument {
  return {
    ticker,
    name: `${ticker} Inc.`,
    pe_ratio: 20,
    market_cap_usd: 1e9,
    dividend_yield: 0.01,
    earnings_yield: 0.05,
  }
}

describe('useFundamentalsStore', () => {
  it('fetches a ticker once and serves repeat requests from the cache', async () => {
    const fetchedTickers: string[] = []
    const store = useFundamentalsStore(
      piniaWith(
        fakeApi({
          fetchInstrument: async (ticker) => {
            fetchedTickers.push(ticker)
            return instrument(ticker)
          },
        }),
      ),
    )

    await Promise.all([store.load('AAA'), store.load('AAA')]) // e.g. a double click
    await store.load('AAA')

    expect(fetchedTickers).toEqual(['AAA'])
    expect(store.entryFor('AAA')).toEqual({ loading: false, error: null, data: instrument('AAA') })
  })

  it('keeps one ticker failing from affecting another', async () => {
    const outage = new Error('provider down')
    const store = useFundamentalsStore(
      piniaWith(
        fakeApi({
          fetchInstrument: async (ticker) => {
            if (ticker === 'BBB') throw outage
            return instrument(ticker)
          },
        }),
      ),
    )

    await Promise.all([store.load('AAA'), store.load('BBB')])

    expect(store.entryFor('AAA')?.data).toEqual(instrument('AAA'))
    expect(store.entryFor('BBB')).toEqual({ loading: false, error: outage, data: null })
  })

  it('tries a failed ticker again on the next request', async () => {
    let backendIsUp = false
    const store = useFundamentalsStore(
      piniaWith(
        fakeApi({
          fetchInstrument: async (ticker) => {
            if (!backendIsUp) throw new Error('provider down')
            return instrument(ticker)
          },
        }),
      ),
    )
    await store.load('AAA')

    backendIsUp = true
    await store.load('AAA')

    expect(store.entryFor('AAA')?.data).toEqual(instrument('AAA'))
  })
})
