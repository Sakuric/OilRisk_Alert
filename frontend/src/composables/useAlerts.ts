import { ref, onMounted } from 'vue'
import { getAlerts } from '@/api/alert'
import type { AlertRecord } from '@/types/alert'
import type { AlertParams } from '@/api/alert'

export function useAlerts(params?: AlertParams) {
  const data = ref<AlertRecord[]>([])
  const total = ref(0)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetch(overrideParams?: AlertParams) {
    loading.value = true
    error.value = null
    try {
      const res = await getAlerts(overrideParams ?? params)
      data.value = res.data.data.records
      total.value = res.data.data.total
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Unknown error'
    } finally {
      loading.value = false
    }
  }

  onMounted(fetch)

  return { data, total, loading, error, fetch }
}
