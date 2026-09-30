import { fireEvent, render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import { TEST_CATALOGUE } from '@/__tests__/fixtures'
import MetricPicker from '../MetricPicker.vue'

function renderPicker(modelValue: string) {
  return render(MetricPicker, {
    props: { label: 'Height', metrics: TEST_CATALOGUE, modelValue },
  })
}

async function openPicker(modelValue: string) {
  const picker = renderPicker(modelValue)
  await fireEvent.keyDown(screen.getByRole('button'), { key: 'Enter' })
  return picker
}

describe('MetricPicker', () => {
  it('names the picked metric on its button', () => {
    renderPicker('beta_1y')

    expect(screen.getByRole('button', { name: 'Height: Beta (1y)' })).toBeTruthy()
  })

  it('lists every metric, with the picked one checked', async () => {
    await openPicker('beta_1y')

    const items = await screen.findAllByRole('menuitemradio')
    expect(
      items.map((item) => [item.textContent?.trim(), item.getAttribute('aria-checked')]),
    ).toEqual([
      ['Day change', 'false'],
      ['Beta (1y)', 'true'],
    ])
  })

  it('reports the key of the metric picked', async () => {
    const { emitted } = await openPicker('beta_1y')

    await fireEvent.click(await screen.findByRole('menuitemradio', { name: 'Day change' }))

    expect(emitted('update:modelValue')).toEqual([['day_change']])
  })
})
