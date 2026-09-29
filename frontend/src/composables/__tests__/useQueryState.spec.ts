import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { defineComponent } from 'vue'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'

import { useQueryFilters, useQuerySort } from '../useQueryState'

/** Runs a composable inside a component with a real router opened at `url`. */
async function useWithRouterAt<T>(url: string, composable: () => T): Promise<[T, Router]> {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/:pathMatch(.*)*', component: { render: () => null } }],
  })
  await router.push(url)
  let result!: T
  const Host = defineComponent({
    setup() {
      result = composable()
      return () => null
    },
  })
  mount(Host, { global: { plugins: [router] } })
  return [result, router]
}

describe('useQuerySort', () => {
  it('reads the sort column and direction from the URL', async () => {
    const [descending] = await useWithRouterAt('/list?sort=-beta_1y', useQuerySort)
    const [ascending] = await useWithRouterAt('/list?sort=ticker', useQuerySort)
    const [unsorted] = await useWithRouterAt('/list', useQuerySort)

    expect(descending.value).toEqual([{ id: 'beta_1y', desc: true }])
    expect(ascending.value).toEqual([{ id: 'ticker', desc: false }])
    expect(unsorted.value).toEqual([])
  })

  it('writes the sort to the URL, keeps the other params, and drops it when cleared', async () => {
    const [sort, router] = await useWithRouterAt('/list?q=apple', useQuerySort)

    sort.value = [{ id: 'day_change', desc: true }]
    await flushPromises() // let the URL update land
    expect(router.currentRoute.value.fullPath).toBe('/list?q=apple&sort=-day_change')

    sort.value = []
    await flushPromises()
    expect(router.currentRoute.value.fullPath).toBe('/list?q=apple')
  })
})

describe('useQueryFilters', () => {
  it('reads the chosen sectors and the search text from the URL', async () => {
    const [filters] = await useWithRouterAt(
      '/list?sector=Technology&sector=Unclassified&q=alpha',
      useQueryFilters,
    )

    expect(filters.sectors.value).toEqual(['Technology', 'Unclassified'])
    expect(filters.search.value).toBe('alpha')
  })

  it('writes the filters to the URL and drops each one when emptied', async () => {
    const [filters, router] = await useWithRouterAt('/list?sort=ticker', useQueryFilters)

    filters.sectors.value = ['Technology', 'Fixed Income']
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({
      sort: 'ticker',
      sector: ['Technology', 'Fixed Income'],
    })

    filters.sectors.value = []
    await flushPromises()
    filters.search.value = 'gamma'
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ sort: 'ticker', q: 'gamma' })

    filters.search.value = ''
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ sort: 'ticker' })
  })
})
