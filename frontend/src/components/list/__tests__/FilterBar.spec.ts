import { fireEvent, render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import FilterBar from '../FilterBar.vue'

const ALL_SECTORS = ['Fixed Income', 'Technology', 'Unclassified']

function renderFilterBar(props: { sectors?: string[]; search?: string } = {}) {
  return render(FilterBar, {
    props: { allSectors: ALL_SECTORS, sectors: [], search: '', ...props },
  })
}

describe('FilterBar', () => {
  it('offers every sector and marks the chosen ones', () => {
    renderFilterBar({ sectors: ['Technology'] })

    const pressed = screen
      .getAllByRole('button')
      .map((chip) => [chip.textContent?.trim(), chip.getAttribute('aria-pressed')])
    expect(pressed).toEqual([
      ['Fixed Income', 'false'],
      ['Technology', 'true'],
      ['Unclassified', 'false'],
    ])
  })

  it('adds a sector when its chip is clicked and removes it on a second click', async () => {
    const { emitted, rerender } = renderFilterBar({ sectors: ['Technology'] })

    await fireEvent.click(screen.getByRole('button', { name: 'Unclassified' }))
    await rerender({ sectors: ['Technology', 'Unclassified'] })
    await fireEvent.click(screen.getByRole('button', { name: 'Technology' }))

    expect(emitted('update:sectors')).toEqual([
      [['Technology', 'Unclassified']],
      [['Unclassified']],
    ])
  })

  it('reports the search text as it is typed, starting from the current search', async () => {
    const { emitted } = renderFilterBar({ search: 'al' })
    const input = screen.getByRole('searchbox', { name: 'Search ticker or name' })
    expect((input as HTMLInputElement).value).toBe('al')

    await fireEvent.update(input, 'alp')

    expect(emitted('update:search')).toEqual([['alp']])
  })
})
