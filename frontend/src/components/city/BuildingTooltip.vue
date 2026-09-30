<script setup lang="ts">
import { computed } from 'vue'

import type { Position } from '@/api/client'
import type { BuildingHover } from '@/lib/cityView'
import { sectorOf } from '@/lib/positions'

const props = defineProps<{
  position: Position
  hover: BuildingHover
}>()

const POINTER_GAP = 12 // px between the pointer and the tooltip

/** Beside the pointer, flipped towards the middle so it never runs off the canvas. */
const placement = computed(() => {
  const { x, y, canvasWidth, canvasHeight } = props.hover
  const shiftX = x > canvasWidth / 2 ? `calc(-100% - ${POINTER_GAP}px)` : `${POINTER_GAP}px`
  const shiftY = y > canvasHeight / 2 ? `calc(-100% - ${POINTER_GAP}px)` : `${POINTER_GAP}px`
  return { left: `${x}px`, top: `${y}px`, transform: `translate(${shiftX}, ${shiftY})` }
})
</script>

<template>
  <div
    role="tooltip"
    class="pointer-events-none absolute z-10 max-w-64 rounded-md border bg-popover px-3 py-2 text-sm text-popover-foreground shadow-md"
    :style="placement"
  >
    <p class="font-semibold">{{ position.ticker }}</p>
    <p>{{ position.name }}</p>
    <p class="text-xs text-muted-foreground">{{ sectorOf(position) }}</p>
  </div>
</template>
