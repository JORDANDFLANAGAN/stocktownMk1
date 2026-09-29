<script setup lang="ts">
import type { MetricInfo, Position } from '@/api/client'
import { formatMetricValue } from '@/lib/format'

defineProps<{
  position: Position
  metrics: MetricInfo[]
  sessionDate: string | null
}>()
</script>

<template>
  <section aria-labelledby="city-metrics-heading" class="flex flex-col gap-2">
    <div class="flex items-baseline justify-between">
      <h3 id="city-metrics-heading" class="text-sm font-medium">Metrics</h3>
      <!-- every metric is from the snapshot, even while the header price is live -->
      <span v-if="sessionDate" class="text-xs text-muted-foreground">
        At the close, {{ sessionDate }}
      </span>
    </div>
    <dl class="grid grid-cols-[1fr_auto] gap-x-4 gap-y-1.5 text-sm">
      <template v-for="metric in metrics" :key="metric.key">
        <dt class="text-muted-foreground">{{ metric.label }}</dt>
        <dd class="text-right tabular-nums">
          {{ formatMetricValue(position.metrics[metric.key] ?? null, metric) }}
        </dd>
      </template>
    </dl>
  </section>
</template>
