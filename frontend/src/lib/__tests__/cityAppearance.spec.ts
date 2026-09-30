import { describe, expect, it } from 'vitest'

import type { Position } from '@/api/client'
import { TEST_CATALOGUE, TEST_PORTFOLIO } from '@/__tests__/fixtures'
import { sectorColours, styleBuildings, UNCLASSIFIED_COLOUR } from '../cityAppearance'
import type { BuildingPlot } from '../cityLayout'
import { MAX_HEIGHT, MIN_HEIGHT } from '../cityScales'

const BETA = TEST_CATALOGUE[1]! // AAA 1.3 (highest), BBB none, CCC 0.1 (lowest)
const POSITIONS = TEST_PORTFOLIO.positions // AAA Technology, BBB no sector, CCC Fixed Income

const ELEVEN_SECTORS = Array.from({ length: 11 }, (_, index) => `Sector ${index + 1}`)
const SET3_GREY = '#d9d9d9'

// The layout reads each plot's sector from its position; unclassified becomes 'Unclassified'.
const PLOTS: Record<string, BuildingPlot> = {
  AAA: { ticker: 'AAA', sector: 'Technology', x: 0, z: 0, width: 1, depth: 1 },
  BBB: { ticker: 'BBB', sector: 'Unclassified', x: 0, z: 0, width: 1, depth: 1 },
  CCC: { ticker: 'CCC', sector: 'Fixed Income', x: 0, z: 0, width: 1, depth: 1 },
}

function plotsFor(tickers: string[]): BuildingPlot[] {
  return tickers.map((ticker) => PLOTS[ticker]!)
}

function appearance(buildings: ReturnType<typeof styleBuildings>) {
  return buildings.map(({ ticker, height, colour }) => [ticker, height, colour])
}

describe('styleBuildings', () => {
  const colours = sectorColours(['Fixed Income', 'Technology', 'Unclassified'])

  it('raises each building by the height metric and colours it by its sector', () => {
    const buildings = styleBuildings(plotsFor(['AAA', 'BBB', 'CCC']), POSITIONS, BETA)

    expect(appearance(buildings)).toEqual([
      ['AAA', MAX_HEIGHT, colours.get('Technology')],
      ['BBB', MIN_HEIGHT, UNCLASSIFIED_COLOUR],
      ['CCC', MIN_HEIGHT, colours.get('Fixed Income')],
    ])
  })

  it('matches buildings to positions by ticker, whatever order the layout puts them in', () => {
    const buildings = styleBuildings(plotsFor(['CCC', 'BBB', 'AAA']), POSITIONS, BETA)

    expect(appearance(buildings)).toEqual([
      ['CCC', MIN_HEIGHT, colours.get('Fixed Income')],
      ['BBB', MIN_HEIGHT, UNCLASSIFIED_COLOUR],
      ['AAA', MAX_HEIGHT, colours.get('Technology')],
    ])
  })

  it('carries each position’s weight, for the top-down labels', () => {
    const buildings = styleBuildings(plotsFor(['CCC', 'AAA']), POSITIONS, BETA)

    expect(buildings.map(({ ticker, weight }) => [ticker, weight])).toEqual([
      ['CCC', 0.2],
      ['AAA', 0.5],
    ])
  })

  it('stands a building at the lowest height when its position has no entry for the metric', () => {
    const [alpha, beta, gamma] = POSITIONS as [Position, Position, Position]
    const withoutEntry = [alpha, { ...beta, metrics: {} }, gamma]

    const buildings = styleBuildings(plotsFor(['AAA', 'BBB', 'CCC']), withoutEntry, BETA)

    expect(buildings.map(({ height }) => height)).toEqual([MAX_HEIGHT, MIN_HEIGHT, MIN_HEIGHT])
  })
})

describe('sectorColours', () => {
  it('gives each of the S&P’s eleven sectors its own colour, none of them grey', () => {
    const colours = [...sectorColours(ELEVEN_SECTORS)]
      .filter(([sector]) => sector !== 'Unclassified')
      .map(([, colour]) => colour)

    expect(new Set(colours).size).toBe(11)
    expect(colours).not.toContain(SET3_GREY)
    expect(colours).not.toContain(UNCLASSIFIED_COLOUR)
  })

  it('keeps Unclassified grey wherever it comes in the list', () => {
    const colours = sectorColours(['Unclassified', 'Energy', 'Utilities'])

    expect(colours.get('Unclassified')).toBe(UNCLASSIFIED_COLOUR)
    expect(colours.get('Energy')).toBe(sectorColours(['Energy']).get('Energy'))
  })

  it('reuses the palette from the start after eleven sectors', () => {
    const colours = sectorColours([...ELEVEN_SECTORS, 'Sector 12'])

    expect(colours.get('Sector 12')).toBe(colours.get('Sector 1'))
  })
})
