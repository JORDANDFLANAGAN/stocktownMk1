<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { useUniverseStore } from '@/stores/universe'

const props = defineProps<{ ticker: string }>()

const route = useRoute()
const router = useRouter()
const store = useUniverseStore()

const position = computed(() => store.positions.find(({ ticker }) => ticker === props.ticker))

/** Back to the view underneath (list or city), keeping sort and filters. */
function close(): void {
  const parentView = route.matched[route.matched.length - 2]
  router.push({
    name: parentView?.name,
    params: { universeId: route.params.universeId },
    query: route.query,
  })
}
</script>

<template>
  <!-- open for as long as the route is: closing it means leaving the route -->
  <Sheet :open="true" @update:open="close">
    <SheetContent side="right">
      <SheetHeader>
        <SheetTitle>{{ ticker }}</SheetTitle>
        <SheetDescription v-if="position">
          {{ position.name }} · {{ position.sector ?? 'Unclassified' }}
        </SheetDescription>
        <SheetDescription v-else>Not in {{ store.universe?.name }}.</SheetDescription>
      </SheetHeader>
    </SheetContent>
  </Sheet>
</template>
