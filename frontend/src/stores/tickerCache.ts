import { defineStore } from 'pinia'
import { ref, type Ref } from 'vue'

import type { Api } from '@/api/client'
import { useApi } from '@/composables/useApi'

export interface TickerCacheEntry<T> {
  loading: boolean
  error: unknown
  data: T | null
}

/** A Pinia store of drawer data, fetched on a ticker's first click and cached per ticker. */
export function defineTickerCacheStore<T>(
  id: string,
  fetch: (api: Api, ticker: string) => Promise<T>,
) {
  return defineStore(id, () => {
    const api = useApi()

    // typed by hand: Vue's ref() can't unwrap a generic T, and the entries hold plain data
    const entries = ref(new Map()) as Ref<Map<string, TickerCacheEntry<T>>>

    function entryFor(ticker: string): TickerCacheEntry<T> | undefined {
      return entries.value.get(ticker)
    }

    /** Fetches once per ticker. Already loaded or in flight: does nothing. Failed before: tries again. */
    async function load(ticker: string): Promise<void> {
      const existing = entries.value.get(ticker)
      if (existing !== undefined && existing.error === null) {
        return
      }

      entries.value.set(ticker, { loading: true, error: null, data: null })
      try {
        const data = await fetch(api, ticker)
        entries.value.set(ticker, { loading: false, error: null, data })
      } catch (caught) {
        entries.value.set(ticker, { loading: false, error: caught, data: null })
      }
    }

    return { entryFor, load }
  })
}
