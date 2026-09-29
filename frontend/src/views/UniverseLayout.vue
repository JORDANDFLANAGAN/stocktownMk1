<script setup lang="ts">
import { computed, watch } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'

import { ApiError } from '@/api/client'
import { useUniverseStore } from '@/stores/universe'

const route = useRoute()
const store = useUniverseStore()

const universeId = computed(() => String(route.params.universeId))
const isUnknownUniverse = computed(
  () => store.error instanceof ApiError && store.error.status === 404,
)

watch(universeId, (id) => store.load(id), { immediate: true })
</script>

<template>
  <div class="flex h-screen flex-col">
    <header class="flex items-baseline gap-4 border-b px-6 py-3">
      <h1 class="text-lg font-semibold">{{ store.universe?.name ?? 'Market City' }}</h1>
      <span v-if="store.universe?.session_date" class="text-sm text-muted-foreground">
        Prices as of {{ store.universe.session_date }}
      </span>
      <nav class="ml-auto flex gap-4 text-sm">
        <!-- query carried over: filters and metric picks are shared by both views -->
        <RouterLink
          :to="{ name: 'list', params: { universeId }, query: route.query }"
          active-class="font-semibold text-primary"
        >
          List
        </RouterLink>
        <RouterLink
          :to="{ name: 'city', params: { universeId }, query: route.query }"
          active-class="font-semibold text-primary"
        >
          City
        </RouterLink>
      </nav>
    </header>

    <main class="flex-1 overflow-auto">
      <p v-if="isUnknownUniverse" class="p-6">There is no universe called "{{ universeId }}".</p>
      <p v-else-if="store.error" class="p-6">
        Couldn't load the data.
        <button class="text-primary underline" @click="store.load(universeId)">Try again</button>
      </p>
      <p v-else-if="store.universe === null" class="p-6 text-muted-foreground">Loading…</p>
      <RouterView v-else />
    </main>
  </div>
</template>
