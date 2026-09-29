import { describe, expect, it } from 'vitest'

import type { MetricInfo, Universe } from '@/api/client'
import { fakeApi, piniaWith } from '@/__tests__/fakeApi'
import { TEST_PORTFOLIO } from '@/__tests__/fixtures'
import { useUniverseStore } from '../universe'

const CATALOGUE: MetricInfo[] = [
  {
    key: 'day_change',
    label: 'Day change',
    unit: 'percent',
    scale: 'linear',
    refresh: 'daily',
    signed: true,
  },
]

describe('useUniverseStore', () => {
  it('loads the requested universe together with the metric catalogue', async () => {
    const requestedIds: string[] = []
    const store = useUniverseStore(
      piniaWith(
        fakeApi({
          fetchUniverse: async (universeId) => {
            requestedIds.push(universeId)
            return TEST_PORTFOLIO
          },
          fetchMetrics: async () => CATALOGUE,
        }),
      ),
    )

    await store.load('test-portfolio')

    expect(requestedIds).toEqual(['test-portfolio'])
    expect(store.positions.map((position) => position.ticker)).toEqual(['AAA', 'BBB', 'CCC'])
    expect(store.metricsCatalogue).toEqual(CATALOGUE)
  })

  it('reports loading until the data arrives', async () => {
    let arrive: (universe: Universe) => void = () => {}
    const slowUniverse = new Promise<Universe>((resolve) => (arrive = resolve))
    const store = useUniverseStore(
      piniaWith(
        fakeApi({ fetchUniverse: () => slowUniverse, fetchMetrics: async () => CATALOGUE }),
      ),
    )

    const loading = store.load('test-portfolio')
    expect(store.loading).toBe(true)

    arrive(TEST_PORTFOLIO)
    await loading
    expect(store.loading).toBe(false)
  })

  it('reports a failed load and keeps the universe already on screen', async () => {
    const outage = new Error('provider down')
    let backendIsUp = true
    const store = useUniverseStore(
      piniaWith(
        fakeApi({
          fetchUniverse: async () => {
            if (!backendIsUp) throw outage
            return TEST_PORTFOLIO
          },
          fetchMetrics: async () => CATALOGUE,
        }),
      ),
    )
    await store.load('test-portfolio')

    backendIsUp = false
    await store.load('test-portfolio')

    expect(store.error).toBe(outage)
    expect(store.loading).toBe(false)
    expect(store.positions).toHaveLength(3)
  })
})
