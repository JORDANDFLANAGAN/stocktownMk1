import type { LiveSocket, OpenSocket } from '@/composables/useLiveBar'

/** Stands in for the browser WebSocket; the test decides what the server sends and when it drops. */
export class FakeSocket implements LiveSocket {
  onmessage: ((event: MessageEvent<string>) => void) | null = null
  onclose: ((event: CloseEvent) => void) | null = null
  closedByClient = false

  constructor(readonly url: string) {}

  /** Like the browser: closing on purpose still fires `onclose` a moment later. */
  close(): void {
    this.closedByClient = true
    setTimeout(() => this.onclose?.(new CloseEvent('close', { code: 1005 })), 0)
  }

  /** Sends a bar from Monday 2026-09-28, the session after the test snapshot's. */
  sendBar(ticker: string, close: number): void {
    const bar = {
      type: 'bar',
      ticker,
      minute_utc: '2026-09-28T19:59:00Z',
      session_date: '2026-09-28',
      open: close,
      high: close,
      low: close,
      close,
      volume: 100,
    }
    this.onmessage?.(new MessageEvent('message', { data: JSON.stringify(bar) }))
  }

  drop(code = 1006): void {
    this.onclose?.(new CloseEvent('close', { code }))
  }
}

/** An `OpenSocket` that hands out fake sockets and keeps them, so a test can play the server. */
export function recordingSockets() {
  const sockets: FakeSocket[] = []
  const openSocket: OpenSocket = (url) => {
    const socket = new FakeSocket(url)
    sockets.push(socket)
    return socket
  }
  const latestSocket = () => sockets[sockets.length - 1]!
  return { openSocket, sockets, latestSocket }
}
