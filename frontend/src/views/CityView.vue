<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'

import CityCanvas from '@/components/city/CityCanvas.vue'
import { layoutCity } from '@/lib/cityLayout'
import { useUniverseStore } from '@/stores/universe'

const route = useRoute()
const store = useUniverseStore()

const layout = computed(() => layoutCity(store.positions))

// Three.js draws with WebGL 2. Browsers without it (and the test environment) get a pointer to
// the list, which shows the same data.
const canDraw3d = typeof WebGL2RenderingContext !== 'undefined'
</script>

<template>
  <section class="h-full">
    <CityCanvas v-if="canDraw3d" :buildings="layout.buildings" />
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
