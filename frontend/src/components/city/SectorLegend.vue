<script setup lang="ts">
import type { SectorColour } from '@/lib/cityAppearance'

defineProps<{ sectors: SectorColour[] }>()
</script>

<template>
  <ul
    aria-label="Sector colours"
    class="flex flex-col gap-1 rounded-md border bg-background/90 p-2 text-xs shadow-sm"
  >
    <li v-for="{ sector, colour } in sectors" :key="sector" class="flex items-center gap-2">
      <span
        class="size-3 shrink-0 rounded-sm"
        :style="{ backgroundColor: colour }"
        aria-hidden="true"
      />
      {{ sector }}
    </li>
  </ul>
</template>
