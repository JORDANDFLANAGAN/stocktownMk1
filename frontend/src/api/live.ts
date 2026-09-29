/** Messages sent on `WS /live?ticker=`. Hand-written because OpenAPI doesn't describe WebSockets. */

export interface LiveBar {
  type: 'bar'
  ticker: string
  minute_utc: string // ISO 8601, e.g. "2026-09-28T19:59:00Z"
  minute_market: string // the same minute on the market's clock, e.g. "2026-09-28T15:59:00-04:00"
  session_date: string // the market's trading day for this bar, e.g. "2026-09-28"
  open: number
  high: number
  low: number
  close: number
  volume: number
}

/** Every message the server can send, told apart by `type`. Only bars so far. */
export type LiveMessage = LiveBar

/** Trusts our own server for the fields, but refuses message types this code doesn't know. */
export function parseLiveMessage(raw: string): LiveMessage {
  const message = JSON.parse(raw) as { type?: unknown }
  if (message.type === 'bar') {
    return message as LiveBar
  }
  throw new Error(`Unrecognised live message: ${raw}`)
}
