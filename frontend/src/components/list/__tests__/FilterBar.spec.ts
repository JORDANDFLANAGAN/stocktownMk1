import { fireEvent, render, screen } from '@testing-library/vue'
import { flushPromises } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import FilterBar from '../FilterBar.vue'

const ALL_SECTORS = ['Fixed Income', 'Technology', 'Unclassified']

function renderFilterBar(props: { sectors?: string[]; search?: string } = {}) {
  return render(FilterBar, {
    props: { allSectors: ALL_SECTORS, sectors: [], search: '', ...props },
  })
}

describe('FilterBar', () => {
  it('passes on the sectors picked in the dropdown', async () => {
    const { emitted } = renderFilterBar({ sectors: ['Technology'] })

    await fireEvent.click(screen.getByRole('button', { name: 'Technology' }))
    await flushPromises()
    await fireEvent.click(screen.getByRole('option', { name: 'Unclassified' }))

    expect(emitted('update:sectors')).toEqual([[['Technology', 'Unclassified']]])
  })

  it('reports the search text as it is typed, starting from the current search', async () => {
    const { emitted } = renderFilterBar({ search: 'al' })
    const input = screen.getByRole('searchbox', { name: 'Search ticker or name' })
    expect((input as HTMLInputElement).value).toBe('al')

    await fireEvent.update(input, 'alp')

    expect(emitted('update:search')).toEqual([['alp']])
  })
})
