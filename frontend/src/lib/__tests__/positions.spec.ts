import { describe, expect, it } from 'vitest'

import type { Position } from '@/api/client'
import { TEST_PORTFOLIO } from '@/__tests__/fixtures'
import { filterPositions, sectorsIn } from '../positions'

const POSITIONS = TEST_PORTFOLIO.positions // AAA Technology, BBB no sector, CCC Fixed Income

function tickers(positions: Position[]): string[] {
  return positions.map((position) => position.ticker)
}

describe('filterPositions', () => {
  it('keeps every position when no filter is set', () => {
    expect(tickers(filterPositions(POSITIONS, { sectors: [], search: '' }))).toEqual([
      'AAA',
      'BBB',
      'CCC',
    ])
  })

  it('keeps only the chosen sectors, with Unclassified meaning no sector', () => {
    const filter = { sectors: ['Technology', 'Unclassified'], search: '' }

    expect(tickers(filterPositions(POSITIONS, filter))).toEqual(['AAA', 'BBB'])
  })

  it('matches the search against ticker or name, ignoring case and outer spaces', () => {
    expect(tickers(filterPositions(POSITIONS, { sectors: [], search: ' bbb ' }))).toEqual(['BBB'])
    expect(tickers(filterPositions(POSITIONS, { sectors: [], search: 'BOND' }))).toEqual(['CCC'])
  })

  it('requires a position to pass both the sector and the search filter', () => {
    const filter = { sectors: ['Technology', 'Fixed Income'], search: 'gamma' }

    expect(tickers(filterPositions(POSITIONS, filter))).toEqual(['CCC'])
  })
})

describe('sectorsIn', () => {
  it('lists the sectors present, alphabetically, with Unclassified last', () => {
    const utility = { ...POSITIONS[0]!, ticker: 'DDD', sector: 'Utilities' } // sorts after "Unclassified"

    expect(sectorsIn([...POSITIONS, utility])).toEqual([
      'Fixed Income',
      'Technology',
      'Utilities',
      'Unclassified',
    ])
  })
})
