import type { MetricInfo, Position } from '@/api/client'
import type { BuildingPlot } from './cityLayout'
import { heightScale } from './cityScales'
import { sectorsIn, UNCLASSIFIED } from './positions'

/** Neutral grey (zinc-400) for positions with no sector. */
export const UNCLASSIFIED_COLOUR = '#a1a1aa'

// One colour per GICS sector (the names SSGA's sector funds use). Eight are a validated
// colour-blind-safe categorical set; cyan, brown and plum extend it to eleven. The pairing was
// checked against the S&P city's layout: every two neighbouring districts stay distinct under
// simulated red-green colour blindness (OKLab ΔE ≥ 11.8, target 8) and normal vision (≥ 18.4,
// floor 15). No eleven hues can all be told apart everywhere, so district labels carry identity
// too. Re-check the pairing if the sectors' weight order changes noticeably.
const GICS_SECTOR_COLOURS = new Map([
  ['Information Technology', '#2a78d6'], // blue
  ['Financials', '#e34948'], // red
  ['Communication Services', '#4a3aa7'], // violet
  ['Health Care', '#008300'], // green
  ['Consumer Discretionary', '#e87ba4'], // pink
  ['Industrials', '#eda100'], // yellow
  ['Consumer Staples', '#a0652a'], // brown
  ['Energy', '#17becf'], // cyan
  ['Utilities', '#eb6834'], // orange
  ['Real Estate', '#b0428f'], // plum
  ['Materials', '#1baf7a'], // aqua
])
// Sectors outside GICS (a portfolio's own names) take the same colours in order, repeating past 11.
const OTHER_SECTOR_PALETTE = [...GICS_SECTOR_COLOURS.values()]

export interface StyledBuilding extends BuildingPlot {
  height: number
  colour: string
  weight: number
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

  return plots.map((plot) => {
    const position = byTicker.get(plot.ticker)
    return {
      ...plot,
      height: heightOf(position?.metrics[heightMetric.key] ?? null),
      colour: colourOf.get(plot.sector) ?? UNCLASSIFIED_COLOUR,
      weight: position?.weight ?? 0,
    }
  })
}

/**
 * A colour per sector. GICS sectors always get their own colour, whatever else is on screen;
 * other names take the palette in the order given; Unclassified is grey.
 */
export function sectorColours(sectors: string[]): Map<string, string> {
  const colours = new Map<string, string>()
  const others = sectors.filter(
    (sector) => sector !== UNCLASSIFIED && !GICS_SECTOR_COLOURS.has(sector),
  )
  for (const sector of sectors) {
    const gics = GICS_SECTOR_COLOURS.get(sector)
    if (gics !== undefined) colours.set(sector, gics)
  }
  others.forEach((sector, index) => {
    colours.set(sector, OTHER_SECTOR_PALETTE[index % OTHER_SECTOR_PALETTE.length]!)
  })
  colours.set(UNCLASSIFIED, UNCLASSIFIED_COLOUR)
  return colours
}

export interface SectorColour {
  sector: string
  colour: string
}

/** The sectors on screen with their colours, in legend order (alphabetical, Unclassified last). */
export function sectorKey(positions: Position[]): SectorColour[] {
  const sectors = sectorsIn(positions)
  const colours = sectorColours(sectors)
  return sectors.map((sector) => ({ sector, colour: colours.get(sector)! }))
}
