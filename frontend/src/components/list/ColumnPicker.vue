<script setup lang="ts">
import type { MetricInfo } from '@/api/client'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

const props = defineProps<{
  metrics: MetricInfo[]
  visibleMetrics: string[]
}>()

const emit = defineEmits<{
  'update:visibleMetrics': [keys: string[]]
}>()

/** Shows or hides one metric column, keeping catalogue order whatever order they're ticked in. */
function setShown(key: string, shown: boolean): void {
  const chosen = props.metrics
    .map((metric) => metric.key)
    .filter((candidate) => (candidate === key ? shown : props.visibleMetrics.includes(candidate)))
  emit('update:visibleMetrics', chosen)
}

/** Keeps the menu open, so several columns can be ticked in one go. */
function stayOpen(event: Event): void {
  event.preventDefault()
}
</script>

<template>
  <DropdownMenu>
    <DropdownMenuTrigger as-child>
      <Button variant="outline" size="sm">Columns</Button>
    </DropdownMenuTrigger>
    <DropdownMenuContent align="end" class="w-56">
      <DropdownMenuCheckboxItem
        v-for="metric in metrics"
        :key="metric.key"
        :model-value="visibleMetrics.includes(metric.key)"
        @update:model-value="(shown) => setShown(metric.key, shown === true)"
        @select="stayOpen"
      >
        {{ metric.label }}
      </DropdownMenuCheckboxItem>
    </DropdownMenuContent>
  </DropdownMenu>
</template>
