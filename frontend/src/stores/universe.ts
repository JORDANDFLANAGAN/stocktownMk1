import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import type { MetricInfo, Universe } from '@/api/client'
import { useApi } from '@/composables/useApi'

/** The universe on screen (its positions and their metrics) plus the metric catalogue. */
export const useUniverseStore = defineStore('universe', () => {
  const api = useApi()

  const universe = ref<Universe | null>(null)
  const metricsCatalogue = ref<MetricInfo[]>([])
  const loading = ref(false)
  const error = ref<unknown>(null) // usually an ApiError; a TypeError if the network is down

  const positions = computed(() => universe.value?.positions ?? [])

  async function load(universeId: string): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const [loadedUniverse, loadedMetrics] = await Promise.all([
        api.fetchUniverse(universeId),
        api.fetchMetrics(),
      ])
      universe.value = loadedUniverse
      metricsCatalogue.value = loadedMetrics
    } catch (caught) {
      error.value = caught // the universe already on screen (if any) stays
    } finally {
      loading.value = false
    }
  }

  return { universe, metricsCatalogue, loading, error, positions, load }
})
