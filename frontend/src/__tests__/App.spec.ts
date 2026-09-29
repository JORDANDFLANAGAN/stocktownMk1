import { cleanup, fireEvent, render, screen } from '@testing-library/vue'
import { createPinia } from 'pinia'
import { afterEach, describe, expect, it } from 'vitest'
import { createMemoryHistory } from 'vue-router'

import { ApiError, type Api } from '@/api/client'
import { API_KEY } from '@/composables/useApi'
import { createAppRouter } from '@/router'
import App from '@/App.vue'
import { fakeApi } from './fakeApi'
import { TEST_PORTFOLIO } from './fixtures'

/** Renders the whole app at a URL, wired like main.ts but with memory history and the given Api. */
async function renderAppAt(url: string, api: Api) {
  const router = createAppRouter(createMemoryHistory())
  await router.push(url)
  render(App, { global: { plugins: [router, createPinia()], provide: { [API_KEY]: api } } })
  return router
}

/** An Api serving TEST_PORTFOLIO and recording which universes were requested. */
function testPortfolioApi() {
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

describe('App', () => {
  afterEach(cleanup)

  it('opens the default universe as a list at the root URL', async () => {
    const { api, requestedUniverses } = testPortfolioApi()

    const router = await renderAppAt('/', api)

    expect(router.currentRoute.value.fullPath).toBe('/spy/list')
    expect(requestedUniverses).toEqual(['spy'])
  })

  it('loads the universe named in the URL and titles the page with it', async () => {
    const { api, requestedUniverses } = testPortfolioApi()

    await renderAppAt('/test-portfolio/list', api)

    expect(await screen.findByRole('heading', { name: 'Test Portfolio' })).toBeTruthy()
    expect(requestedUniverses).toEqual(['test-portfolio'])
  })

  it('opens a deep link to a ticker with the list behind the drawer', async () => {
    await renderAppAt('/test-portfolio/list/ticker/AAA', testPortfolioApi().api)

    expect(await screen.findByRole('heading', { name: 'AAA' })).toBeTruthy()
    expect(screen.getByText(/List view: 3 positions/)).toBeTruthy()
  })

  it('keeps the query when switching between list and city', async () => {
    const router = await renderAppAt(
      '/test-portfolio/list?sector=Technology',
      testPortfolioApi().api,
    )

    await fireEvent.click(await screen.findByRole('link', { name: 'City' }))
    await screen.findByText(/City view/)

    expect(router.currentRoute.value.fullPath).toBe('/test-portfolio/city?sector=Technology')
  })

  it('says so when the universe does not exist', async () => {
    const api = fakeApi({
      fetchUniverse: async () => {
        throw new ApiError(404, null)
      },
      fetchMetrics: async () => [],
    })

    await renderAppAt('/nope/list', api)

    expect(await screen.findByText('There is no universe called "nope".')).toBeTruthy()
  })

  it('offers a retry when loading fails, and recovers', async () => {
    let backendIsUp = false
    const api = fakeApi({
      fetchUniverse: async () => {
        if (!backendIsUp) throw new ApiError(503, 30)
        return TEST_PORTFOLIO
      },
      fetchMetrics: async () => [],
    })
    await renderAppAt('/test-portfolio/list', api)

    backendIsUp = true
    await fireEvent.click(await screen.findByRole('button', { name: 'Try again' }))

    expect(await screen.findByRole('heading', { name: 'Test Portfolio' })).toBeTruthy()
  })
})
