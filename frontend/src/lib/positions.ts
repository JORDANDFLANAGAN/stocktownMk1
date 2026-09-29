import type { Position } from '@/api/client'

/** How a position with no sector is shown and filtered. */
export const UNCLASSIFIED = 'Unclassified'

export interface PositionFilter {
  /** Sectors to keep; empty keeps every sector. */
  sectors: string[]
  /** Case-insensitive text matched against ticker and name; blank matches everything. */
  search: string
}

export function sectorOf(position: Position): string {
  return position.sector ?? UNCLASSIFIED
}

/** The sectors present in the universe, alphabetical, with Unclassified last. */
export function sectorsIn(positions: Position[]): string[] {
  const sectors = [...new Set(positions.map(sectorOf))].sort()
  const classified = sectors.filter((sector) => sector !== UNCLASSIFIED)
  return sectors.includes(UNCLASSIFIED) ? [...classified, UNCLASSIFIED] : classified
}

/** Shared by the list and the city, so both views always agree on what is filtered out. */
export function filterPositions(positions: Position[], filter: PositionFilter): Position[] {
  const search = filter.search.trim().toLowerCase()
  return positions.filter(
    (position) =>
      (filter.sectors.length === 0 || filter.sectors.includes(sectorOf(position))) &&
      (search === '' ||
        position.ticker.toLowerCase().includes(search) ||
        position.name.toLowerCase().includes(search)),
  )
}
