import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getCurrentRisk, getTimeseries } from '@/api/risk'
import type { CurrentRisk, TimeseriesData } from '@/types/risk'

export const useRiskStore = defineStore('risk', () => {
  const currentRisk = ref<CurrentRisk | null>(null)
  const timeseriesData = ref<TimeseriesData | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const stale = ref(false)

  function setCurrentRisk(data: CurrentRisk) {
    currentRisk.value = data
    stale.value = false
  }

  function setTimeseries(data: TimeseriesData) {
    timeseriesData.value = data
  }

  function setLoading(val: boolean) {
    loading.value = val
  }

  function setError(msg: string | null) {
    error.value = msg
  }

  function markStale() {
    stale.value = true
  }

  async function fetchCurrentRisk() {
    loading.value = true
    error.value = null
    try {
      const res = await getCurrentRisk()
      currentRisk.value = res.data.data
      stale.value = false
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Unknown error'
      stale.value = true
    } finally {
      loading.value = false
    }
  }

  async function fetchTimeseries(start?: string, end?: string) {
    try {
      const res = await getTimeseries({ start, end })
      timeseriesData.value = res.data.data
    } catch {
      // silent — timeseries refresh is best-effort
    }
  }

  return {
    currentRisk,
    timeseriesData,
    loading,
    error,
    stale,
    setCurrentRisk,
    setTimeseries,
    setLoading,
    setError,
    markStale,
    fetchCurrentRisk,
    fetchTimeseries,
  }
})
