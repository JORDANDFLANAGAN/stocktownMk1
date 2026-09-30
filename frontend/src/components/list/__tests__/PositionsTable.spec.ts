import { cleanup, fireEvent, render, screen, within } from '@testing-library/vue'
import type { SortingState } from '@tanstack/vue-table'
import { describe, expect, it } from 'vitest'
import { nextTick } from 'vue'

import { TEST_CATALOGUE, TEST_PORTFOLIO } from '@/__tests__/fixtures'
import PositionsTable from '../PositionsTable.vue'

const EVERY_METRIC = TEST_CATALOGUE.map((metric) => metric.key)

function renderTable(
  props: { visibleMetrics?: string[]; sorting?: SortingState; selectedTicker?: string } = {},
) {
  return render(PositionsTable, {
    props: {
      positions: TEST_PORTFOLIO.positions,
      metrics: TEST_CATALOGUE,
      visibleMetrics: EVERY_METRIC,
      sorting: [],
      ...props,
    },
  })
}

function headerTexts(): (string | undefined)[] {
  return screen.getAllByRole('columnheader').map((header) => header.textContent?.trim())
}

/** The ticker of each body row, top to bottom. */
function tickersInOrder(): string[] {
  const [, ...bodyRows] = screen.getAllByRole('row')
  return bodyRows.map((row) => within(row).getAllByRole('cell')[0]!.textContent!.trim())
}

describe('PositionsTable', () => {
  it('has the fixed columns, then one column per metric in catalogue order', () => {
    renderTable()

    expect(headerTexts()).toEqual(['Ticker', 'Name', 'Sector', 'Weight', 'Day change', 'Beta (1y)'])
  })

  it('shows only the chosen metric columns, headers and cells alike', () => {
    renderTable({ visibleMetrics: ['beta_1y'] })

    const bbbRow = screen.getByRole('row', { name: /BBB/ })
    expect(headerTexts()).toEqual(['Ticker', 'Name', 'Sector', 'Weight', 'Beta (1y)'])
    expect(
      within(bbbRow)
        .getAllByRole('cell')
        .map((cell) => cell.textContent?.trim()),
    ).toEqual(['BBB', 'Beta Holdings', 'Unclassified', '30.00%', '—'])
  })

  it('keeps sorting by a metric whose column is hidden', () => {
    renderTable({ visibleMetrics: [], sorting: [{ id: 'beta_1y', desc: true }] })

    expect(tickersInOrder()).toEqual(['AAA', 'CCC', 'BBB'])
  })

  it('formats each value by its catalogue entry and shows missing values as a dash', () => {
    renderTable()

    const cellTexts = (row: HTMLElement) =>
      within(row)
        .getAllByRole('cell')
        .map((cell) => cell.textContent?.trim())
    expect(cellTexts(screen.getByRole('row', { name: /AAA/ }))).toEqual([
      'AAA',
      'Alpha Corp',
      'Technology',
      '50.00%',
      '+1.2%',
      '1.30×',
    ])
    expect(cellTexts(screen.getByRole('row', { name: /BBB/ }))).toEqual([
      'BBB',
      'Beta Holdings',
      'Unclassified',
      '30.00%',
      '−2.1%',
      '—',
    ])
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

  describe('keyboard', () => {
    /** The body rows, top to bottom (AAA, BBB, CCC unsorted). */
    function bodyRows(): HTMLTableRowElement[] {
      const [, ...rows] = screen.getAllByRole('row') as HTMLTableRowElement[]
      return rows
    }

    function tickerOf(row: Element | null): string | undefined {
      return (row as HTMLTableRowElement | null)?.cells[0]?.textContent?.trim()
    }

    function tabStops(): (string | undefined)[] {
      return bodyRows()
        .filter((row) => row.tabIndex === 0)
        .map(tickerOf)
    }

    it('puts only one row in the tab order: the selected one, else the first', () => {
      renderTable()
      expect(tabStops()).toEqual(['AAA'])
      cleanup()

      renderTable({ selectedTicker: 'CCC' })
      expect(tabStops()).toEqual(['CCC'])
    })

    it('moves focus between rows with the arrow keys, stopping at the ends', async () => {
      renderTable()
      const [first] = bodyRows()
      first!.focus()

      const focusedAfter = async (key: string) => {
        await fireEvent.keyDown(document.activeElement!, { key })
        return tickerOf(document.activeElement)
      }
      expect(await focusedAfter('ArrowUp')).toBe('AAA')
      expect(await focusedAfter('ArrowDown')).toBe('BBB')
      expect(await focusedAfter('ArrowDown')).toBe('CCC')
      expect(await focusedAfter('ArrowDown')).toBe('CCC')
      expect(await focusedAfter('ArrowUp')).toBe('BBB')
    })

    it('jumps to the first and last rows with Home and End', async () => {
      renderTable()
      bodyRows()[1]!.focus()

      await fireEvent.keyDown(document.activeElement!, { key: 'End' })
      expect(tickerOf(document.activeElement)).toBe('CCC')
      await fireEvent.keyDown(document.activeElement!, { key: 'Home' })
      expect(tickerOf(document.activeElement)).toBe('AAA')
    })

    it('keeps the tab stop on the row moved to', async () => {
      renderTable()
      bodyRows()[0]!.focus()

      await fireEvent.keyDown(document.activeElement!, { key: 'ArrowDown' })

      expect(tabStops()).toEqual(['BBB'])
    })

    it('makes a row focused by mouse or Tab the tab stop', async () => {
      renderTable()

      bodyRows()[2]!.focus()
      await nextTick()

      expect(tabStops()).toEqual(['CCC'])
    })

    it('puts focus back on its row when the selection clears (the drawer closed)', async () => {
      const { rerender } = renderTable({ selectedTicker: 'BBB' })
      ;(document.activeElement as HTMLElement | null)?.blur()

      await rerender({ selectedTicker: undefined })

      expect(tickerOf(document.activeElement)).toBe('BBB')
    })
  })
})
