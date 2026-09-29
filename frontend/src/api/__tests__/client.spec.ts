import { describe, expect, it } from 'vitest'

import { TEST_PORTFOLIO } from '@/__tests__/fixtures'
import { ApiError, createApi } from '../client'

const BACKEND = 'http://backend.test'

/** An Api wired to a fake backend that answers every request with the same response. */
function apiAnswering(status: number, body: unknown, headers: Record<string, string> = {}) {
  const requestedUrls: string[] = []
  const fetch = async (request: Request) => {
    requestedUrls.push(request.url)
    return Response.json(body, { status, headers })
  }
  return { api: createApi({ baseUrl: BACKEND, fetch }), requestedUrls }
}

describe('Api', () => {
  it('fetches the universe named by its id', async () => {
    const { api, requestedUrls } = apiAnswering(200, TEST_PORTFOLIO)

    const universe = await api.fetchUniverse('test-portfolio')

    expect(requestedUrls).toEqual([`${BACKEND}/universes/test-portfolio`])
    expect(universe).toEqual(TEST_PORTFOLIO)
  })

  it('reports an unknown ticker as not found', async () => {
    const { api } = apiAnswering(404, { detail: 'Unknown ticker' })

    const failure = api.fetchInstrument('NOPE')

    await expect(failure).rejects.toThrow(ApiError)
    await expect(failure).rejects.toMatchObject({ status: 404, retryAfterSeconds: null })
  })

  it('passes on how long to wait when the data provider is down', async () => {
    const { api } = apiAnswering(503, { detail: 'Provider unavailable' }, { 'Retry-After': '30' })

    await expect(api.fetchMetrics()).rejects.toMatchObject({ status: 503, retryAfterSeconds: 30 })
  })
})
