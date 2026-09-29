import { fireEvent, screen } from '@testing-library/vue'
import { flushPromises } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import { renderAppAt, testPortfolioApi } from '@/__tests__/renderApp'

describe('TickerDrawer', () => {
  it('shows the name and sector of the ticker in the URL', async () => {
    await renderAppAt('/test-portfolio/list/ticker/BBB', testPortfolioApi().api)

    const drawer = await screen.findByRole('dialog', { name: 'BBB' })

    expect(drawer.textContent).toContain('Beta Holdings · Unclassified')
  })

  it('says so when the ticker is not in the universe', async () => {
    await renderAppAt('/test-portfolio/list/ticker/ZZZ', testPortfolioApi().api)

    const drawer = await screen.findByRole('dialog', { name: 'ZZZ' })

    expect(drawer.textContent).toContain('Not in Test Portfolio.')
  })

  it('closes back to the list, keeping sort and filters', async () => {
    const router = await renderAppAt(
      '/test-portfolio/list/ticker/AAA?sort=-weight&sector=Technology',
      testPortfolioApi().api,
    )

    await fireEvent.click(await screen.findByRole('button', { name: 'Close' }))
    await flushPromises()

    expect(router.currentRoute.value.fullPath).toBe(
      '/test-portfolio/list?sort=-weight&sector=Technology',
    )
    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it('closes back to the city when opened from the city', async () => {
    const router = await renderAppAt('/test-portfolio/city/ticker/AAA', testPortfolioApi().api)

    await screen.findByRole('dialog', { name: 'AAA' })
    await fireEvent.keyDown(document.activeElement ?? document.body, { key: 'Escape' })
    await flushPromises()

    expect(router.currentRoute.value.fullPath).toBe('/test-portfolio/city')
  })
})
