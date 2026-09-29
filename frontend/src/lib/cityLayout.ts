import { hierarchy, treemap, type HierarchyRectangularNode } from 'd3-hierarchy'

import type { Position } from '@/api/client'
import { sectorOf } from './positions'

/** Side of the square city in world units; building heights (cityScales) use the same units. */
export const CITY_SIZE = 100
const STREET_WIDTH = 1.5 // between sector districts
const ALLEY_WIDTH = 0.25 // between neighbouring buildings in a district

/** A rectangle on the ground: centre (x, z) with the city centred on the origin, and its size. */
export interface Footprint {
  x: number
  z: number
  width: number
  depth: number
}

export interface BuildingPlot extends Footprint {
  ticker: string
  sector: string
}

export interface DistrictPlot extends Footprint {
  sector: string
}

export interface CityLayout {
  buildings: BuildingPlot[]
  districts: DistrictPlot[]
}

export interface LayoutOptions {
  size?: number
  street?: number
  alley?: number
}

interface CityNode {
  name: string // sector for a district, ticker for a building
  weight: number // a building's weight; districts sum their buildings
  children?: CityNode[]
}

/**
 * A treemap of treemaps: each sector is a district sized by its total weight, each holding a
 * building sized by its own weight, and the padding between them becomes streets and alleys.
 * Pure, so the same positions always give the same city.
 */
export function layoutCity(
  positions: Position[],
  { size = CITY_SIZE, street = STREET_WIDTH, alley = ALLEY_WIDTH }: LayoutOptions = {},
): CityLayout {
  if (positions.length === 0) {
    return { buildings: [], districts: [] }
  }

  const root = hierarchy<CityNode>({ name: 'city', weight: 0, children: districtNodes(positions) })
    .sum((node) => node.weight)
    .sort((a, b) => (b.value ?? 0) - (a.value ?? 0))

  const city = treemap<CityNode>()
    .size([size, size])
    .paddingInner((node) => (node.depth === 0 ? street : alley))(root)

  const districts = (city.children ?? []).map((district) => ({
    sector: district.data.name,
    ...footprintOf(district, size),
  }))
  const buildings = city.leaves().map((building) => ({
    ticker: building.data.name,
    sector: building.parent!.data.name,
    ...footprintOf(building, size),
  }))
  return { buildings, districts }
}

function districtNodes(positions: Position[]): CityNode[] {
  const bySector = new Map<string, CityNode[]>()
  for (const position of positions) {
    const sector = sectorOf(position)
    const buildings = bySector.get(sector) ?? []
    buildings.push({ name: position.ticker, weight: position.weight })
    bySector.set(sector, buildings)
  }
  return [...bySector].map(([sector, buildings]) => ({
    name: sector,
    weight: 0,
    children: buildings,
  }))
}

/** d3 lays out from the corner (0, 0); the scene is centred on the origin. */
function footprintOf(node: HierarchyRectangularNode<CityNode>, size: number): Footprint {
  return {
    x: (node.x0 + node.x1) / 2 - size / 2,
    z: (node.y0 + node.y1) / 2 - size / 2,
    width: node.x1 - node.x0,
    depth: node.y1 - node.y0,
  }
}
