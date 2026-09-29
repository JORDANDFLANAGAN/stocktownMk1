import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { effectScope, nextTick, ref } from 'vue'

import { recordingSockets } from '@/__tests__/fakeSocket'
import { useLiveBar } from '../useLiveBar'

/** Runs useLiveBar the way a component would, recording every socket it opens. */
function startLiveBar(initialTicker: string) {
  const ticker = ref(initialTicker)
  const { openSocket, sockets, latestSocket } = recordingSockets()
  const scope = effectScope()
  const live = scope.run(() => useLiveBar(ticker, openSocket))!
  return { ticker, live, sockets, latestSocket, closePopup: () => scope.stop() }
}

describe('useLiveBar', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => vi.useRealTimers())

  it('shows each bar the server sends for the ticker', () => {
    const { live, latestSocket } = startLiveBar('AAPL')
    expect(latestSocket().url).toBe('/api/live?ticker=AAPL')
    expect(live.status.value).toBe('connecting')

    latestSocket().sendBar('AAPL', 338.4)

    expect(live.bar.value?.close).toBe(338.4)
    expect(live.status.value).toBe('live')
  })

  it('moves to the new ticker when the ticker changes', async () => {
    const { ticker, live, sockets } = startLiveBar('AAPL')
    sockets[0]!.sendBar('AAPL', 338.4)

    ticker.value = 'MSFT'
    await nextTick()
    vi.runAllTimers() // let the old socket's close event arrive

    expect(sockets[0]!.closedByClient).toBe(true)
    expect(sockets.map((socket) => socket.url)).toEqual([
      '/api/live?ticker=AAPL',
      '/api/live?ticker=MSFT',
    ])
    expect(live.bar.value).toBeNull() // no AAPL price shown under MSFT
  })

  it('closes the connection when the popup closes, even while waiting to retry', () => {
    const { sockets, latestSocket, closePopup } = startLiveBar('AAPL')
    latestSocket().drop()

    closePopup()
    vi.runAllTimers()

    expect(sockets).toHaveLength(1)
  })

  it('retries an unexpected drop after 1s, 2s and 4s, then gives up', () => {
    const { live, sockets, latestSocket } = startLiveBar('AAPL')

    for (const delayMs of [1_000, 2_000, 4_000]) {
      const socketsBefore = sockets.length
      latestSocket().drop()
      vi.advanceTimersByTime(delayMs - 1)
      expect(sockets).toHaveLength(socketsBefore)
      vi.advanceTimersByTime(1)
      expect(sockets).toHaveLength(socketsBefore + 1)
    }
    latestSocket().drop()
    vi.runAllTimers()

    expect(sockets).toHaveLength(4)
    expect(live.status.value).toBe('disconnected')
  })

  it('gives a connection that recovers a fresh set of retries', () => {
    const { live, sockets, latestSocket } = startLiveBar('AAPL')
    for (let drop = 0; drop < 3; drop++) {
      latestSocket().drop()
      vi.runAllTimers()
      latestSocket().sendBar('AAPL', 338.4) // back up again
    }

    latestSocket().drop()
    vi.runAllTimers()

    expect(sockets).toHaveLength(5)
    expect(live.status.value).toBe('connecting')
  })

  it.each([
    [4404, 'unknown-ticker'],
    [4503, 'unavailable'],
  ])('reports close code %i as %s without retrying', (code, expectedStatus) => {
    const { live, sockets, latestSocket } = startLiveBar('AAPL')

    latestSocket().drop(code)
    vi.runAllTimers()

    expect(live.status.value).toBe(expectedStatus)
    expect(sockets).toHaveLength(1)
  })
})
