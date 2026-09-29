<script setup lang="ts">
import { RouterView } from 'vue-router'

import { useUniverseStore } from '@/stores/universe'

const store = useUniverseStore()
</script>

<template>
  <section class="p-6">
    <p class="text-muted-foreground">
      City view: {{ store.positions.length }} buildings (the city arrives in Phase 6).
    </p>
    <RouterView />
  </section>
</template>
