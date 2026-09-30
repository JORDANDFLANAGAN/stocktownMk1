import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import SectorLegend from '../SectorLegend.vue'

describe('SectorLegend', () => {
  it('shows each sector next to its colour, in the order given', () => {
    render(SectorLegend, {
      props: {
        sectors: [
          { sector: 'Energy', colour: '#8dd3c7' },
          { sector: 'Utilities', colour: '#a1a1aa' },
        ],
      },
    })

    const entries = screen
      .getAllByRole('listitem')
      .map((entry) => [
        entry.textContent?.trim(),
        entry.querySelector('span')?.style.backgroundColor,
      ])
    expect(entries).toEqual([
      ['Energy', 'rgb(141, 211, 199)'],
      ['Utilities', 'rgb(161, 161, 170)'],
    ])
  })
})
