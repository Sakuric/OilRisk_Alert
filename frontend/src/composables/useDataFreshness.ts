import { ref, watch, onUnmounted } from 'vue'
import { getSystemStatus, triggerCollect } from '@/api/system'
import { useRiskStore } from '@/stores/risk'
import type { SystemStatusVO, CollectResultVO } from '@/types/system'

export type FreshnessLevel = 'realtime' | 'stale' | 'error'

const POLL_INTERVAL = 60_000
const COLLECTING_POLL_INTERVAL = 5_000

function isTradeDay(date: Date): boolean {
  const day = date.getDay()
  return day !== 0 && day !== 6
}

function getLatestTradeDate(): string {
  const now = new Date()
  while (!isTradeDay(now)) {
    now.setDate(now.getDate() - 1)
  }
  return now.toISOString().slice(0, 10)
}

export function useDataFreshness() {
  const riskStore = useRiskStore()
  const status = ref<SystemStatusVO | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const collecting = ref(false)
  const collectResult = ref<CollectResultVO | null>(null)
  const collectError = ref<string | null>(null)

  const freshnessLevel = ref<FreshnessLevel>('stale')
  const dataDate = ref<string | null>(null)
  const updatedTime = ref<string | null>(null)

  let pollTimer: ReturnType<typeof setInterval> | null = null
  let collectPollTimer: ReturnType<typeof setInterval> | null = null

  function computeFreshness(s: SystemStatusVO) {
    dataDate.value = s.dataDate
    updatedTime.value = s.lastCollectionTime
      ? s.lastCollectionTime.slice(11, 16)
      : null

    if (s.lastCollectionStatus === 'FAILED') {
      freshnessLevel.value = 'error'
      return
    }

    if (!s.dataDate) {
      freshnessLevel.value = 'stale'
      return
    }

    const latestTrade = getLatestTradeDate()
    freshnessLevel.value = s.dataDate >= latestTrade ? 'realtime' : 'stale'
  }

  async function fetchStatus() {
    loading.value = true
    error.value = null
    try {
      const res = await getSystemStatus()
      status.value = res.data.data
      computeFreshness(res.data.data)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Unknown error'
      freshnessLevel.value = 'error'
    } finally {
      loading.value = false
    }
  }

  function stopCollectPolling() {
    if (collectPollTimer) {
      clearInterval(collectPollTimer)
      collectPollTimer = null
    }
  }

  function startCollectPolling() {
    stopCollectPolling()
    collectPollTimer = setInterval(async () => {
      try {
        const res = await getSystemStatus()
        status.value = res.data.data
        computeFreshness(res.data.data)

        const st = res.data.data.lastCollectionStatus
        if (st && st !== 'RUNNING') {
          collecting.value = false
          stopCollectPolling()
          collectResult.value = {
            status: st.toLowerCase() as CollectResultVO['status'],
            message: `Collection ${st.toLowerCase()}`,
          }
          riskStore.fetchCurrentRisk()
          riskStore.fetchTimeseries()
        }
      } catch {
        // Keep polling on transient errors
      }
    }, COLLECTING_POLL_INTERVAL)
  }

  async function triggerManualCollect() {
    if (collecting.value) return
    collecting.value = true
    collectError.value = null
    collectResult.value = null
    try {
      const res = await triggerCollect()
      const triggerStatus = res.data.data.status

      if (triggerStatus === 'started' || triggerStatus === 'already_running') {
        // Async: poll status until collection completes
        startCollectPolling()
      } else {
        // Synchronous completion (fallback)
        collectResult.value = res.data.data
        collecting.value = false
        await fetchStatus()
        riskStore.fetchCurrentRisk()
        riskStore.fetchTimeseries()
      }
    } catch (e) {
      collectError.value = e instanceof Error ? e.message : 'Unknown error'
      collecting.value = false
    }
  }

  watch(dataDate, (newDate, oldDate) => {
    if (newDate && newDate !== oldDate && oldDate !== null) {
      riskStore.fetchCurrentRisk()
      riskStore.fetchTimeseries()
    }
  })

  fetchStatus()
  pollTimer = setInterval(fetchStatus, POLL_INTERVAL)

  onUnmounted(() => {
    if (pollTimer) clearInterval(pollTimer)
    stopCollectPolling()
  })

  return {
    status,
    loading,
    error,
    freshnessLevel,
    dataDate,
    updatedTime,
    collecting,
    collectResult,
    collectError,
    fetchStatus,
    triggerManualCollect,
  }
}
