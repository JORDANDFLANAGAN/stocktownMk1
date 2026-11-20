<script setup lang="ts">
import { GAIN_COLOUR, LOSS_COLOUR } from '@/lib/cityAppearance'
</script>

<template>
  <ul
    aria-label="Day change colours"
    class="flex flex-col gap-1 rounded-md border bg-background/90 p-2 text-xs shadow-sm"
  >
    <li class="flex items-center gap-2">
      <span class="size-3 shrink-0 rounded-sm" :style="{ backgroundColor: GAIN_COLOUR }" aria-hidden="true" />
      Positive
    </li>
    <li class="flex items-center gap-2">
      <span class="size-3 shrink-0 rounded-sm" :style="{ backgroundColor: LOSS_COLOUR }" aria-hidden="true" />
      Negative
    </li>
  </ul>
</template>
