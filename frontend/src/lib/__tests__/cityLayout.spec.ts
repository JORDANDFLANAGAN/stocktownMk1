import { describe, expect, it } from 'vitest'

import type { Position } from '@/api/client'
import { TEST_PORTFOLIO } from '@/__tests__/fixtures'
import { layoutCity, type Footprint } from '../cityLayout'

const SIZE = 100
const NO_PADDING = { size: SIZE, street: 0, alley: 0 }

function holding(ticker: string, sector: string | null, weight: number): Position {
  return {
    ticker,
    name: ticker,
    asset_class: 'equity',
    sector,
    weight,
    last_close: 100,
    metrics: {},
  }
}

// Two districts of two buildings each, so there are streets and alleys to measure.
const TWO_DISTRICTS = [
  holding('T1', 'Technology', 0.3),
  holding('T2', 'Technology', 0.2),
  holding('H1', 'Health Care', 0.35),
  holding('H2', 'Health Care', 0.15),
]

function area(footprint: Footprint): number {
  return footprint.width * footprint.depth
}

/** The clear ground between two footprints (0 if they touch or overlap). */
function gapBetween(a: Footprint, b: Footprint): number {
  const alongX = Math.abs(a.x - b.x) - (a.width + b.width) / 2
  const alongZ = Math.abs(a.z - b.z) - (a.depth + b.depth) / 2
  return Math.max(alongX, alongZ, 0)
}

function contains(outer: Footprint, inner: Footprint): boolean {
  const EPSILON = 1e-9
  return (
    inner.x - inner.width / 2 >= outer.x - outer.width / 2 - EPSILON &&
    inner.x + inner.width / 2 <= outer.x + outer.width / 2 + EPSILON &&
    inner.z - inner.depth / 2 >= outer.z - outer.depth / 2 - EPSILON &&
    inner.z + inner.depth / 2 <= outer.z + outer.depth / 2 + EPSILON
  )
}

describe('layoutCity', () => {
  it('gives every position one building, inside the city', () => {
    const { buildings } = layoutCity(TEST_PORTFOLIO.positions, { size: SIZE })

    expect(buildings.map((building) => building.ticker).sort()).toEqual(['AAA', 'BBB', 'CCC'])
    const city: Footprint = { x: 0, z: 0, width: SIZE, depth: SIZE }
    expect(buildings.every((building) => contains(city, building))).toBe(true)
  })

  it('gives each building ground in proportion to its weight', () => {
    const { buildings } = layoutCity(TWO_DISTRICTS, NO_PADDING)

    const areas = Object.fromEntries(buildings.map((building) => [building.ticker, area(building)]))
    expect(areas.T1).toBeCloseTo(0.3 * SIZE * SIZE)
    expect(areas.T2).toBeCloseTo(0.2 * SIZE * SIZE)
    expect(areas.H1).toBeCloseTo(0.35 * SIZE * SIZE)
    expect(areas.H2).toBeCloseTo(0.15 * SIZE * SIZE)
  })

  it('groups buildings into one district per sector, including unclassified positions', () => {
    const { buildings, districts } = layoutCity(TEST_PORTFOLIO.positions, { size: SIZE })

    expect(districts.map((district) => district.sector).sort()).toEqual([
      'Fixed Income',
      'Technology',
      'Unclassified',
    ])
    for (const building of buildings) {
      const district = districts.find((candidate) => candidate.sector === building.sector)!
      expect(contains(district, building)).toBe(true)
    }
    expect(buildings.find((building) => building.ticker === 'BBB')?.sector).toBe('Unclassified')
  })

  it('sizes each district by the total weight of its buildings', () => {
    const { districts } = layoutCity(TWO_DISTRICTS, NO_PADDING)

    const areas = Object.fromEntries(districts.map((district) => [district.sector, area(district)]))
    expect(areas.Technology).toBeCloseTo(0.5 * SIZE * SIZE)
    expect(areas['Health Care']).toBeCloseTo(0.5 * SIZE * SIZE)
  })

  it('leaves a street between districts and a narrower alley between neighbours', () => {
    const { buildings } = layoutCity(TWO_DISTRICTS, { size: SIZE, street: 2, alley: 0.5 })

    for (const a of buildings) {
      for (const b of buildings.filter((other) => other !== a)) {
        const minimumGap = a.sector === b.sector ? 0.5 : 2
        expect(gapBetween(a, b)).toBeGreaterThanOrEqual(minimumGap - 1e-9)
      }
    }
  })

  it('builds nothing for an empty universe', () => {
    expect(layoutCity([], { size: SIZE })).toEqual({ buildings: [], districts: [] })
  })
})
