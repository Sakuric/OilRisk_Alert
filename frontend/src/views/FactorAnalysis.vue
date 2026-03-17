<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAppStore } from '@/stores/app'
import { getRadarScores, getFactorExplanation, updateWeights, getWeightHistory } from '@/api/factor'
import { getCurrentRisk } from '@/api/risk'
import RadarChart from '@/components/charts/RadarChart.vue'
import FactorShapChart from '@/components/charts/FactorShapChart.vue'
import WeightAreaChart from '@/components/charts/WeightAreaChart.vue'
import type { WeightDataPoint } from '@/components/charts/WeightAreaChart.vue'
import type { RadarScore, WeightConfig, FactorDetail } from '@/types/factor'
import type { RiskLevel } from '@/types/risk'
import { RISK_COLORS } from '@/types/risk'

const { t } = useI18n()
const appStore = useAppStore()

const radarData = ref<RadarScore[]>([])
const shapFactors = ref<FactorDetail[]>([])
const riskIndex = ref<number | null>(null)
const riskLevel = ref<RiskLevel | null>(null)
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
const riskColor = computed(() => riskLevel.value ? RISK_COLORS[riskLevel.value] : undefined)

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
    const riskPromise = getCurrentRisk()
    const radarPromise = getRadarScores()
    const shapPromise = riskPromise.then((res) => {
      latestDate.value = res.data.data.date
      riskIndex.value = res.data.data.riskIndex
      riskLevel.value = res.data.data.riskLevel
      return getFactorExplanation(res.data.data.date)
    })
    const [, radarRes, shapRes] = await Promise.all([riskPromise, radarPromise, shapPromise])
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
    const res = await updateWeights(weights.value, abortController.signal)
    const result = res.data.data
    riskIndex.value = result.riskIndex
    riskLevel.value = result.riskLevel
    radarData.value = result.radarScores
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

// 权重演变数据（从 API 获取真实数据）
const weightHistoryData = ref<WeightDataPoint[]>([])

async function fetchWeightHistory() {
  try {
    const res = await getWeightHistory(24)
    const data = res.data.data
    if (data && data.length > 0) {
      weightHistoryData.value = data
    }
  } catch (e) {
    // Weight history is non-critical, silent fail
  }
}

onMounted(() => {
  fetchData()
  fetchWeightHistory()
})

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

    <!-- Risk Index Card -->
    <div v-if="riskIndex !== null" class="factor-analysis__risk-card" :style="{ borderColor: riskColor }">
      <span class="factor-analysis__risk-label">{{ t('overview.gauge.riskIndex') }}</span>
      <span class="factor-analysis__risk-value" :style="{ color: riskColor }">{{ riskIndex.toFixed(1) }}</span>
      <span class="factor-analysis__risk-level" :style="{ color: riskColor }">{{ t('risk.level.' + riskLevel) }}</span>
      <span class="factor-analysis__model-badge">Stacking (LSTM + XGBoost + Ridge)</span>
    </div>

    <!-- Weight Evolution Chart -->
    <div class="factor-analysis__card factor-analysis__weight-history">
      <h3 class="factor-analysis__card-title">{{ t('factorAnalysis.weightHistory') }}</h3>
      <p class="factor-analysis__card-desc">{{ t('factorAnalysis.weightHistoryDesc') }}</p>
      <WeightAreaChart :data="weightHistoryData" />
    </div>

    <!-- Bottom row: SHAP + (Radar + Formula + Weights) -->
    <div class="factor-analysis__bottom">
      <div class="factor-analysis__card factor-analysis__shap">
        <h3 class="factor-analysis__card-title">SHAP {{ t('factorAnalysis.shapModelDesc') }}</h3>
        <FactorShapChart :factors="shapFactors" :locale="locale" />
      </div>

      <div class="factor-analysis__card factor-analysis__weights">
        <!-- Radar Chart -->
        <h3 class="factor-analysis__card-title">{{ t('factorAnalysis.radarTitle') }}</h3>
        <div class="factor-analysis__radar-inline">
          <RadarChart :data="radarData" :theme="themeMode" :locale="locale" />
        </div>

        <div class="factor-analysis__formula-divider"></div>

        <!-- Model Formula -->
        <div class="factor-analysis__formula">
          <h3 class="factor-analysis__card-title">{{ t('factorAnalysis.modelFormulaTitle') }}</h3>
          <div class="factor-analysis__formula-content">
            <div class="factor-analysis__formula-step">
              <span class="factor-analysis__formula-label">{{ t('factorAnalysis.formulaBase') }}</span>
              <code class="factor-analysis__formula-code">
                R<sub>base</sub> = Stacking( LSTM<sub>return</sub> , XGBoost<sub>risk</sub> , MarketState )
              </code>
            </div>
            <div class="factor-analysis__formula-step">
              <span class="factor-analysis__formula-label">{{ t('factorAnalysis.formulaWeighted') }}</span>
              <code class="factor-analysis__formula-code">
                ratio = <span class="factor-analysis__formula-frac">
                  <span class="factor-analysis__formula-num">
                    <template v-for="(slider, idx) in weightSliders" :key="slider.key">
                      <span
                        class="factor-analysis__formula-weight"
                        :class="{ 'factor-analysis__formula-weight--changed': weights[slider.key] !== 1.0 }"
                      >w<sub>{{ slider.label }}</sub></span>
                      <span v-if="idx < weightSliders.length - 1"> &middot; |SHAP<sub>{{ slider.label }}</sub>| + </span>
                      <span v-else> &middot; |SHAP<sub>{{ slider.label }}</sub>|</span>
                    </template>
                  </span>
                  <span class="factor-analysis__formula-denom">&Sigma; |SHAP<sub>i</sub>|</span>
                </span>
              </code>
            </div>
            <div class="factor-analysis__formula-step">
              <span class="factor-analysis__formula-label">{{ t('factorAnalysis.formulaFinal') }}</span>
              <code class="factor-analysis__formula-code">
                R<sub>final</sub> = R<sub>base</sub> &times; ratio
              </code>
            </div>
            <div class="factor-analysis__formula-weights">
              <span
                v-for="slider in weightSliders"
                :key="slider.key"
                class="factor-analysis__formula-tag"
                :class="{ 'factor-analysis__formula-tag--changed': weights[slider.key] !== 1.0 }"
              >
                w<sub>{{ slider.label }}</sub> = {{ weights[slider.key].toFixed(1) }}
              </span>
            </div>
            <p class="factor-analysis__formula-desc">{{ t('factorAnalysis.formulaDesc') }}</p>
          </div>
        </div>

        <div class="factor-analysis__formula-divider"></div>

        <!-- Weight Configuration -->
        <h3 class="factor-analysis__card-title">{{ t('factorAnalysis.weightConfig') }}</h3>
        <p class="factor-analysis__card-desc">{{ t('factorAnalysis.weightConfigDesc') }}</p>

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

