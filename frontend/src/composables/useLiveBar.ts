import { inject, onScopeDispose, ref, watch, type InjectionKey, type Ref } from 'vue'

import { parseLiveMessage, type LiveBar } from '@/api/live'

export type LiveStatus = 'connecting' | 'live' | 'unknown-ticker' | 'unavailable' | 'disconnected'

/** The parts of the browser's WebSocket this composable uses, so tests can pass a fake. */
export interface LiveSocket {
  onmessage: ((event: MessageEvent<string>) => void) | null
  onclose: ((event: CloseEvent) => void) | null
  close(): void
}

export type OpenSocket = (url: string) => LiveSocket

const RETRY_DELAYS_MS = [1_000, 2_000, 4_000]
const CLOSE_UNKNOWN_TICKER = 4404
const CLOSE_PROVIDER_UNAVAILABLE = 4503

const openBrowserSocket: OpenSocket = (url) => new WebSocket(url)

/** Tests provide a fake under this key; otherwise the browser's WebSocket is used. */
export const OPEN_SOCKET_KEY: InjectionKey<OpenSocket> = Symbol('OpenSocket')

/**
 * Streams minute bars for the ticker from `WS /api/live`. Follows the ticker when it changes and
 * closes the connection when the calling component goes away. An unexpected drop is retried
 * after 1s, 2s and 4s before giving up.
 */
export function useLiveBar(
  ticker: Ref<string>,
  openSocket: OpenSocket = inject(OPEN_SOCKET_KEY, openBrowserSocket),
) {
  const bar = ref<LiveBar | null>(null)
  const status = ref<LiveStatus>('connecting')

  let socket: LiveSocket | null = null
  let retryTimer: ReturnType<typeof setTimeout> | undefined
  let retriesUsed = 0

  function connect(): void {
    socket = openSocket(`/api/live?ticker=${encodeURIComponent(ticker.value)}`)
    socket.onmessage = (event) => {
      bar.value = parseLiveMessage(event.data)
      status.value = 'live'
      retriesUsed = 0
    }
    socket.onclose = (event) => {
      socket = null
      handleClose(event.code)
    }
  }

  function handleClose(code: number): void {
    if (code === CLOSE_UNKNOWN_TICKER) {
      status.value = 'unknown-ticker'
      return
    }
    if (code === CLOSE_PROVIDER_UNAVAILABLE) {
      status.value = 'unavailable'
      return
    }
    const delay = RETRY_DELAYS_MS[retriesUsed]
    if (delay === undefined) {
      status.value = 'disconnected'
      return
    }
    retriesUsed += 1
    status.value = 'connecting'
    retryTimer = setTimeout(connect, delay)
  }

  /** Closes on purpose: the handlers are detached first so the close isn't treated as a drop. */
  function disconnect(): void {
    clearTimeout(retryTimer)
    if (socket !== null) {
      socket.onmessage = null
      socket.onclose = null
      socket.close()
      socket = null
    }
  }

  watch(
    ticker,
    () => {
      disconnect()
      bar.value = null
      status.value = 'connecting'
      retriesUsed = 0
      connect()
    },
    { immediate: true },
  )

  onScopeDispose(disconnect)

  return { bar, status }
}
