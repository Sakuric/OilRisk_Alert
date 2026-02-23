import { ref, watch } from 'vue'
import { getTimeseries } from '@/api/risk'
import { useRiskStore } from '@/stores/risk'
import { useAppStore } from '@/stores/app'
import type { TimeseriesData } from '@/types/risk'

export function useTimeseries() {
  const riskStore = useRiskStore()
  const appStore = useAppStore()
  const data = ref<TimeseriesData | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetch() {
    loading.value = true
    error.value = null
    try {
      const res = await getTimeseries({
        start: appStore.timeRange.start,
        end: appStore.timeRange.end,
      })
      data.value = res.data.data
      riskStore.setTimeseries(res.data.data)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Unknown error'
    } finally {
      loading.value = false
    }
  }

  watch(() => appStore.timeRange, fetch, { immediate: true })

  return { data, loading, error, fetch }
}
