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
    <!-- brand left, the universe on screen centred (the page's heading), views right -->
    <header class="grid grid-cols-[1fr_auto_1fr] items-center gap-4 border-b px-6 py-3">
      <RouterLink to="/" class="justify-self-start text-2xl font-bold tracking-tight">
        Stocktown
      </RouterLink>
      <div class="flex items-baseline gap-3">
        <h1 v-if="store.universe" class="text-base font-medium">{{ store.universe.name }}</h1>
        <span v-if="store.universe?.session_date" class="text-sm text-muted-foreground">
          Prices as of {{ store.universe.session_date }}
        </span>
      </div>
      <nav class="flex gap-4 justify-self-end text-sm">
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
          Town
        </RouterLink>
      </nav>
    </header>

    <main class="flex-1 overflow-auto">
      <p v-if="isUnknownUniverse" class="p-6">There is no universe called "{{ universeId }}".</p>
      <p v-else-if="store.error" class="p-6">
        Couldn't load the data.
        <button class="text-primary underline" @click="store.load(universeId)">Try again</button>
      </p>
      <div v-else-if="store.universe === null" class="p-6" aria-busy="true">
        <p class="text-sm text-muted-foreground">
          Building today's snapshot… The first load after the server starts takes a few seconds.
        </p>
        <div class="mt-4 space-y-2" aria-hidden="true">
          <div v-for="bar in 12" :key="bar" class="h-6 animate-pulse rounded bg-muted" />
        </div>
      </div>
      <RouterView v-else />
    </main>
  </div>
</template>
