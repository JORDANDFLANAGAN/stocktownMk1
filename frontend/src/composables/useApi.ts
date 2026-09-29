import { inject, type InjectionKey } from 'vue'

import type { Api } from '@/api/client'

/** Key the app registers its `Api` under (main.ts); tests register a fake instead. */
export const API_KEY: InjectionKey<Api> = Symbol('Api')

export function useApi(): Api {
  const api = inject(API_KEY)
  if (api === undefined) {
    throw new Error('No Api provided: call app.provide(API_KEY, createApi()) in main.ts')
  }
  return api
}