.factor-analysis__risk-card {
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-left-width: 3px;
  border-radius: 8px;
  padding: 12px 16px;
  transition: background-color 0.3s, border-color 0.3s;
}

.factor-analysis__risk-label {
  font-size: 13px;
  color: var(--text-secondary);
}

.factor-analysis__risk-value {
  font-size: 24px;
  font-weight: 700;
  font-family: monospace;
}

.factor-analysis__risk-level {
  font-size: 13px;
  font-weight: 600;
}

.factor-analysis__model-badge {
  margin-left: auto;
  padding: 3px 10px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  background: rgba(139, 92, 246, 0.08);
  border: 1px solid rgba(139, 92, 246, 0.2);
  font-family: monospace;
}

.factor-analysis__card-desc {
  font-size: 12px;
  color: var(--text-muted);
  margin: -8px 0 10px;
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

.factor-analysis__radar-inline {
  height: 280px;
}

.factor-analysis__weight-history {
  min-height: 380px;
}

.factor-analysis__bottom {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  align-items: start;
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

@media (max-width: 768px) {
  .factor-analysis__bottom {
    grid-template-columns: 1fr;
  }
}

/* Formula display (inside weights panel) */
.factor-analysis__formula {
  border-left: 3px solid var(--accent-primary, #8b5cf6);
  padding-left: 12px;
}

.factor-analysis__formula-divider {
  border-top: 1px solid var(--border-color);
  margin: 4px 0;
}

.factor-analysis__formula-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.factor-analysis__formula-step {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.factor-analysis__formula-label {
  flex: 0 0 auto;
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 600;
  white-space: nowrap;
}

.factor-analysis__formula-code {
  font-family: 'Cambria Math', 'Latin Modern Math', Georgia, serif;
  font-size: 14px;
  color: var(--text-primary);
  background: rgba(139, 92, 246, 0.04);
  padding: 6px 12px;
  border-radius: 4px;
  border: 1px solid var(--border-color);
  overflow-x: auto;
}

.factor-analysis__formula-frac {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  vertical-align: middle;
  margin: 0 4px;
}

.factor-analysis__formula-num {
  border-bottom: 1px solid var(--text-primary);
  padding-bottom: 2px;
  font-size: 12px;
  white-space: nowrap;
}

.factor-analysis__formula-denom {
  padding-top: 2px;
  font-size: 12px;
}

.factor-analysis__formula-weight {
  transition: all 0.3s;
}

.factor-analysis__formula-weight--changed {
  color: var(--accent-primary, #8b5cf6);
  font-weight: 700;
  text-shadow: 0 0 8px rgba(139, 92, 246, 0.4);
}

.factor-analysis__formula-weights {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 4px;
}

.factor-analysis__formula-tag {
  font-family: monospace;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
  background: var(--hover-bg, rgba(0,0,0,0.04));
  color: var(--text-secondary);
  border: 1px solid transparent;
  transition: all 0.3s;
}

.factor-analysis__formula-tag--changed {
  color: var(--accent-primary, #8b5cf6);
  border-color: var(--accent-primary, #8b5cf6);
  background: rgba(139, 92, 246, 0.08);
  font-weight: 600;
}

.factor-analysis__formula-desc {
  font-size: 12px;
  color: var(--text-muted);
  margin: 0;
  line-height: 1.5;
}
</style>
