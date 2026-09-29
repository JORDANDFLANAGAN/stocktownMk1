import { fireEvent, screen, within } from '@testing-library/vue'
import { flushPromises } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import { recordingSockets } from '@/__tests__/fakeSocket'
import { renderAppAt, testPortfolioApi } from '@/__tests__/renderApp'

describe('TickerDrawer', () => {
  it('shows the name and sector of the ticker in the URL', async () => {
    await renderAppAt('/test-portfolio/list/ticker/BBB', testPortfolioApi().api)

    const drawer = await screen.findByRole('dialog', { name: 'BBB' })

    expect(drawer.textContent).toContain('Beta Holdings · Unclassified')
  })

  it('shows the last close and its day change until a live bar arrives', async () => {
    await renderAppAt('/test-portfolio/list/ticker/AAA', testPortfolioApi().api)

    const drawer = await screen.findByRole('dialog', { name: 'AAA' })

    expect(drawer.textContent).toContain('$185.20')
    expect(drawer.textContent).toContain('+1.2%')
    expect(drawer.textContent).toContain('Close, 2026-09-25')
  })

  it('shows the live price and its change since the last close during a new session', async () => {
    const { openSocket, latestSocket } = recordingSockets()
    await renderAppAt('/test-portfolio/list/ticker/AAA', testPortfolioApi().api, { openSocket })
    const drawer = await screen.findByRole('dialog', { name: 'AAA' })

    latestSocket().sendBar('AAA', 188.904) // Monday, 2% above Friday's 185.20
    await flushPromises()

    expect(latestSocket().url).toBe('/api/live?ticker=AAA')
    expect(drawer.textContent).toContain('$188.90')
    expect(drawer.textContent).toContain('+2.0%')
    expect(drawer.textContent).toContain('Live')
    expect(drawer.textContent).not.toContain('Close, 2026-09-25')
  })

  it("lists every metric in the catalogue with the position's values", async () => {
    await renderAppAt('/test-portfolio/list/ticker/AAA?cols=beta_1y', testPortfolioApi().api)

    const metrics = await screen.findByRole('region', { name: 'Metrics' })

    expect(metrics.textContent).toContain('Day change')
    expect(metrics.textContent).toContain('+1.2%')
    expect(metrics.textContent).toContain('Beta (1y)')
    expect(metrics.textContent).toContain('1.30×')
  })

  it('loads the fundamentals of the ticker it opens on', async () => {
    await renderAppAt('/test-portfolio/list/ticker/AAA', testPortfolioApi().api)

    const fundamentals = await screen.findByRole('region', { name: 'Fundamentals' })

    expect(await within(fundamentals).findByText('$1.5T')).toBeTruthy()
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

  it('switches to another row clicked while open, without closing in between', async () => {
    const router = await renderAppAt('/test-portfolio/list/ticker/AAA', testPortfolioApi().api)
    await screen.findByRole('dialog', { name: 'AAA' })
    await new Promise((resolve) => setTimeout(resolve, 0)) // reka listens for outside presses a tick after opening
    const visited: string[] = []
    router.afterEach((to) => {
      visited.push(to.fullPath)
    })

    // a real click: the press and the click both land on the row
    const bbbRow = screen.getByRole('row', { name: /Beta Holdings/ })
    await fireEvent.pointerDown(bbbRow)
    await fireEvent.click(bbbRow)
    await flushPromises()

    expect(visited).toEqual(['/test-portfolio/list/ticker/BBB'])
    expect(screen.getByRole('dialog', { name: 'BBB' })).toBeTruthy()
  })

  it('closes back to the city when opened from the city', async () => {
    const router = await renderAppAt('/test-portfolio/city/ticker/AAA', testPortfolioApi().api)

    await screen.findByRole('dialog', { name: 'AAA' })
    await fireEvent.keyDown(document.activeElement ?? document.body, { key: 'Escape' })
    await flushPromises()

    expect(router.currentRoute.value.fullPath).toBe('/test-portfolio/city')
  })
})
