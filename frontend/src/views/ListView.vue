<script setup lang="ts">
import { computed } from 'vue'
import { RouterView, useRoute, useRouter } from 'vue-router'

import ColumnPicker from '@/components/list/ColumnPicker.vue'
import FilterBar from '@/components/list/FilterBar.vue'
import PositionsTable from '@/components/list/PositionsTable.vue'
import { useQueryColumns, useQueryFilters, useQuerySort } from '@/composables/useQueryState'
import { filterPositions, sectorsIn } from '@/lib/positions'
import { useUniverseStore } from '@/stores/universe'

/** Metric columns shown until the viewer picks others; the drawer shows every metric. */
const DEFAULT_METRIC_COLUMNS = ['one_year_return', 'day_change']

const route = useRoute()
const router = useRouter()
const store = useUniverseStore()

const sorting = useQuerySort()
const { sectors, search } = useQueryFilters()
const visibleMetrics = useQueryColumns(DEFAULT_METRIC_COLUMNS)

const allSectors = computed(() => sectorsIn(store.positions))
const visiblePositions = computed(() =>
  filterPositions(store.positions, { sectors: sectors.value, search: search.value }),
)
const selectedTicker = computed(() =>
  typeof route.params.ticker === 'string' ? route.params.ticker : undefined,
)

function openDrawer(ticker: string): void {
  // query kept so sort and filters survive opening and closing the drawer
  router.push({ name: 'list-ticker', params: { ...route.params, ticker }, query: route.query })
}
</script>

<template>
  <section class="flex flex-col gap-3 p-6">
    <FilterBar v-model:sectors="sectors" v-model:search="search" :all-sectors="allSectors" />
    <div class="flex items-center justify-between">
      <p class="text-sm text-muted-foreground">
        Showing {{ visiblePositions.length }} of {{ store.positions.length }}
      </p>
      <ColumnPicker v-model:visible-metrics="visibleMetrics" :metrics="store.metricsCatalogue" />
    </div>
    <PositionsTable
      v-model:sorting="sorting"
      :positions="visiblePositions"
      :metrics="store.metricsCatalogue"
      :visible-metrics="visibleMetrics"
      :selected-ticker="selectedTicker"
      @select="openDrawer"
    />
    <RouterView />
  </section>
</template>
