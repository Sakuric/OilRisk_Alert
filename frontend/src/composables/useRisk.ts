import { ref, onMounted } from 'vue'
import { getCurrentRisk } from '@/api/risk'
import { useRiskStore } from '@/stores/risk'
import type { CurrentRisk } from '@/types/risk'

export function useRisk() {
  const store = useRiskStore()
  const data = ref<CurrentRisk | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetch() {
    loading.value = true
    error.value = null
    store.setLoading(true)
    try {
      const res = await getCurrentRisk()
      data.value = res.data.data
      store.setCurrentRisk(res.data.data)
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Unknown error'
      error.value = msg
      store.setError(msg)
      store.markStale()
    } finally {
      loading.value = false
      store.setLoading(false)
    }
  }

  onMounted(fetch)

  return { data, loading, error, fetch }
}
