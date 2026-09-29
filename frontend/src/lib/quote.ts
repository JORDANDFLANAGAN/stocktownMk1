import type { Position } from '@/api/client'
import type { LiveBar } from '@/api/live'
import type { LiveStatus } from '@/composables/useLiveBar'

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

/**
 * The tag beside the headline price: what the price is (live as of a minute, or the close), plus
 * a note when live prices stopped or never came. The normal wait for the first bar gets no note,
 * so opening the drawer doesn't flicker.
 */
export function quoteTag(
  quote: Quote,
  bar: LiveBar | null,
  status: LiveStatus,
  sessionDate: string | null,
): string {
  const problem = connectionProblem(status, bar)
  if (quote.source === 'live' && bar !== null) {
    const minute = `${marketMinuteOf(bar)} ET`
    return problem === null ? `Live · ${minute}` : `${minute} · ${problem}`
  }
  const close = sessionDate === null ? 'Close' : `Close, ${sessionDate}`
  return problem === null ? close : `${close} · ${problem}`
}

function connectionProblem(status: LiveStatus, bar: LiveBar | null): string | null {
  switch (status) {
    case 'live':
      return null
    case 'connecting':
      return bar === null ? null : 'reconnecting…' // no bar yet = still opening, not a problem
    case 'unavailable':
    case 'disconnected':
      return 'live prices unavailable'
    case 'unknown-ticker':
      return 'no live prices for this ticker'
  }
}

/** "15:59": `minute_market` is ISO 8601 on the market's clock, so characters 11–15 are HH:MM. */
function marketMinuteOf(bar: LiveBar): string {
  return bar.minute_market.slice(11, 16)
}
