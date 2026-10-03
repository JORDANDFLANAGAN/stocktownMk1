import { createPinia, type Pinia } from 'pinia'
import { createApp } from 'vue'

import type { Api } from '@/api/client'
import { API_KEY } from '@/composables/useApi'

/** An Api whose methods fail loudly unless the test supplies them. */
export function fakeApi(methods: Partial<Api>): Api {
  const notUsedByThisTest = (name: string) => () => {
    throw new Error(`fakeApi.${name} was called but the test did not provide it`)
  }
  return {
    fetchUniverse: methods.fetchUniverse ?? notUsedByThisTest('fetchUniverse'),
    fetchMetrics: methods.fetchMetrics ?? notUsedByThisTest('fetchMetrics'),
    fetchInstrument: methods.fetchInstrument ?? notUsedByThisTest('fetchInstrument'),
    fetchBrief: methods.fetchBrief ?? notUsedByThisTest('fetchBrief'),
  }
}

/** A fresh Pinia wired the same way as main.ts, but with the given Api. */
export function piniaWith(api: Api): Pinia {
  const pinia = createPinia()
  createApp({}).provide(API_KEY, api).use(pinia)
  return pinia
}
