import { schemeSet3 } from 'd3-scale-chromatic'

import type { MetricInfo, Position } from '@/api/client'
import type { BuildingPlot } from './cityLayout'
import { heightScale } from './cityScales'
import { sectorsIn, UNCLASSIFIED } from './positions'

/** Neutral grey (zinc-400) for positions with no sector. */
export const UNCLASSIFIED_COLOUR = '#a1a1aa'

// ColorBrewer Set3 without its grey, which would read as Unclassified: 11 colours, one per
// S&P sector.
const SECTOR_PALETTE = schemeSet3.filter((colour) => colour !== '#d9d9d9')

export interface StyledBuilding extends BuildingPlot {
  height: number
  colour: string
}

/**
 * Each plot's height from the chosen metric (scaled against the positions on screen) and colour
 * from its sector. Plots are matched to positions by ticker: the layout orders them by weight.
 */
export function styleBuildings(
  plots: BuildingPlot[],
  positions: Position[],
  heightMetric: MetricInfo,
): StyledBuilding[] {
  const heightOf = heightScale(
    heightMetric,
    positions.map((position) => position.metrics[heightMetric.key] ?? null),
  )
  const colourOf = sectorColours(sectorsIn(positions))
  const byTicker = new Map(positions.map((position) => [position.ticker, position]))

  return plots.map((plot) => ({
    ...plot,
    height: heightOf(byTicker.get(plot.ticker)?.metrics[heightMetric.key] ?? null),
    colour: colourOf.get(plot.sector) ?? UNCLASSIFIED_COLOUR,
  }))
}

/**
 * A colour per sector, following the order given, so the same universe always gets the same
 * colours. More sectors than colours reuse the palette from the start; Unclassified is grey.
 */
export function sectorColours(sectors: string[]): Map<string, string> {
  const classified = sectors.filter((sector) => sector !== UNCLASSIFIED)
  const colours = new Map(
    classified.map((sector, index) => [sector, SECTOR_PALETTE[index % SECTOR_PALETTE.length]!]),
  )
  colours.set(UNCLASSIFIED, UNCLASSIFIED_COLOUR)
  return colours
}
