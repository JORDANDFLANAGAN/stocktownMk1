<script setup lang="ts">
import { computed, onScopeDispose, watch } from 'vue'

import { ApiError, type Instrument } from '@/api/client'
import { Button } from '@/components/ui/button'
import { formatCompactMoney, formatOrDash, formatPercent, formatRatio } from '@/lib/format'
import { useFundamentalsStore } from '@/stores/fundamentals'

/** Wait this long on a ticker before asking Finnhub (60 calls/min), so flicking through rows is free. */
const FETCH_AFTER_MS = 300

const props = defineProps<{ ticker: string }>()

const store = useFundamentalsStore()
const entry = computed(() => store.entryFor(props.ticker))

const state = computed<'loading' | 'not-found' | 'unavailable' | 'ready'>(() => {
  const current = entry.value
  if (current?.data) return 'ready'
  if (current?.error instanceof ApiError && current.error.status === 404) return 'not-found'
  if (current?.error) return 'unavailable'
  return 'loading' // fetching, or still waiting for the drawer to settle on this ticker
})

const rows = computed(() => (entry.value?.data ? rowsFor(entry.value.data) : []))

function rowsFor(instrument: Instrument): { label: string; value: string }[] {
  return [
    { label: 'Market cap', value: formatOrDash(instrument.market_cap_usd, formatCompactMoney) },
    { label: 'P/E', value: formatOrDash(instrument.pe_ratio, (pe) => formatRatio(pe, 1)) },
    { label: 'Earnings yield', value: formatOrDash(instrument.earnings_yield, formatPercent) },
    {
      label: 'Dividend yield',
      value: formatOrDash(instrument.dividend_yield, (dy) => formatPercent(dy, { digits: 2 })),
    },
  ]
}

let pendingFetch: ReturnType<typeof setTimeout> | undefined
watch(
  () => props.ticker,
  (ticker) => {
    clearTimeout(pendingFetch)
    pendingFetch = setTimeout(() => store.load(ticker), FETCH_AFTER_MS)
  },
  { immediate: true },
)
onScopeDispose(() => clearTimeout(pendingFetch)) // closed before settling: nothing is fetched
</script>

<template>
  <section aria-labelledby="fundamentals-heading" class="flex flex-col gap-2">
    <h3 id="fundamentals-heading" class="text-sm font-medium">Fundamentals</h3>

    <dl v-if="state === 'ready'" class="grid grid-cols-[1fr_auto] gap-x-4 gap-y-1.5 text-sm">
      <template v-for="row in rows" :key="row.label">
        <dt class="text-muted-foreground">{{ row.label }}</dt>
        <dd class="text-right tabular-nums">{{ row.value }}</dd>
      </template>
    </dl>
    <p v-else-if="state === 'not-found'" class="text-sm text-muted-foreground">
      No fundamentals for this ticker.
    </p>
    <div v-else-if="state === 'unavailable'" class="flex items-center justify-between text-sm">
      <span class="text-muted-foreground">Fundamentals are unavailable right now.</span>
      <Button variant="outline" size="sm" @click="store.load(ticker)">Retry</Button>
    </div>
    <div v-else class="space-y-2" aria-busy="true" aria-label="Loading fundamentals">
      <div v-for="bar in 4" :key="bar" class="h-5 animate-pulse rounded bg-muted" />
    </div>
  </section>
</template>
