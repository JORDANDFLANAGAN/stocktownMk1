<script setup lang="ts">
import { RouterView } from 'vue-router'

import { useUniverseStore } from '@/stores/universe'

const store = useUniverseStore()
</script>

<template>
  <section class="p-6">
    <p class="text-muted-foreground">
      List view: {{ store.positions.length }} positions (the table arrives in Phase 4).
    </p>
    <RouterView />
  </section>
</template>
