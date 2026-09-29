<script setup lang="ts">
import { computed } from 'vue'

import type { Position } from '@/api/client'
import type { LiveBar } from '@/api/live'
import { SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import type { LiveStatus } from '@/composables/useLiveBar'
import { formatPercent, formatPrice } from '@/lib/format'
import { headlineQuote, quoteTag } from '@/lib/quote'

const props = defineProps<{
  ticker: string
  position: Position | undefined
  universeName: string
  sessionDate: string | null
  bar: LiveBar | null
  status: LiveStatus
}>()

const quote = computed(() =>
  props.position ? headlineQuote(props.position, props.bar, props.sessionDate) : null,
)
</script>

<template>
  <SheetHeader>
    <SheetTitle>{{ ticker }}</SheetTitle>
    <SheetDescription v-if="position">
      {{ position.name }} · {{ position.sector ?? 'Unclassified' }}
    </SheetDescription>
    <SheetDescription v-else>Not in {{ universeName }}.</SheetDescription>

    <div v-if="quote?.price != null" class="flex items-baseline gap-3 pt-2">
      <span class="text-2xl font-semibold tabular-nums">{{ formatPrice(quote.price) }}</span>
      <span
        v-if="quote.change !== null"
        class="tabular-nums"
        :class="quote.change < 0 ? 'text-red-600' : 'text-emerald-600'"
      >
        {{ formatPercent(quote.change, { showPlus: true }) }}
      </span>
      <span class="text-xs text-muted-foreground">
        {{ quoteTag(quote, bar, status, sessionDate) }}
      </span>
    </div>
  </SheetHeader>
</template>
