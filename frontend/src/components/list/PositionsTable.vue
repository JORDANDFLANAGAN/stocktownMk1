<script setup lang="ts">
import {
  columnVisibilityFeature,
  createColumnHelper,
  createSortedRowModel,
  FlexRender,
  rowSortingFeature,
  sortFn_alphanumeric,
  tableFeatures,
  useTable,
  type SortingState,
} from '@tanstack/vue-table'
import { computed, ref, toRef, watch } from 'vue'

import type { MetricInfo, Position } from '@/api/client'
import { formatMetricValue, formatPercent } from '@/lib/format'
import { sectorOf } from '@/lib/positions'

const props = defineProps<{
  positions: Position[]
  metrics: MetricInfo[]
  visibleMetrics: string[] // metric keys whose columns are shown
  sorting: SortingState
  selectedTicker?: string
}>()

const emit = defineEmits<{
  'update:sorting': [sorting: SortingState]
  select: [ticker: string]
}>()

const TEXT_COLUMNS = new Set(['ticker', 'name', 'sector'])
const TRUNCATED_COLUMNS = new Set(['name']) // long names cut short; the full one shows on hover

const features = tableFeatures({
  columnVisibilityFeature,
  rowSortingFeature,
  sortedRowModel: createSortedRowModel(),
  sortFns: { alphanumeric: sortFn_alphanumeric },
})
const column = createColumnHelper<typeof features, Position>()

// Fixed columns first, then one per metric in catalogue order, so a new backend metric appears
// with no frontend change. Built once: the catalogue is loaded before the list is shown.
// Missing metric values read as `undefined`, which always sorts last.
const columns = column.columns([
  column.accessor('ticker', { header: 'Ticker' }),
  column.accessor('name', { header: 'Name' }),
  column.accessor(sectorOf, { id: 'sector', header: 'Sector' }),
  column.accessor('weight', {
    header: 'Weight',
    cell: ({ getValue }) => formatPercent(getValue(), { digits: 2 }),
  }),
  ...props.metrics.map((metric) =>
    column.accessor((position) => position.metrics[metric.key] ?? undefined, {
      id: metric.key,
      header: metric.label,
      sortUndefined: 'last',
      cell: ({ getValue }) => formatMetricValue(getValue() ?? null, metric),
    }),
  ),
])

const table = useTable({
  features,
  columns,
  data: toRef(props, 'positions'),
  getRowId: (position: Position) => position.ticker,
  // hidden metric columns still exist, so the list can stay sorted by one
  state: toRef(() => ({ sorting: props.sorting, columnVisibility: metricVisibility() })),
  onSortingChange: (next) =>
    emit('update:sorting', typeof next === 'function' ? next(props.sorting) : next),
  enableSortingRemoval: false,
})

function metricVisibility(): Record<string, boolean> {
  return Object.fromEntries(
    props.metrics.map((metric) => [metric.key, props.visibleMetrics.includes(metric.key)]),
  )
}

// The body is one tab stop (roving tabindex): the arrow keys move between rows.
const activeTicker = ref<string | undefined>() // the row that last had focus
const rowElements = new Map<string, HTMLElement>()

const rows = computed(() => table.getRowModel().rows)
/** The one row in the tab order: the last one focused, else the selected one, else the first. */
const tabStop = computed(() => {
  const tickers = rows.value.map((row) => row.id)
  if (activeTicker.value !== undefined && tickers.includes(activeTicker.value)) {
    return activeTicker.value
  }
  if (props.selectedTicker !== undefined && tickers.includes(props.selectedTicker)) {
    return props.selectedTicker
  }
  return tickers[0]
})

function rememberRow(ticker: string, element: unknown): void {
  // Vue passes null when the row unmounts
  if (element instanceof HTMLElement) rowElements.set(ticker, element)
  else rowElements.delete(ticker)
}

/** Focuses a row (which scrolls it into view); its focus handler makes it the tab stop. */
function focusRow(ticker: string | undefined): void {
  if (ticker !== undefined) rowElements.get(ticker)?.focus()
}

function onRowKeydown(event: KeyboardEvent, index: number): void {
  const last = rows.value.length - 1
  const targets: Record<string, number> = {
    ArrowDown: index + 1,
    ArrowUp: index - 1,
    Home: 0,
    End: last,
  }
  const target = targets[event.key]
  if (target === undefined) return
  event.preventDefault() // the focused row scrolls itself into view; the page shouldn't jump too
  focusRow(rows.value[target]?.id) // past either end there's no row, so focus stays put
}

// Closing the drawer puts focus back on the row it was opened from.
watch(
  () => props.selectedTicker,
  (now, before) => {
    if (now === undefined && before !== undefined) focusRow(before)
  },
)

function ariaSort(direction: false | 'asc' | 'desc') {
  if (direction === false) return 'none'
  return direction === 'asc' ? 'ascending' : 'descending'
}
</script>

<template>
  <table role="grid" aria-label="Holdings" class="w-full text-sm">
    <thead class="sticky top-0 bg-background">
      <tr v-for="group in table.getHeaderGroups()" :key="group.id" class="border-b">
        <th
          v-for="header in group.headers"
          :key="header.id"
          :aria-sort="ariaSort(header.column.getIsSorted())"
          class="px-3 py-2 font-medium whitespace-nowrap"
          :class="TEXT_COLUMNS.has(header.column.id) ? 'text-left' : 'text-right'"
        >
          <button type="button" @click="header.column.toggleSorting()">
            <FlexRender :header="header" />
            <span v-if="header.column.getIsSorted() === 'asc'" aria-hidden="true"> ▲</span>
            <span v-else-if="header.column.getIsSorted() === 'desc'" aria-hidden="true"> ▼</span>
          </button>
        </th>
      </tr>
    </thead>
    <tbody>
      <tr
        v-for="(row, index) in rows"
        :key="row.id"
        :ref="(element) => rememberRow(row.id, element)"
        :aria-selected="row.id === selectedTicker"
        :tabindex="row.id === tabStop ? 0 : -1"
        class="scroll-mt-10 cursor-pointer border-b hover:bg-muted aria-selected:bg-primary/10"
        @click="emit('select', row.id)"
        @keydown.enter="emit('select', row.id)"
        @keydown="onRowKeydown($event, index)"
        @focus="activeTicker = row.id"
      >
        <td
          v-for="cell in row.getVisibleCells()"
          :key="cell.id"
          class="px-3 py-1.5 whitespace-nowrap"
          :class="[
            TEXT_COLUMNS.has(cell.column.id) ? 'text-left' : 'text-right tabular-nums',
            { 'max-w-64 truncate': TRUNCATED_COLUMNS.has(cell.column.id) },
          ]"
          :title="TRUNCATED_COLUMNS.has(cell.column.id) ? String(cell.getValue()) : undefined"
        >
          <FlexRender :cell="cell" />
        </td>
      </tr>
    </tbody>
  </table>
</template>
