<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'

import type { MetricInfo } from '@/api/client'
import CityCanvas from '@/components/city/CityCanvas.vue'
import MetricPicker from '@/components/city/MetricPicker.vue'
import ViewModeToggle from '@/components/city/ViewModeToggle.vue'
import { useQueryHeight } from '@/composables/useQueryState'
import { styleBuildings } from '@/lib/cityAppearance'
import { layoutCity } from '@/lib/cityLayout'
import type { CityViewMode } from '@/lib/cityView'
import { useUniverseStore } from '@/stores/universe'

/** What the heights show until the viewer picks; the list's first default column. */
const DEFAULT_HEIGHT_METRIC = 'one_year_return'

const route = useRoute()
const store = useUniverseStore()

const height = useQueryHeight(DEFAULT_HEIGHT_METRIC)
const heightMetric = computed(() => metricOrFirst(height.value))
const viewMode = ref<CityViewMode>('3d')

const layout = computed(() => layoutCity(store.positions))
const buildings = computed(() =>
  styleBuildings(layout.value.buildings, store.positions, heightMetric.value),
)

// Three.js draws with WebGL 2. Browsers without it (and the test environment) get a pointer to
// the list, which shows the same data.
const canDraw3d = typeof WebGL2RenderingContext !== 'undefined'

/** A key the catalogue doesn't know (an old link, say) shows its first metric instead. */
function metricOrFirst(key: string): MetricInfo {
  // the catalogue is loaded with the universe, so it's never empty once this view shows
  return store.metricsCatalogue.find((metric) => metric.key === key) ?? store.metricsCatalogue[0]!
}
</script>

<template>
  <section class="relative h-full">
    <template v-if="canDraw3d">
      <CityCanvas :buildings="buildings" :view-mode="viewMode" />
      <div class="absolute top-3 left-3">
        <MetricPicker
          label="Height"
          :metrics="store.metricsCatalogue"
          :model-value="heightMetric.key"
          @update:model-value="(key) => (height = key)"
        />
      </div>
      <ViewModeToggle v-model="viewMode" class="absolute top-3 right-3" />
    </template>
    <p v-else class="p-6 text-sm text-muted-foreground">
      The 3D city needs WebGL 2, which this browser doesn't provide.
      <RouterLink
        :to="{ name: 'list', params: { universeId: route.params.universeId }, query: route.query }"
        class="text-primary underline"
      >
        The list
      </RouterLink>
      shows the same data.
    </p>
    <RouterView />
  </section>
</template>
