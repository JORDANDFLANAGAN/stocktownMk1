import createClient from 'openapi-fetch'

import type { components, paths } from './schema'

export type Universe = components['schemas']['UniverseResponse']
export type Position = components['schemas']['PositionResponse']
export type MetricInfo = components['schemas']['MetricInfoResponse']
export type Instrument = components['schemas']['InstrumentResponse']

/**
 * What the app needs from the backend. Stores depend on this, so tests can hand them a plain fake.
 * A dead network rejects with the browser's `TypeError`, not `ApiError`.
 */
export interface Api {
  fetchUniverse(universeId: string): Promise<Universe>
  fetchMetrics(): Promise<MetricInfo[]>
  fetchInstrument(ticker: string): Promise<Instrument>
}

/** A request the backend answered with an error: 404 = unknown universe/ticker, 503 = data provider down. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly retryAfterSeconds: number | null,
  ) {
    super(`API request failed with status ${status}`)
    this.name = 'ApiError'
  }
}

interface ApiOptions {
  /** Blank in the app: same origin, and Vite proxies to FastAPI in dev. */
  baseUrl?: string
  /** Swapped for a fake in tests. */
  fetch?: (request: Request) => Promise<Response>
}

export function createApi({ baseUrl = '', fetch = globalThis.fetch }: ApiOptions = {}): Api {
  const client = createClient<paths>({ baseUrl, fetch })

  return {
    async fetchUniverse(universeId) {
      const { data, response } = await client.GET('/api/universes/{universe_id}', {
        params: { path: { universe_id: universeId } },
      })
      return dataOrThrow(data, response)
    },

    async fetchMetrics() {
      const { data, response } = await client.GET('/api/metrics')
      return dataOrThrow(data, response)
    },

    async fetchInstrument(ticker) {
      const { data, response } = await client.GET('/api/instruments/{ticker}', {
        params: { path: { ticker } },
      })
      return dataOrThrow(data, response)
    },
  }
}

function dataOrThrow<T>(data: T | undefined, response: Response): T {
  if (data === undefined) {
    throw new ApiError(response.status, retryAfterSeconds(response))
  }
  return data
}

function retryAfterSeconds(response: Response): number | null {
  const seconds = Number(response.headers.get('Retry-After'))
  return seconds > 0 ? seconds : null
}
