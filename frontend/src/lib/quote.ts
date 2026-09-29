import type { Position } from '@/api/client'
import type { LiveBar } from '@/api/live'

const DAY_CHANGE_METRIC = 'day_change'

export interface Quote {
  price: number | null
  change: number | null // fraction since the previous close
  source: 'live' | 'close'
}

/**
 * The price and day change the drawer headlines. Once a live bar arrives from a session after
 * the snapshot's, it is measured against the snapshot's last close. Until then (no bar yet, or
 * the market closed) the snapshot's own close and day change are shown, since a closed market's
 * last bar against its own close would read ~0%.
 */
export function headlineQuote(
  position: Position,
  bar: LiveBar | null,
  sessionDate: string | null,
): Quote {
  // both are ISO dates ("2026-09-28"), so comparing the strings compares the days
  if (bar !== null && sessionDate !== null && bar.session_date > sessionDate) {
    return { price: bar.close, change: changeSince(position.last_close, bar.close), source: 'live' }
  }
  return {
    price: position.last_close,
    change: position.metrics[DAY_CHANGE_METRIC] ?? null,
    source: 'close',
  }
}

function changeSince(previousClose: number | null, price: number): number | null {
  return previousClose === null ? null : price / previousClose - 1
}
