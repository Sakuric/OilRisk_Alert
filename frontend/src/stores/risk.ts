import { defineStore } from 'pinia'
import { ref } from 'vue'
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
  }
})
