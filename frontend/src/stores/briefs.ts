import { defineTickerCacheStore } from './tickerCache'

/** Popup AI briefs, fetched on first click and cached per ticker (the server caches per day). */
export const useBriefStore = defineTickerCacheStore('briefs', (api, ticker) =>
  api.fetchBrief(ticker),
)
