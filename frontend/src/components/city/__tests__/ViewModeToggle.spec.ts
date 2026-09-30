import { fireEvent, render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import ViewModeToggle from '../ViewModeToggle.vue'

describe('ViewModeToggle', () => {
  it('offers both views, with the current one pressed', () => {
    render(ViewModeToggle, { props: { modelValue: 'top-down' } })

    const options = screen
      .getAllByRole('button')
      .map((option) => [option.textContent?.trim(), option.getAttribute('aria-pressed')])
    expect(options).toEqual([
      ['3D', 'false'],
      ['Top-down', 'true'],
    ])
  })

  it('reports the view picked', async () => {
    const { emitted } = render(ViewModeToggle, { props: { modelValue: '3d' } })

    await fireEvent.click(screen.getByRole('button', { name: 'Top-down' }))

    expect(emitted('update:modelValue')).toEqual([['top-down']])
  })
})
