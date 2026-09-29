import { fireEvent, render, screen } from '@testing-library/vue'
import { flushPromises } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError, type Api } from '@/api/client'
import { fakeApi } from '@/__tests__/fakeApi'
import { TEST_INSTRUMENT } from '@/__tests__/fixtures'
import { API_KEY } from '@/composables/useApi'
import FundamentalsSection from '../FundamentalsSection.vue'

const SETTLE_MS = 300

/** An Api that records each ticker it is asked about and answers with `answer`. */
function recordingApi(answer: (ticker: string) => Promise<typeof TEST_INSTRUMENT>) {
  const fetchedTickers: string[] = []
  const api = fakeApi({
    fetchInstrument: (ticker) => {
      fetchedTickers.push(ticker)
      return answer(ticker)
    },
  })
  return { api, fetchedTickers }
}

function renderSection(ticker: string, api: Api) {
  return render(FundamentalsSection, {
    props: { ticker },
    global: { plugins: [createPinia()], provide: { [API_KEY]: api } },
  })
}

/** Each label with its displayed value, in the order shown. */
function shownRows(): [string | undefined, string | undefined][] {
  const labels = screen.getAllByRole('term').map((term) => term.textContent?.trim())
  const values = screen.getAllByRole('definition').map((value) => value.textContent?.trim())
  return labels.map((label, index) => [label, values[index]])
}

describe('FundamentalsSection', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => vi.useRealTimers())

  it('waits for the drawer to settle on a ticker before fetching', async () => {
    const { api, fetchedTickers } = recordingApi(async () => TEST_INSTRUMENT)
    renderSection('AAA', api)

    await vi.advanceTimersByTimeAsync(SETTLE_MS - 1)
    expect(fetchedTickers).toEqual([])

    await vi.advanceTimersByTimeAsync(1)
    expect(fetchedTickers).toEqual(['AAA'])
  })

  it('fetches only the ticker the drawer settles on when flicking through rows', async () => {
    const { api, fetchedTickers } = recordingApi(async () => TEST_INSTRUMENT)
    const { rerender } = renderSection('AAA', api)

    await vi.advanceTimersByTimeAsync(100)
    await rerender({ ticker: 'BBB' })
    await vi.advanceTimersByTimeAsync(100)
    await rerender({ ticker: 'CCC' })
    await vi.advanceTimersByTimeAsync(SETTLE_MS)

    expect(fetchedTickers).toEqual(['CCC'])
  })

  it('fetches nothing when the drawer closes before settling', async () => {
    const { api, fetchedTickers } = recordingApi(async () => TEST_INSTRUMENT)
    const { unmount } = renderSection('AAA', api)

    await vi.advanceTimersByTimeAsync(100)
    unmount()
    await vi.advanceTimersByTimeAsync(SETTLE_MS)

    expect(fetchedTickers).toEqual([])
  })

  it('shows a placeholder while loading, then the formatted fundamentals', async () => {
    const { api } = recordingApi(async () => TEST_INSTRUMENT)
    renderSection('AAA', api)
    expect(screen.getByLabelText('Loading fundamentals')).toBeTruthy()

    await vi.advanceTimersByTimeAsync(SETTLE_MS)
    await flushPromises()

    expect(shownRows()).toEqual([
      ['Market cap', '$1.5T'],
      ['P/E', '25.0×'],
      ['Earnings yield', '4.0%'],
      ['Dividend yield', '0.50%'],
    ])
  })

  it('shows a dash for a figure the provider does not have, e.g. a loss-maker’s P/E', async () => {
    const lossMaker = { ...TEST_INSTRUMENT, pe_ratio: null, earnings_yield: -0.02 }
    const { api } = recordingApi(async () => lossMaker)
    renderSection('AAA', api)

    await vi.advanceTimersByTimeAsync(SETTLE_MS)
    await flushPromises()

    expect(shownRows()).toContainEqual(['P/E', '—'])
    expect(shownRows()).toContainEqual(['Earnings yield', '−2.0%'])
  })

  it('says so when there are no fundamentals for the ticker', async () => {
    const { api } = recordingApi(async () => {
      throw new ApiError(404, null)
    })
    renderSection('AAA', api)

    await vi.advanceTimersByTimeAsync(SETTLE_MS)
    await flushPromises()

    expect(screen.getByText('No fundamentals for this ticker.')).toBeTruthy()
  })

  it('offers a retry when the provider is unavailable, and recovers', async () => {
    let providerIsUp = false
    const { api, fetchedTickers } = recordingApi(async () => {
      if (!providerIsUp) throw new ApiError(503, 60)
      return TEST_INSTRUMENT
    })
    renderSection('AAA', api)
    await vi.advanceTimersByTimeAsync(SETTLE_MS)
    await flushPromises()

    providerIsUp = true
    await fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    await flushPromises()

    expect(fetchedTickers).toEqual(['AAA', 'AAA'])
    expect(shownRows()).toContainEqual(['Market cap', '$1.5T'])
  })
})
