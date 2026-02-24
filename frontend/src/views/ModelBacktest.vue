<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useTheme } from '@/composables/useTheme'
import { runBacktest } from '@/api/backtest'
import * as echarts from 'echarts'
import type { BacktestParams, BacktestResult } from '@/types/backtest'

const { t } = useI18n()
const { isDark } = useTheme()

type ModelName = 'XGBoost' | 'ARIMA' | 'LSTM'

const models: ModelName[] = ['XGBoost', 'ARIMA', 'LSTM']
const modelColors: Record<ModelName, string> = {
  XGBoost: '#d29922',
  ARIMA: '#3fb950',
  LSTM: '#da3633',
}

const today = new Date().toISOString().slice(0, 10)
const oneYearAgo = (() => {
  const d = new Date()
  d.setFullYear(d.getFullYear() - 1)
  return d.toISOString().slice(0, 10)
})()

const startDate = ref(oneYearAgo)
const endDate = ref(today)
const selectedModel = ref<ModelName>('XGBoost')
const loading = ref(false)
const error = ref<string | null>(null)

// Overlay results
const overlayResults = ref<{ model: ModelName; result: BacktestResult }[]>([])
const latestResult = computed(() =>
  overlayResults.value.length > 0
    ? overlayResults.value[overlayResults.value.length - 1].result
    : null,
)

const isLargePeriod = computed(() => {
  const start = new Date(startDate.value)
  const end = new Date(endDate.value)
  const diffYears = (end.getTime() - start.getTime()) / (365.25 * 24 * 3600 * 1000)
  return diffYears > 3
})

const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

async function executeBacktest() {
  error.value = null
  loading.value = true
  try {
    const params: BacktestParams = {
      startDate: startDate.value,
      endDate: endDate.value,
      model: selectedModel.value,
    }
    const res = await runBacktest(params)
    // Remove previous result for same model
    overlayResults.value = overlayResults.value.filter(
      (o) => o.model !== selectedModel.value,
    )
    overlayResults.value.push({ model: selectedModel.value, result: res.data.data })
    updateChart()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Unknown error'
  } finally {
    loading.value = false
  }
}

function clearOverlay() {
  overlayResults.value = []
  if (chart) chart.clear()
}

function getChartOption(): echarts.EChartsOption {
  if (overlayResults.value.length === 0) return {}

  const firstResult = overlayResults.value[0].result
  const series: echarts.SeriesOption[] = []

  // Actual line (from first result, they share the same actual data)
  series.push({
    name: t('backtest.actual'),
    type: 'line',
    data: firstResult.actual,
    smooth: true,
    symbol: 'none',
    lineStyle: { width: 2, color: '#58a6ff' },
    itemStyle: { color: '#58a6ff' },
  })

  // Predicted lines per model
  for (const overlay of overlayResults.value) {
    const color = modelColors[overlay.model]
    series.push({
      name: `${t('backtest.predicted')} (${overlay.model})`,
      type: 'line',
      data: overlay.result.predicted,
      smooth: true,
      symbol: 'none',
      lineStyle: { width: 2, color, type: 'dashed' },
      itemStyle: { color },
    })
  }

  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: isDark.value ? 'rgba(8, 11, 26, 0.9)' : 'rgba(255, 255, 255, 0.95)',
      borderColor: isDark.value ? 'rgba(139, 92, 246, 0.2)' : 'rgba(0, 0, 0, 0.1)',
      textStyle: { color: isDark.value ? '#f1f1f8' : '#1a1a2e' },
    },
    legend: {
      textStyle: { color: isDark.value ? '#b0b3d0' : '#4a4d6a' },
      top: 0,
    },
    grid: {
      left: 60,
      right: 30,
      top: 40,
      bottom: 40,
    },
    xAxis: {
      type: 'category',
      data: firstResult.dates,
      boundaryGap: false,
      axisLine: { lineStyle: { color: isDark.value ? 'rgba(139, 92, 246, 0.15)' : '#e2e4ef' } },
      axisLabel: { color: isDark.value ? '#b0b3d0' : '#4a4d6a' },
    },
    yAxis: {
      type: 'value',
      axisLine: { lineStyle: { color: isDark.value ? 'rgba(139, 92, 246, 0.15)' : '#e2e4ef' } },
      axisLabel: { color: isDark.value ? '#b0b3d0' : '#4a4d6a' },
      splitLine: { lineStyle: { color: isDark.value ? 'rgba(139, 92, 246, 0.08)' : '#eff0f7' } },
    },
    series,
    animationDuration: 600,
  }
}

function updateChart() {
  // Handle DOM element change from v-if/v-else switch
  if (chart && chart.getDom() !== chartRef.value) {
    chart.dispose()
    chart = null
  }
  if (!chart && chartRef.value) {
    chart = echarts.init(chartRef.value)
  }
  if (chart) {
    chart.setOption(getChartOption(), { notMerge: true })
  }
}

function handleResize() {
  chart?.resize()
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
})
</script>

