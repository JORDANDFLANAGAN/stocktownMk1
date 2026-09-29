import { fireEvent, render, screen } from '@testing-library/vue'
import { flushPromises } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import { TEST_CATALOGUE } from '@/__tests__/fixtures'
import ColumnPicker from '../ColumnPicker.vue'

async function openPickerShowing(visibleMetrics: string[]) {
  const picker = render(ColumnPicker, { props: { metrics: TEST_CATALOGUE, visibleMetrics } })
  await fireEvent.keyDown(screen.getByRole('button', { name: 'Columns' }), { key: 'Enter' })
  return picker
}

describe('ColumnPicker', () => {
  it('lists every metric, ticked when its column is shown', async () => {
    await openPickerShowing(['beta_1y'])

    const items = await screen.findAllByRole('menuitemcheckbox')
    expect(
      items.map((item) => [item.textContent?.trim(), item.getAttribute('aria-checked')]),
    ).toEqual([
      ['Day change', 'false'],
      ['Beta (1y)', 'true'],
    ])
  })

  it('adds a column in catalogue order, whatever order it is ticked in', async () => {
    const { emitted } = await openPickerShowing(['beta_1y'])

    await fireEvent.click(await screen.findByRole('menuitemcheckbox', { name: 'Day change' }))

    expect(emitted('update:visibleMetrics')).toEqual([[['day_change', 'beta_1y']]])
  })

  it('stays open after a tick, so several columns can be changed in one go', async () => {
    await openPickerShowing([])

    await fireEvent.click(await screen.findByRole('menuitemcheckbox', { name: 'Day change' }))
    await flushPromises()

    expect(screen.queryByRole('menuitemcheckbox', { name: 'Beta (1y)' })).not.toBeNull()
  })

  it('removes a column when it is unticked', async () => {
    const { emitted } = await openPickerShowing(['day_change', 'beta_1y'])

    await fireEvent.click(await screen.findByRole('menuitemcheckbox', { name: 'Day change' }))

    expect(emitted('update:visibleMetrics')).toEqual([[['beta_1y']]])
  })
})
