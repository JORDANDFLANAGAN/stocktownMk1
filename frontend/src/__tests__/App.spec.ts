import { cleanup, fireEvent, screen } from '@testing-library/vue'
import { flushPromises } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

import { ApiError } from '@/api/client'
import { fakeApi } from './fakeApi'
import { TEST_PORTFOLIO } from './fixtures'
import { renderAppAt, testPortfolioApi } from './renderApp'

describe('App', () => {
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
    expect(screen.getByText('Showing 3 of 3')).toBeTruthy()
  })

  it('keeps the query when switching between list and city', async () => {
    const router = await renderAppAt(
      '/test-portfolio/list?sector=Technology',
      testPortfolioApi().api,
    )

    await fireEvent.click(await screen.findByRole('link', { name: 'Town' }))

    await vi.waitFor(() =>
      expect(router.currentRoute.value.fullPath).toBe('/test-portfolio/town?sector=Technology'),
    )
  })

  it('points to the list, keeping the query, when the browser cannot draw the 3D city', async () => {
    // the test environment has no WebGL 2, like a browser without it
    await renderAppAt('/test-portfolio/town?sector=Technology', testPortfolioApi().api)

    const listLink = await screen.findByRole('link', { name: 'The list' })

    expect(screen.getByText(/needs WebGL 2/)).toBeTruthy()
    expect(listLink.getAttribute('href')).toBe('/test-portfolio/list?sector=Technology')
  })

  it('applies the filters in the URL to the list', async () => {
    await renderAppAt('/test-portfolio/list?sector=Technology', testPortfolioApi().api)

    expect(await screen.findByText('Showing 1 of 3')).toBeTruthy()
  })

  it('records a column sort in the URL', async () => {
    const router = await renderAppAt('/test-portfolio/list', testPortfolioApi().api)

    await fireEvent.click(await screen.findByRole('button', { name: 'Name' }))
    await flushPromises()

    expect(router.currentRoute.value.fullPath).toBe('/test-portfolio/list?sort=name')
  })

  it('shows the default metric columns, or the ones named in the URL', async () => {
    await renderAppAt('/test-portfolio/list', testPortfolioApi().api)
    expect(await screen.findByRole('columnheader', { name: 'Day change' })).toBeTruthy()
    expect(screen.queryByRole('columnheader', { name: 'Beta (1y)' })).toBeNull()
    cleanup()

    await renderAppAt('/test-portfolio/list?cols=beta_1y', testPortfolioApi().api)
    expect(await screen.findByRole('columnheader', { name: 'Beta (1y)' })).toBeTruthy()
    expect(screen.queryByRole('columnheader', { name: 'Day change' })).toBeNull()
  })

  it('adds a ticked metric column to the table and the URL', async () => {
    const router = await renderAppAt('/test-portfolio/list?sort=name', testPortfolioApi().api)

    await fireEvent.keyDown(await screen.findByRole('button', { name: 'Columns' }), {
      key: 'Enter',
    })
    const betaItem = await screen.findByRole('menuitemcheckbox', { name: 'Beta (1y)' })
    await fireEvent.click(betaItem)
    await fireEvent.keyDown(betaItem, { key: 'Escape' }) // close the menu
    await flushPromises()

    expect(router.currentRoute.value.fullPath).toBe(
      '/test-portfolio/list?sort=name&cols=day_change&cols=beta_1y',
    )
    expect(screen.getByRole('columnheader', { name: 'Beta (1y)' })).toBeTruthy()
  })

  it('opens the drawer for a clicked row, keeping the sort and filters', async () => {
    const router = await renderAppAt('/test-portfolio/list?sort=-weight', testPortfolioApi().api)

    await fireEvent.click(await screen.findByRole('row', { name: /Beta Holdings/ }))
    await screen.findByRole('heading', { name: 'BBB' })

    expect(router.currentRoute.value.fullPath).toBe('/test-portfolio/list/ticker/BBB?sort=-weight')
  })

  it('shows that the snapshot is being built while the data loads', async () => {
    const api = fakeApi({
      fetchUniverse: () => new Promise(() => {}), // still building
      fetchMetrics: async () => [],
    })

    await renderAppAt('/test-portfolio/list', api)

    expect(await screen.findByText(/Building today's snapshot/)).toBeTruthy()
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
