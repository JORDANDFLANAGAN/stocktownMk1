<script setup lang="ts">
import { Button } from '@/components/ui/button'
import { CITY_VIEW_MODES, type CityViewMode } from '@/lib/cityView'

defineProps<{ modelValue: CityViewMode }>()

const emit = defineEmits<{
  'update:modelValue': [mode: CityViewMode]
}>()
</script>

<template>
  <div role="group" aria-label="View" class="flex gap-1 rounded-md border bg-background p-0.5">
    <Button
      v-for="option in CITY_VIEW_MODES"
      :key="option.mode"
      size="sm"
      :variant="modelValue === option.mode ? 'default' : 'ghost'"
      :aria-pressed="modelValue === option.mode"
      @click="emit('update:modelValue', option.mode)"
    >
      {{ option.label }}
    </Button>
  </div>
</template>
