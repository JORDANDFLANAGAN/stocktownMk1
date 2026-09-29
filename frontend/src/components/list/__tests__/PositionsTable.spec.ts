import { cleanup, fireEvent, render, screen, within } from '@testing-library/vue'
import type { SortingState } from '@tanstack/vue-table'
import { describe, expect, it } from 'vitest'

import type { MetricInfo } from '@/api/client'
import { TEST_PORTFOLIO } from '@/__tests__/fixtures'
import PositionsTable from '../PositionsTable.vue'

const METRICS: MetricInfo[] = [
  { key: 'day_change', label: 'Day change', unit: 'percent', scale: 'linear', refresh: 'daily' },
  { key: 'beta_1y', label: 'Beta (1y)', unit: 'ratio', scale: 'linear', refresh: 'daily' },
]

function renderTable(props: { sorting?: SortingState; selectedTicker?: string } = {}) {
  return render(PositionsTable, {
    props: { positions: TEST_PORTFOLIO.positions, metrics: METRICS, sorting: [], ...props },
  })
}

/** The ticker of each body row, top to bottom. */
function tickersInOrder(): string[] {
  const [, ...bodyRows] = screen.getAllByRole('row')
  return bodyRows.map((row) => within(row).getAllByRole('cell')[0]!.textContent!.trim())
}

describe('PositionsTable', () => {
  it('has the fixed columns, then one column per metric in catalogue order', () => {
    renderTable()

    const headers = screen.getAllByRole('columnheader').map((header) => header.textContent?.trim())
    expect(headers).toEqual(['Ticker', 'Name', 'Sector', 'Weight', 'Day change', 'Beta (1y)'])
  })

  it('formats each value by its unit and shows missing values as a dash', () => {
    renderTable()

    const bbbRow = screen.getByRole('row', { name: /BBB/ })
    expect(
      within(bbbRow)
        .getAllByRole('cell')
        .map((cell) => cell.textContent?.trim()),
    ).toEqual(['BBB', 'Beta Holdings', 'Unclassified', '30.00%', '−2.1%', '—'])
  })

  it('sorts by the column it is given, with missing values last either way', () => {
    renderTable({ sorting: [{ id: 'beta_1y', desc: true }] })
    expect(tickersInOrder()).toEqual(['AAA', 'CCC', 'BBB'])
    cleanup()

    renderTable({ sorting: [{ id: 'beta_1y', desc: false }] })
    expect(tickersInOrder()).toEqual(['CCC', 'AAA', 'BBB'])
  })

  it('asks for a sort when a column header is clicked', async () => {
    const { emitted } = renderTable()

    await fireEvent.click(screen.getByRole('button', { name: 'Day change' }))

    expect(emitted('update:sorting')).toEqual([[[{ id: 'day_change', desc: true }]]])
  })

  it('selects a position when its row is clicked', async () => {
    const { emitted } = renderTable()

    await fireEvent.click(screen.getByRole('row', { name: /Beta Holdings/ }))

    expect(emitted('select')).toEqual([['BBB']])
  })

  it('marks the selected position', () => {
    renderTable({ selectedTicker: 'CCC' })

    const selected = screen.getAllByRole('row').filter((row) => row.ariaSelected === 'true')
    expect(selected.map((row) => within(row).getAllByRole('cell')[0]!.textContent)).toEqual(['CCC'])
  })
})
