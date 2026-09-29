import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import { TEST_CATALOGUE, TEST_PORTFOLIO } from '@/__tests__/fixtures'
import CityMetricsSection from '../CityMetricsSection.vue'

function renderSectionFor(ticker: string) {
  const position = TEST_PORTFOLIO.positions.find((candidate) => candidate.ticker === ticker)!
  render(CityMetricsSection, {
    props: { position, metrics: TEST_CATALOGUE, sessionDate: '2026-09-25' },
  })
}

/** Each metric label with its displayed value, in the order shown. */
function shownMetrics(): [string | undefined, string | undefined][] {
  const labels = screen.getAllByRole('term').map((term) => term.textContent?.trim())
  const values = screen.getAllByRole('definition').map((value) => value.textContent?.trim())
  return labels.map((label, index) => [label, values[index]])
}

describe('CityMetricsSection', () => {
  it('lists every catalogue metric in order, formatted by its unit and sign', () => {
    renderSectionFor('AAA')

    expect(shownMetrics()).toEqual([
      ['Day change', '+1.2%'],
      ['Beta (1y)', '1.30×'],
    ])
  })

  it('shows a dash for a metric the position has no value for', () => {
    renderSectionFor('BBB')

    expect(shownMetrics()).toEqual([
      ['Day change', '−2.1%'],
      ['Beta (1y)', '—'],
    ])
  })

  it('says the metrics are from the close of the snapshot session', () => {
    renderSectionFor('AAA')

    expect(screen.getByText('At the close, 2026-09-25')).toBeTruthy()
  })
})
