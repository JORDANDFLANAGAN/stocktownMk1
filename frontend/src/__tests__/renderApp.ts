import { render } from '@testing-library/vue'
import { createPinia } from 'pinia'
import { createMemoryHistory } from 'vue-router'

import { ApiError, type Api } from '@/api/client'
import App from '@/App.vue'
import { API_KEY } from '@/composables/useApi'
import { OPEN_SOCKET_KEY, type OpenSocket } from '@/composables/useLiveBar'
import { createAppRouter } from '@/router'
import { fakeApi } from './fakeApi'
import { recordingSockets } from './fakeSocket'
import { TEST_BRIEF, TEST_CATALOGUE, TEST_INSTRUMENT, TEST_PORTFOLIO } from './fixtures'

/**
 * Renders the whole app at a URL, wired like main.ts but with memory history, the given Api and
 * fake live sockets (by default ones the server never speaks on).
 */
export async function renderAppAt(
  url: string,
  api: Api,
  { openSocket = recordingSockets().openSocket }: { openSocket?: OpenSocket } = {},
) {
  const router = createAppRouter(createMemoryHistory())
  await router.push(url)
  render(App, {
    global: {
      plugins: [router, createPinia()],
      provide: { [API_KEY]: api, [OPEN_SOCKET_KEY]: openSocket },
    },
  })
  return router
}

/**
 * An Api serving TEST_PORTFOLIO, TEST_CATALOGUE and AAA's fundamentals and brief (other tickers: 404),
 * recording which universes were requested.
 */
export function testPortfolioApi() {
  const requestedUniverses: string[] = []
  const api = fakeApi({
    fetchUniverse: async (universeId) => {
      requestedUniverses.push(universeId)
      return TEST_PORTFOLIO
    },
    fetchMetrics: async () => TEST_CATALOGUE,
    fetchInstrument: async (ticker) => {
      if (ticker !== TEST_INSTRUMENT.ticker) throw new ApiError(404, null)
      return TEST_INSTRUMENT
    },
    fetchBrief: async (ticker) => {
      if (ticker !== TEST_BRIEF.ticker) throw new ApiError(404, null)
      return TEST_BRIEF
    },
  })
  return { api, requestedUniverses }
}
