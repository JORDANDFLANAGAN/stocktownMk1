import { defineStore } from 'pinia'
import { ref } from 'vue'

import type { Instrument } from '@/api/client'
import { useApi } from '@/composables/useApi'

export interface FundamentalsEntry {
  loading: boolean
  error: unknown
  data: Instrument | null
}

/** Popup fundamentals (P/E, market cap, ...), fetched on first click and cached per ticker. */
export const useFundamentalsStore = defineStore('fundamentals', () => {
  const api = useApi()

  const entries = ref(new Map<string, FundamentalsEntry>())

  function entryFor(ticker: string): FundamentalsEntry | undefined {
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
      const data = await api.fetchInstrument(ticker)
      entries.value.set(ticker, { loading: false, error: null, data })
    } catch (caught) {
      entries.value.set(ticker, { loading: false, error: caught, data: null })
    }
  }

  return { entryFor, load }
})
