<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAppStore } from '@/stores/app'
import { getRadarScores, getFactorExplanation, updateWeights } from '@/api/factor'
import { getCurrentRisk } from '@/api/risk'
import RadarChart from '@/components/charts/RadarChart.vue'
import FactorShapChart from '@/components/charts/FactorShapChart.vue'
import type { RadarScore, WeightConfig, FactorDetail } from '@/types/factor'

const { t } = useI18n()
const appStore = useAppStore()

const radarData = ref<RadarScore[]>([])
const shapFactors = ref<FactorDetail[]>([])
const loading = ref(false)
const weightsLoading = ref(false)
const error = ref<string | null>(null)
const latestDate = ref('')

const weights = ref<WeightConfig>({
  supplyDemand: 1.0,
  macro: 1.0,
  financial: 1.0,
  geopolitical: 1.0,
  sentiment: 1.0,
})

const themeMode = computed(() => appStore.theme)
const locale = computed(() => (appStore.locale === 'zh-CN' ? 'zh' : 'en') as 'zh' | 'en')

const weightSliders = computed(() => [
  { key: 'supplyDemand' as const, label: t('factorAnalysis.supplyDemand') },
  { key: 'macro' as const, label: t('factorAnalysis.macro') },
  { key: 'financial' as const, label: t('factorAnalysis.financial') },
  { key: 'geopolitical' as const, label: t('factorAnalysis.geopolitical') },
  { key: 'sentiment' as const, label: t('factorAnalysis.sentiment') },
])

let debounceTimer: ReturnType<typeof setTimeout> | null = null
let abortController: AbortController | null = null

async function fetchData() {
  loading.value = true
  error.value = null
  try {
    // Get latest date from risk/current, then use it for SHAP query
    const riskRes = await getCurrentRisk()
    latestDate.value = riskRes.data.data.date
    const [radarRes, shapRes] = await Promise.all([
      getRadarScores(),
      getFactorExplanation(latestDate.value),
    ])
    radarData.value = radarRes.data.data
    shapFactors.value = shapRes.data.data
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Unknown error'
  } finally {
    loading.value = false
  }
}

function onWeightChange() {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    submitWeights()
  }, 300)
}

async function submitWeights() {
  if (abortController) abortController.abort()
  abortController = new AbortController()
  weightsLoading.value = true

  const timer = setTimeout(() => {
    abortController?.abort()
  }, 5000)

  try {
    await updateWeights(weights.value, abortController.signal)
    // Refresh data after weight update
    const date = latestDate.value || new Date().toISOString().slice(0, 10)
    const [radarRes, shapRes] = await Promise.all([
      getRadarScores(),
      getFactorExplanation(date),
    ])
    radarData.value = radarRes.data.data
    shapFactors.value = shapRes.data.data
  } catch (e) {
    if (e instanceof DOMException && e.name === 'AbortError') {
      error.value = t('factorAnalysis.timeout')
    } else {
      error.value = e instanceof Error ? e.message : 'Unknown error'
    }
  } finally {
    clearTimeout(timer)
    weightsLoading.value = false
    abortController = null
  }
}

function resetWeights() {
  weights.value = {
    supplyDemand: 1.0,
    macro: 1.0,
    financial: 1.0,
    geopolitical: 1.0,
    sentiment: 1.0,
  }
  onWeightChange()
}

onMounted(fetchData)

onUnmounted(() => {
  if (debounceTimer) clearTimeout(debounceTimer)
  if (abortController) abortController.abort()
})
</script>

<template>
  <div class="factor-analysis">
    <!-- Loading -->
    <div v-if="loading" class="factor-analysis__loading">
      {{ t('common.loading') }}
    </div>

    <!-- Error toast -->
    <div v-if="error" class="factor-analysis__error">
      {{ error }}
      <button class="factor-analysis__error-close" @click="error = null">&times;</button>
    </div>

    <!-- Radar row -->
    <div class="factor-analysis__card factor-analysis__radar">
      <h3 class="factor-analysis__card-title">{{ t('factorAnalysis.radarTitle') }}</h3>
      <RadarChart :data="radarData" :theme="themeMode" />
    </div>

    <!-- Bottom row: SHAP + Weights -->
    <div class="factor-analysis__bottom">
      <div class="factor-analysis__card factor-analysis__shap">
        <h3 class="factor-analysis__card-title">SHAP</h3>
        <FactorShapChart :factors="shapFactors" :locale="locale" />
      </div>

      <div class="factor-analysis__card factor-analysis__weights">
        <h3 class="factor-analysis__card-title">{{ t('factorAnalysis.weightConfig') }}</h3>

        <div
          v-for="slider in weightSliders"
          :key="slider.key"
          class="factor-analysis__slider-group"
        >
          <label class="factor-analysis__slider-label">{{ slider.label }}</label>
          <input
            type="range"
            min="0"
            max="2"
            step="0.1"
            :value="weights[slider.key]"
            :disabled="weightsLoading"
            class="factor-analysis__slider"
            @input="(e) => { weights[slider.key] = parseFloat((e.target as HTMLInputElement).value); onWeightChange() }"
          />
          <span class="factor-analysis__slider-value">{{ weights[slider.key].toFixed(1) }}</span>
        </div>

        <button
          class="factor-analysis__reset-btn"
          :disabled="weightsLoading"
          @click="resetWeights"
        >
          {{ t('factorAnalysis.reset') }}
        </button>

        <div v-if="weightsLoading" class="factor-analysis__calculating">
          {{ t('factorAnalysis.calculating') }}
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.factor-analysis {
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.factor-analysis__loading {
  text-align: center;
  padding: 20px;
  color: var(--text-secondary);
  font-size: 14px;
}

.factor-analysis__error {
  background: rgba(248, 81, 73, 0.1);
  border: 1px solid var(--risk-high);
  color: var(--risk-high);
  padding: 10px 16px;
  border-radius: 6px;
  font-size: 13px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.factor-analysis__error-close {
  background: none;
  border: none;
  color: var(--risk-high);
  font-size: 18px;
  cursor: pointer;
  padding: 0 4px;
}

.factor-analysis__card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 16px;
  transition: background-color 0.3s, border-color 0.3s;
}

.factor-analysis__card-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 12px;
}

.factor-analysis__radar {
  min-height: 320px;
}

.factor-analysis__bottom {
  display: grid;
  grid-template-columns: 3fr 2fr;
  gap: 16px;
}

.factor-analysis__shap {
  min-height: 380px;
}

.factor-analysis__weights {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.factor-analysis__slider-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.factor-analysis__slider-label {
  flex: 0 0 60px;
  font-size: 13px;
  color: var(--text-primary);
}

.factor-analysis__slider {
  flex: 1;
  -webkit-appearance: none;
  appearance: none;
  height: 6px;
  background: var(--border-color);
  border-radius: 3px;
  outline: none;
  cursor: pointer;
}

.factor-analysis__slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--accent-primary, #8b5cf6);
  cursor: pointer;
}

.factor-analysis__slider:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.factor-analysis__slider-value {
  flex: 0 0 32px;
  text-align: right;
  font-size: 13px;
  font-family: monospace;
  color: var(--text-primary);
}

.factor-analysis__reset-btn {
  align-self: flex-start;
  padding: 6px 16px;
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.factor-analysis__reset-btn:hover {
  color: var(--text-primary);
  border-color: var(--accent-primary, #8b5cf6);
}

.factor-analysis__reset-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.factor-analysis__calculating {
  font-size: 12px;
  color: var(--text-secondary);
  font-style: italic;
}
</style>
