import { render } from '@testing-library/vue'
import { createPinia } from 'pinia'
import { createMemoryHistory } from 'vue-router'

import type { Api } from '@/api/client'
import App from '@/App.vue'
import { API_KEY } from '@/composables/useApi'
import { createAppRouter } from '@/router'
import { fakeApi } from './fakeApi'
import { TEST_PORTFOLIO } from './fixtures'

/** Renders the whole app at a URL, wired like main.ts but with memory history and the given Api. */
export async function renderAppAt(url: string, api: Api) {
  const router = createAppRouter(createMemoryHistory())
  await router.push(url)
  render(App, { global: { plugins: [router, createPinia()], provide: { [API_KEY]: api } } })
  return router
}

/** An Api serving TEST_PORTFOLIO and recording which universes were requested. */
export function testPortfolioApi() {
  const requestedUniverses: string[] = []
  const api = fakeApi({
    fetchUniverse: async (universeId) => {
      requestedUniverses.push(universeId)
      return TEST_PORTFOLIO
    },
    fetchMetrics: async () => [],
  })
  return { api, requestedUniverses }
}
