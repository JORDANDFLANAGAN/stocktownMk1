<script setup lang="ts">
import { computed, toRef } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { Sheet, SheetContent } from '@/components/ui/sheet'
import { useLiveBar } from '@/composables/useLiveBar'
import { useUniverseStore } from '@/stores/universe'
import CityMetricsSection from './CityMetricsSection.vue'
import DrawerHeader from './DrawerHeader.vue'

const props = defineProps<{ ticker: string }>()

const route = useRoute()
const router = useRouter()
const store = useUniverseStore()
// one connection per open drawer; the sections get the bar as a prop
const { bar } = useLiveBar(toRef(props, 'ticker'))

const position = computed(() => store.positions.find(({ ticker }) => ticker === props.ticker))

/** A press outside (e.g. on another row) picks that row instead; X and Esc close the drawer. */
function keepOpen(event: Event): void {
  event.preventDefault()
}

/** Back to the view underneath (list or city), keeping sort and filters. */
function close(): void {
  const parentView = route.matched[route.matched.length - 2]
  router.push({
    name: parentView?.name,
    params: { universeId: route.params.universeId },
    query: route.query,
  })
}
</script>

<template>
  <!-- Open for as long as the route is: closing it means leaving the route. Not modal, so the
       view underneath stays usable and choosing another row or building switches the drawer in
       place rather than closing it and opening a new one. -->
  <Sheet :open="true" :modal="false" @update:open="close">
    <SheetContent side="right" @interact-outside="keepOpen">
      <DrawerHeader
        :ticker="ticker"
        :position="position"
        :universe-name="store.universe?.name ?? ''"
        :session-date="store.universe?.session_date ?? null"
        :bar="bar"
      />
      <div v-if="position" class="flex-1 overflow-y-auto px-4 pb-4">
        <CityMetricsSection
          :position="position"
          :metrics="store.metricsCatalogue"
          :session-date="store.universe?.session_date ?? null"
        />
      </div>
    </SheetContent>
  </Sheet>
</template>
