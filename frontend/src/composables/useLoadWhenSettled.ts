import { onScopeDispose, watch, type WatchSource } from 'vue'

/** Wait this long on a ticker before fetching, so flicking through rows costs no API calls. */
export const SETTLE_MS = 300

/**
 * Calls `load` for the ticker once the drawer has stayed on it for SETTLE_MS. Moving on, or
 * closing the drawer, before then fetches nothing.
 */
export function useLoadWhenSettled(ticker: WatchSource<string>, load: (ticker: string) => void) {
  let pendingLoad: ReturnType<typeof setTimeout> | undefined
  watch(
    ticker,
    (current) => {
      clearTimeout(pendingLoad)
      pendingLoad = setTimeout(() => load(current), SETTLE_MS)
    },
    { immediate: true },
  )
  onScopeDispose(() => clearTimeout(pendingLoad))
}
