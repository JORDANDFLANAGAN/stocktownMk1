<script setup lang="ts">
import { computed, toRef } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { Sheet, SheetContent } from '@/components/ui/sheet'
import { useLiveBar } from '@/composables/useLiveBar'
import { useUniverseStore } from '@/stores/universe'
import DrawerHeader from './DrawerHeader.vue'

const props = defineProps<{ ticker: string }>()

const route = useRoute()
const router = useRouter()
const store = useUniverseStore()
// one connection per open drawer; the sections get the bar as a prop
const { bar } = useLiveBar(toRef(props, 'ticker'))

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
      <DrawerHeader
        :ticker="ticker"
        :position="position"
        :universe-name="store.universe?.name ?? ''"
        :session-date="store.universe?.session_date ?? null"
        :bar="bar"
      />
    </SheetContent>
  </Sheet>
</template>
