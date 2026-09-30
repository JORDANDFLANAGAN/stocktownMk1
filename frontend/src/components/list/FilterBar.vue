<script setup lang="ts">
import { ref } from 'vue'

import SectorPicker from '@/components/list/SectorPicker.vue'

const props = defineProps<{
  allSectors: string[]
  sectors: string[]
  search: string
}>()

const emit = defineEmits<{
  'update:sectors': [sectors: string[]]
  'update:search': [search: string]
}>()

// The input keeps its own text: the URL updates a moment later, and binding the input straight
// to it would drop keystrokes typed in between.
const searchText = ref(props.search)

function onSearchInput(): void {
  emit('update:search', searchText.value)
}
</script>

<template>
  <div class="flex items-center justify-between gap-2">
    <input
      v-model="searchText"
      type="search"
      placeholder="Search ticker or name"
      aria-label="Search ticker or name"
      class="rounded-md border px-3 py-1.5 text-sm"
      @input="onSearchInput"
    />
    <SectorPicker
      :all-sectors="allSectors"
      :sectors="sectors"
      @update:sectors="(chosen) => emit('update:sectors', chosen)"
    />
  </div>
</template>
