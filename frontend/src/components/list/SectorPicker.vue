<script setup lang="ts">
import { CheckIcon, ChevronDownIcon } from '@lucide/vue'
import {
  ComboboxAnchor,
  ComboboxContent,
  ComboboxEmpty,
  ComboboxInput,
  ComboboxItem,
  ComboboxItemIndicator,
  ComboboxPortal,
  ComboboxRoot,
  ComboboxTrigger,
  ComboboxViewport,
} from 'reka-ui'
import { computed } from 'vue'

import { Button } from '@/components/ui/button'

const props = defineProps<{
  allSectors: string[]
  sectors: string[]
}>()

const emit = defineEmits<{
  'update:sectors': [sectors: string[]]
}>()

/** No sectors chosen means every sector is shown. */
const triggerLabel = computed(() => {
  if (props.sectors.length === 0) return 'All sectors'
  if (props.sectors.length === 1) return props.sectors[0]
  return `${props.sectors.length} sectors`
})

const chosen = computed({
  get: () => props.sectors,
  // keeps the universe's sector order, whatever order they're ticked in
  set: (picked: string[]) =>
    emit(
      'update:sectors',
      props.allSectors.filter((sector) => picked.includes(sector)),
    ),
})
</script>

<template>
  <ComboboxRoot v-model="chosen" multiple>
    <ComboboxAnchor as-child>
      <!-- reka's trigger is built to sit beside an input, so it's unfocusable and labelled
           "Show popup"; here it is the only control, so it's focusable and named by its text -->
      <ComboboxTrigger as-child tabindex="0" :aria-label="triggerLabel">
        <Button variant="outline" size="sm">
          {{ triggerLabel }}
          <ChevronDownIcon class="opacity-50" />
        </Button>
      </ComboboxTrigger>
    </ComboboxAnchor>
    <ComboboxPortal>
      <ComboboxContent
        position="popper"
        align="end"
        :side-offset="4"
        class="z-50 w-56 overflow-hidden rounded-md bg-popover p-1 text-popover-foreground shadow-md ring-1 ring-foreground/10"
      >
        <ComboboxInput
          auto-focus
          placeholder="Search sectors"
          aria-label="Search sectors"
          class="mb-1 w-full rounded-sm border px-2 py-1.5 text-sm outline-hidden"
        />
        <ComboboxViewport class="max-h-72 overflow-y-auto">
          <ComboboxEmpty class="py-4 text-center text-sm text-muted-foreground">
            No sector matches
          </ComboboxEmpty>
          <ComboboxItem
            v-for="sector in allSectors"
            :key="sector"
            :value="sector"
            class="relative flex cursor-default items-center rounded-sm py-1.5 pr-8 pl-2 text-sm outline-hidden select-none data-highlighted:bg-accent data-highlighted:text-accent-foreground"
          >
            {{ sector }}
            <ComboboxItemIndicator class="absolute right-2 flex items-center">
              <CheckIcon class="size-4" />
            </ComboboxItemIndicator>
          </ComboboxItem>
        </ComboboxViewport>
      </ComboboxContent>
    </ComboboxPortal>
  </ComboboxRoot>
</template>