<template>
  <div class="backtest">
    <!-- Control card -->
    <div class="backtest__card backtest__controls">
      <div class="backtest__control-row">
        <div class="backtest__field">
          <label class="backtest__label">{{ t('backtest.startDate') }}</label>
          <input v-model="startDate" type="date" class="backtest__date-input" />
        </div>
        <div class="backtest__field">
          <label class="backtest__label">{{ t('backtest.endDate') }}</label>
          <input v-model="endDate" type="date" class="backtest__date-input" />
        </div>
      </div>

      <div class="backtest__model-tabs">
        <label class="backtest__label">{{ t('backtest.model') }}</label>
        <div class="backtest__tabs">
          <button
            v-for="m in models"
            :key="m"
            :class="['backtest__tab', { active: selectedModel === m }]"
            @click="selectedModel = m"
          >
            {{ m }}
          </button>
        </div>
      </div>

      <div class="backtest__actions">
        <button
          class="backtest__run-btn"
          :disabled="loading"
          @click="executeBacktest"
        >
          {{ loading ? t('common.loading') : t('backtest.run') }}
        </button>
        <span v-if="isLargePeriod" class="backtest__warning">
          {{ t('backtest.largePeriodWarning') }}
        </span>
      </div>
    </div>

    <!-- Error -->
    <div v-if="error" class="backtest__error">
      {{ error }}
    </div>

    <!-- Results -->
    <template v-if="overlayResults.length > 0">
      <!-- Chart -->
      <div class="backtest__card backtest__chart-card">
        <div class="backtest__chart-header">
          <h3 class="backtest__card-title">{{ t('backtest.predicted') }}</h3>
          <button class="backtest__clear-btn" @click="clearOverlay">
            {{ t('backtest.clearOverlay') }}
          </button>
        </div>
        <div ref="chartRef" class="backtest__chart"></div>
      </div>

      <!-- Stats -->
      <div v-if="latestResult" class="backtest__stats">
        <div class="backtest__stat-card">
          <span class="backtest__stat-label">{{ t('backtest.hitRate') }}</span>
          <span class="backtest__stat-value">{{ (latestResult.hitRate * 100).toFixed(1) }}%</span>
        </div>
        <div class="backtest__stat-card">
          <span class="backtest__stat-label">{{ t('backtest.falseAlarmRate') }}</span>
          <span class="backtest__stat-value">{{ (latestResult.falseAlarmRate * 100).toFixed(1) }}%</span>
        </div>
        <div class="backtest__stat-card">
          <span class="backtest__stat-label">{{ t('backtest.mae') }}</span>
          <span class="backtest__stat-value">{{ latestResult.mae.toFixed(2) }}</span>
        </div>
        <div class="backtest__stat-card">
          <span class="backtest__stat-label">{{ t('backtest.directionAccuracy') }}</span>
          <span class="backtest__stat-value">{{ (latestResult.directionAccuracy * 100).toFixed(1) }}%</span>
        </div>
      </div>
    </template>

    <!-- Empty state when no results yet -->
    <div v-else class="backtest__card backtest__empty">
      <div ref="chartRef" style="display:none"></div>
      <p class="backtest__empty-text">{{ t('common.noData') }}</p>
    </div>
  </div>
</template>

<style scoped>
.backtest {
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.backtest__card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 16px;
  transition: background-color 0.3s, border-color 0.3s;
}

.backtest__card-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
}

.backtest__controls {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.backtest__control-row {
  display: flex;
  gap: 16px;
}

.backtest__field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.backtest__label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
}

.backtest__date-input {
  padding: 6px 10px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-card);
  color: var(--text-primary);
  font-size: 13px;
}

.backtest__model-tabs {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.backtest__tabs {
  display: flex;
  gap: 4px;
}

.backtest__tab {
  padding: 5px 16px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.backtest__tab.active {
  border-color: var(--accent-primary, #8b5cf6);
  color: var(--text-primary);
  background: rgba(88, 166, 255, 0.1);
}

.backtest__actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.backtest__run-btn {
  padding: 8px 24px;
  border: 1px solid var(--accent-primary, #8b5cf6);
  border-radius: 6px;
  background: rgba(88, 166, 255, 0.1);
  color: var(--accent-primary, #8b5cf6);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.backtest__run-btn:hover {
  background: rgba(88, 166, 255, 0.2);
}

.backtest__run-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.backtest__warning {
  font-size: 12px;
  color: #d29922;
}

.backtest__error {
  background: rgba(248, 81, 73, 0.1);
  border: 1px solid var(--risk-high);
  color: var(--risk-high);
  padding: 10px 16px;
  border-radius: 6px;
  font-size: 13px;
}

.backtest__chart-card {
  min-height: 400px;
}

.backtest__chart-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.backtest__clear-btn {
  padding: 4px 12px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: transparent;
  color: var(--text-secondary);
  font-size: 12px;
  cursor: pointer;
}

.backtest__clear-btn:hover {
  border-color: var(--risk-high);
  color: var(--risk-high);
}

.backtest__chart {
  width: 100%;
  height: 360px;
}

.backtest__stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.backtest__stat-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.backtest__stat-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.backtest__stat-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
}

.backtest__empty {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
}

.backtest__empty-text {
  color: var(--text-secondary);
  font-size: 14px;
}
</style>
