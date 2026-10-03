import { defineTickerCacheStore } from './tickerCache'

/** Popup fundamentals (P/E, market cap, ...), fetched on first click and cached per ticker. */
export const useFundamentalsStore = defineTickerCacheStore('fundamentals', (api, ticker) =>
  api.fetchInstrument(ticker),
)
