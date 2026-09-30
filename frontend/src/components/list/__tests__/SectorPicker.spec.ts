import { fireEvent, render, screen } from '@testing-library/vue'
import { flushPromises } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import SectorPicker from '../SectorPicker.vue'

const ALL_SECTORS = ['Fixed Income', 'Technology', 'Unclassified']

function renderPicker(sectors: string[]) {
  return render(SectorPicker, { props: { allSectors: ALL_SECTORS, sectors } })
}

async function openPickerChoosing(sectors: string[]) {
  const picker = renderPicker(sectors)
  await fireEvent.click(screen.getByRole('button'))
  await flushPromises()
  return picker
}

function shownOptions(): [string | undefined, string | null][] {
  return screen
    .getAllByRole('option')
    .map((option) => [option.textContent?.trim(), option.getAttribute('aria-selected')])
}

describe('SectorPicker', () => {
  it('lists every sector, ticked when chosen', async () => {
    await openPickerChoosing(['Technology'])

    expect(shownOptions()).toEqual([
      ['Fixed Income', 'false'],
      ['Technology', 'true'],
      ['Unclassified', 'false'],
    ])
  })

  it("adds a sector in the universe's order, whatever order it is ticked in", async () => {
    const { emitted } = await openPickerChoosing(['Unclassified'])

    await fireEvent.click(screen.getByRole('option', { name: 'Fixed Income' }))

    expect(emitted('update:sectors')).toEqual([[['Fixed Income', 'Unclassified']]])
  })

  it('removes a sector when it is unticked', async () => {
    const { emitted } = await openPickerChoosing(['Technology', 'Unclassified'])

    await fireEvent.click(screen.getByRole('option', { name: 'Technology' }))

    expect(emitted('update:sectors')).toEqual([[['Unclassified']]])
  })

  it('narrows the list to the sectors matching the search, ignoring case', async () => {
    await openPickerChoosing([])

    await fireEvent.update(screen.getByRole('combobox', { name: 'Search sectors' }), 'tech')

    expect(shownOptions()).toEqual([['Technology', 'false']])
  })

  it('stays open after a tick, so several sectors can be changed in one go', async () => {
    await openPickerChoosing([])

    await fireEvent.click(screen.getByRole('option', { name: 'Technology' }))
    await flushPromises()

    expect(screen.queryByRole('option', { name: 'Fixed Income' })).not.toBeNull()
  })

  it('names its button after the choice', async () => {
    const { rerender } = renderPicker([])
    expect(screen.getByRole('button', { name: 'All sectors' })).toBeTruthy()

    await rerender({ sectors: ['Technology'] })
    expect(screen.getByRole('button', { name: 'Technology' })).toBeTruthy()

    await rerender({ sectors: ['Technology', 'Unclassified'] })
    expect(screen.getByRole('button', { name: '2 sectors' })).toBeTruthy()
  })

  it('can be reached with the Tab key', () => {
    renderPicker([])

    expect(screen.getByRole('button', { name: 'All sectors' }).tabIndex).toBe(0)
  })
})
