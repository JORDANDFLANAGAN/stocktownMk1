<script setup lang="ts">
import { ChevronDownIcon } from '@lucide/vue'
import { computed } from 'vue'

import type { MetricInfo } from '@/api/client'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

const props = defineProps<{
  label: string
  metrics: MetricInfo[]
  modelValue: string
}>()

const emit = defineEmits<{
  'update:modelValue': [key: string]
}>()

const chosenLabel = computed(
  () => props.metrics.find((metric) => metric.key === props.modelValue)?.label,
)
</script>

<template>
  <DropdownMenu>
    <DropdownMenuTrigger as-child>
      <Button variant="outline" size="sm">
        {{ label }}: {{ chosenLabel }}
        <ChevronDownIcon class="opacity-50" />
      </Button>
    </DropdownMenuTrigger>
    <DropdownMenuContent class="w-64">
      <DropdownMenuRadioGroup
        :model-value="modelValue"
        @update:model-value="(key) => emit('update:modelValue', String(key))"
      >
        <DropdownMenuRadioItem v-for="metric in metrics" :key="metric.key" :value="metric.key">
          {{ metric.label }}
        </DropdownMenuRadioItem>
      </DropdownMenuRadioGroup>
    </DropdownMenuContent>
  </DropdownMenu>
</template>
