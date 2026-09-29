import { describe, expect, it } from 'vitest'

import { parseLiveMessage } from '../live'

describe('parseLiveMessage', () => {
  it('reads a minute bar exactly as the server sends it', () => {
    const raw =
      '{"type":"bar","ticker":"AAPL","minute_utc":"2026-09-28T19:59:00Z",' +
      '"open":338.49,"high":338.54,"low":338.31,"close":338.4,"volume":36355}'

    expect(parseLiveMessage(raw)).toEqual({
      type: 'bar',
      ticker: 'AAPL',
      minute_utc: '2026-09-28T19:59:00Z',
      open: 338.49,
      high: 338.54,
      low: 338.31,
      close: 338.4,
      volume: 36355,
    })
  })

  it('refuses a message type it does not know rather than treating it as a bar', () => {
    expect(() => parseLiveMessage('{"type":"status","state":"reconnecting"}')).toThrow(
      'Unrecognised live message',
    )
  })
})
