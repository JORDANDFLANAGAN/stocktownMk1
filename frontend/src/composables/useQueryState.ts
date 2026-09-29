import type { SortingState } from '@tanstack/vue-table'
import { computed, type WritableComputedRef } from 'vue'
import { useRoute, useRouter, type LocationQueryRaw, type LocationQueryValue } from 'vue-router'

/**
 * List state kept in the URL, so a link or a refresh restores it:
 *   ?sort=-beta_1y            sort by beta, highest first (no "-" = lowest first)
 *   &sector=Technology&sector=Utilities
 *   &q=apple
 * Each setter replaces the URL (no new history entry) and keeps the other params.
 */

export function useQuerySort(): WritableComputedRef<SortingState> {
  const route = useRoute()
  const replaceQuery = useReplaceQuery()

  return computed({
    get: () => parseSort(firstValue(route.query.sort)),
    set: (sorting) => replaceQuery({ sort: formatSort(sorting) }),
  })
}

export function useQueryFilters() {
  const route = useRoute()
  const replaceQuery = useReplaceQuery()

  const sectors = computed<string[]>({
    get: () => allValues(route.query.sector),
    set: (chosen) => replaceQuery({ sector: chosen.length > 0 ? chosen : undefined }),
  })
  const search = computed<string>({
    get: () => firstValue(route.query.q),
    set: (text) => replaceQuery({ q: text === '' ? undefined : text }),
  })

  return { sectors, search }
}

function useReplaceQuery() {
  const route = useRoute()
  const router = useRouter()
  return (changes: LocationQueryRaw) => router.replace({ query: { ...route.query, ...changes } })
}

type QueryValue = LocationQueryValue | LocationQueryValue[] | undefined

function allValues(value: QueryValue): string[] {
  const values = Array.isArray(value) ? value : [value]
  return values.filter((item): item is string => typeof item === 'string' && item !== '')
}

function firstValue(value: QueryValue): string {
  return allValues(value)[0] ?? ''
}

function parseSort(text: string): SortingState {
  if (text === '') {
    return []
  }
  const descending = text.startsWith('-')
  return [{ id: descending ? text.slice(1) : text, desc: descending }]
}

function formatSort(sorting: SortingState): string | undefined {
  const [column] = sorting
  if (column === undefined) {
    return undefined
  }
  return column.desc ? `-${column.id}` : column.id
}
