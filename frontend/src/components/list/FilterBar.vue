<script setup lang="ts">
import { ref } from 'vue'

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

function toggleSector(sector: string): void {
  const chosen = props.sectors.includes(sector)
    ? props.sectors.filter((existing) => existing !== sector)
    : [...props.sectors, sector]
  emit('update:sectors', chosen)
}

function onSearchInput(): void {
  emit('update:search', searchText.value)
}
</script>

<template>
  <div class="flex flex-wrap items-center gap-2">
    <input
      v-model="searchText"
      type="search"
      placeholder="Search ticker or name"
      aria-label="Search ticker or name"
      class="rounded-md border px-3 py-1.5 text-sm"
      @input="onSearchInput"
    />
    <button
      v-for="sector in allSectors"
      :key="sector"
      type="button"
      :aria-pressed="sectors.includes(sector)"
      class="rounded-full border px-3 py-1 text-xs aria-pressed:border-primary aria-pressed:bg-primary aria-pressed:text-primary-foreground"
      @click="toggleSector(sector)"
    >
      {{ sector }}
    </button>
  </div>
</template>
