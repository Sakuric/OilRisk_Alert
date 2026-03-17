<script setup lang="ts">
import { computed, ref, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRisk } from '@/composables/useRisk'
import { useTimeseries } from '@/composables/useTimeseries'
import { useAlerts } from '@/composables/useAlerts'
import { useDataFreshness } from '@/composables/useDataFreshness'
import { useRiskStore } from '@/stores/risk'
import { useTheme } from '@/composables/useTheme'
import { useAppStore } from '@/stores/app'
import { getAlerts } from '@/api/alert'
import { getRadarScores } from '@/api/factor'
import { getModelSignals } from '@/api/risk'
import RiskGauge from '@/components/charts/RiskGauge.vue'
import PriceRiskAlertChart from '@/components/charts/PriceRiskAlertChart.vue'
import FactorBarChart from '@/components/charts/FactorBarChart.vue'
import RadarChart from '@/components/charts/RadarChart.vue'
import AlertCard from '@/components/common/AlertCard.vue'
import type { RadarScore } from '@/types/factor'
import type { ModelSignal, TimeseriesPoint } from '@/types/risk'

const { t } = useI18n()
const riskStore = useRiskStore()
const { isDark } = useTheme()
const appStore = useAppStore()
const locale = computed(() => (appStore.locale === 'zh-CN' ? 'zh' : 'en') as 'zh' | 'en')
const { data: riskData } = useRisk()
const { data: tsData } = useTimeseries()
const { data: alertsData } = useAlerts({ page: 1, size: 3 })
const {
  freshnessLevel,
  dataDate: statusDataDate,
  updatedTime,
  collecting,
  collectResult,
  collectError,
  triggerManualCollect,
} = useDataFreshness()

const llmExpanded = ref(true)
const aiSummaryText = ref('')
const displayedAiSummary = ref('')
const radarScores = ref<RadarScore[]>([])
const modelSignal = ref<ModelSignal | null>(null)
const aiGenerating = ref(false)
const aiError = ref('')
let typewriterTimer: any = null
let currentEventSource: EventSource | null = null

const riskIndex = computed(() => riskData.value?.riskIndex ?? 0)
const riskLevel = computed(() => riskData.value?.riskLevel ?? 'Low')
const topFactors = computed(() => riskData.value?.topFactors ?? [])

const dates = computed(() => tsData.value?.dates ?? [])
const oilPrice = computed(() => tsData.value?.oilPrice ?? [])
const tsRiskIndex = computed(() => tsData.value?.riskIndex ?? [])
const tsAlerts = computed(() => tsData.value?.alerts ?? [])

function startTypewriter(text: string) {
  displayedAiSummary.value = ''
  let i = 0
  clearInterval(typewriterTimer)
  if (!text) return
  typewriterTimer = setInterval(() => {
    if (i < text.length) {
      displayedAiSummary.value += text.charAt(i)
      i++
    } else {
      clearInterval(typewriterTimer)
    }
  }, 15)
}

async function fetchData() {
  try {
    const [alertRes, radarRes, signalRes] = await Promise.all([
      getAlerts({ page: 1, size: 1 }),
      getRadarScores(),
      getModelSignals().catch(() => null),
    ])

    const records = alertRes.data.data.records
    if (records.length > 0 && records[0].aiReport) {
      aiSummaryText.value = records[0].aiReport
      startTypewriter(aiSummaryText.value)
    }

    radarScores.value = radarRes.data.data

    if (signalRes?.data?.data) {
      modelSignal.value = signalRes.data.data
    }
  } catch {
    // silent fail
  }
}

onMounted(fetchData)

function generateAiSummary() {
  if (aiGenerating.value) return
  aiGenerating.value = true
  aiError.value = ''
  displayedAiSummary.value = ''
  clearInterval(typewriterTimer)

  if (currentEventSource) {
    currentEventSource.close()
    currentEventSource = null
  }

  const es = new EventSource('/api/risk/ai-summary')
  currentEventSource = es

  es.onmessage = (e) => {
    if (e.data === '[DONE]') {
      aiGenerating.value = false
      aiSummaryText.value = displayedAiSummary.value
      es.close()
      currentEventSource = null
      return
    }
    try {
      const { token } = JSON.parse(e.data)
      displayedAiSummary.value += token
    } catch {
      // ignore malformed frames
    }
  }

  es.onerror = () => {
    aiGenerating.value = false
    aiError.value = t('overview.aiSummaryError')
    es.close()
    currentEventSource = null
  }
}

const selectedAlert = ref<TimeseriesPoint | null>(null)

function onAlertSelect(alert: TimeseriesPoint) {
  selectedAlert.value = alert
}

watch(aiSummaryText, (newVal) => {
  if (llmExpanded.value && !aiGenerating.value) startTypewriter(newVal)
})
</script>

<template>
  <div class="overview">
    <div v-if="riskStore.stale" class="overview__stale-banner">
      {{ t('overview.staleWarning') }}
    </div>

    <!-- Data Freshness Status Bar -->
    <div class="overview__status-bar glass-card">
      <div class="overview__status-info">
        <span
          class="overview__status-dot"
          :class="`overview__status-dot--${freshnessLevel}`"
        ></span>
        <span class="overview__status-label">
          {{ t('overview.dataStatus.label') }}:
          <strong>{{ t('overview.dataStatus.' + freshnessLevel) }}</strong>
        </span>
        <span v-if="statusDataDate" class="overview__status-sep">|</span>
        <span v-if="statusDataDate" class="overview__status-item">
          {{ t('overview.dataStatus.dataDate') }}: {{ statusDataDate }}
        </span>
        <span v-if="updatedTime" class="overview__status-sep">|</span>
        <span v-if="updatedTime" class="overview__status-item">
          {{ t('overview.dataStatus.updatedAt') }}: {{ updatedTime }}
        </span>
      </div>
      <div class="overview__status-actions">
        <span v-if="collectResult" class="overview__status-result overview__status-result--ok">
          {{ collectResult.collection ? `${t('overview.dataStatus.collected')} ${collectResult.collection.success}/${collectResult.collection.total} ${t('overview.dataStatus.factors')}` : collectResult.message || collectResult.status }}
        </span>
        <span v-if="collectError" class="overview__status-result overview__status-result--err">
          {{ t('overview.dataStatus.refreshFailed') }}
        </span>
        <button
          class="overview__refresh-btn"
          :disabled="collecting"
          @click="triggerManualCollect"
        >
          {{ collecting ? t('overview.dataStatus.refreshing') : t('overview.dataStatus.manualRefresh') }}
        </button>
      </div>
    </div>

    <div class="overview__grid">
      <!-- Left Column -->
      <div class="overview__col-left">
        <div class="overview__card glass-card">
          <div class="overview__card-header">
            <h3 class="overview__card-title">{{ t('overview.gauge.title') }}</h3>
            <span class="status-dot" :class="`status-dot--${riskLevel.toLowerCase()}`"></span>
          </div>
          <div class="chart-container">
            <RiskGauge :risk-index="riskIndex" :risk-level="riskLevel" />
          </div>
        </div>

        <div class="overview__card glass-card">
          <h3 class="overview__card-title">{{ t('factorAnalysis.radarTitle') }}</h3>
          <div class="chart-container">
            <RadarChart :data="radarScores" :theme="isDark ? 'dark' : 'light'" :locale="locale" />
          </div>
        </div>

        <!-- Model Signals Panel -->
        <div v-if="modelSignal" class="overview__card glass-card overview__signals">
          <h3 class="overview__card-title">{{ t('overview.modelSignals.title') }}</h3>
          <div class="overview__signal-grid">
            <div class="overview__signal-item">
              <span class="overview__signal-label">LSTM</span>
              <span class="overview__signal-value">${{ modelSignal.lstmPredPrice.toFixed(2) }}</span>
              <span class="overview__signal-direction" :class="modelSignal.lstmDirection === 'Up' ? 'signal--up' : 'signal--down'">
                {{ t('overview.modelSignals.direction.' + modelSignal.lstmDirection) }}
              </span>
              <span class="overview__signal-sub">{{ t('overview.modelSignals.upProb') }}: {{ (modelSignal.lstmUpProb * 100).toFixed(1) }}%</span>
            </div>
            <div class="overview__signal-item">
              <span class="overview__signal-label">XGBoost</span>
              <span class="overview__signal-value">{{ (modelSignal.xgbRiskScore * 100).toFixed(1) }}%</span>
              <span class="overview__signal-sub">{{ t('overview.modelSignals.impactProb') }}</span>
            </div>
            <div class="overview__signal-item">
              <span class="overview__signal-label">Stacking</span>
              <span class="overview__signal-value" :class="modelSignal.stackingReturnPct >= 0 ? 'signal--up' : 'signal--down'">
                {{ modelSignal.stackingReturnPct >= 0 ? '+' : '' }}{{ modelSignal.stackingReturnPct.toFixed(2) }}%
              </span>
              <span class="overview__signal-zone">{{ t('risk.level.' + modelSignal.stackingRiskZone) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Right Column -->
      <div class="overview__col-right">
        <div class="overview__card glass-card">
          <h3 class="overview__card-title">{{ t('overview.priceChart.title') }}</h3>
          <div class="chart-container-large">
            <PriceRiskAlertChart
              :dates="dates"
              :oil-price="oilPrice"
              :risk-index="tsRiskIndex"
              :alerts="tsAlerts"
              @select-alert="onAlertSelect"
            />
          </div>
        </div>

        <div class="overview__bottom-row">
          <div class="overview__card glass-card">
            <h3 class="overview__card-title">{{ t('overview.factorChart.title') }}</h3>
            <div class="chart-container">
              <FactorBarChart :factors="topFactors" />
            </div>
          </div>

          <div class="overview__card glass-card">
            <h3 class="overview__card-title">{{ t('overview.alerts.title') }}</h3>
            <div class="overview__alerts-list">
              <template v-if="alertsData.length > 0">
                <AlertCard
                  v-for="alert in alertsData"
                  :key="alert.id"
                  :alert="alert"
                />
              </template>
              <p v-else class="overview__no-data">{{ t('overview.alerts.noData') }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- AI Summary -->
      <div class="overview__card glass-card overview__card--llm">
        <div class="overview__llm-header" @click="llmExpanded = !llmExpanded">
          <div class="overview__llm-title-group">
            <span class="ai-icon">&#10024;</span>
            <h3 class="overview__card-title">{{ t('overview.aiSummary') }}</h3>
            <button
              class="overview__ai-gen-btn"
              :disabled="aiGenerating"
              @click.stop="generateAiSummary"
            >
              {{ aiGenerating ? t('overview.generatingAiSummary') : t('overview.generateAiSummary') }}
            </button>
          </div>
          <button class="overview__llm-toggle">
            <span>{{ llmExpanded ? '\u2212' : '+' }}</span>
          </button>
        </div>
        <div v-show="llmExpanded" class="overview__llm-body">
          <div class="typewriter-container">
            <p v-if="aiError" class="overview__llm-error">{{ aiError }}</p>
            <p v-if="displayedAiSummary" class="overview__llm-text">{{ displayedAiSummary }}<span v-if="aiGenerating" class="cursor">|</span></p>
            <p v-else-if="aiSummaryText" class="overview__llm-text">{{ aiSummaryText }}</p>
            <p v-else class="overview__llm-placeholder">{{ t('overview.noAISummary') }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.overview {
  max-width: 1600px;
  margin: 0 auto;
  padding: 10px;
}

.overview__stale-banner {
  background: linear-gradient(90deg, transparent, var(--risk-medium), transparent);
  color: #fff;
  text-align: center;
  padding: 6px;
  margin-bottom: 20px;
  font-size: 13px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1px;
  border-radius: 6px;
}

.overview__grid {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 16px;
}

.overview__col-left {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.overview__col-right {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 0;
}

.overview__col-right > :first-child {
  flex: 1;
  min-height: 0;
}

.overview__bottom-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

/* Glass card */
.glass-card {
  background: var(--bg-card);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
  border: 1px solid var(--bg-card-border);
  border-radius: 16px;
  box-shadow: var(--glass-shadow);
  position: relative;
  overflow: hidden;
}

.glass-card::before {
  content: "";
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  border-radius: inherit;
  padding: 1px;
  background: var(--glass-border);
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  pointer-events: none;
}

.overview__card {
  padding: 16px;
}

.overview__card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.overview__card-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.chart-container {
  height: 240px;
}

.chart-container-large {
  height: 100%;
  min-height: 350px;
}

/* Status dot */
.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  box-shadow: 0 0 8px currentColor;
}
.status-dot--low { color: var(--risk-low); background: var(--risk-low); }
.status-dot--medium { color: var(--risk-medium); background: var(--risk-medium); }
.status-dot--high { color: var(--risk-high); background: var(--risk-high); }

/* Alerts */
.overview__alerts-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 240px;
  overflow-y: auto;
}

.overview__no-data {
  color: var(--text-muted);
  font-size: 13px;
  text-align: center;
  padding: 20px;
}

/* AI Summary */
.overview__card--llm {
  grid-column: 1 / -1;
  border-left: 4px solid var(--accent-primary);
}

.overview__llm-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
}

.overview__llm-title-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.ai-icon { font-size: 18px; }

.overview__llm-toggle {
  background: var(--hover-bg);
  border: none;
  color: var(--text-secondary);
  width: 24px;
  height: 24px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 16px;
}

.overview__llm-body {
  margin-top: 15px;
  padding-top: 15px;
  border-top: 1px solid var(--border-color);
}

.typewriter-container { min-height: 60px; }

.overview__llm-text {
  color: var(--text-primary);
  font-size: 14px;
  line-height: 1.7;
  white-space: pre-wrap;
}

.overview__llm-placeholder {
  color: var(--text-muted);
  font-size: 13px;
  font-style: italic;
}

.overview__ai-gen-btn {
  padding: 3px 10px;
  border: 1px solid var(--accent-primary);
  border-radius: 4px;
  background: transparent;
  color: var(--accent-primary);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.overview__ai-gen-btn:hover:not(:disabled) {
  background: var(--accent-primary);
  color: #fff;
}

.overview__ai-gen-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.overview__llm-error {
  color: var(--risk-high);
  font-size: 13px;
  margin: 0 0 8px;
}

.cursor {
  display: inline-block;
  width: 2px;
  background-color: var(--accent-primary);
  margin-left: 4px;
  animation: blink 1s step-end infinite;
}

@keyframes blink {
  from, to { opacity: 1; }
  50% { opacity: 0; }
}

/* Data Status Bar */
.overview__status-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  margin-bottom: 16px;
  border-radius: 12px;
}

.overview__status-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-secondary);
  flex-wrap: wrap;
}

.overview__status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.overview__status-dot--realtime {
  background: var(--risk-low);
  box-shadow: 0 0 6px var(--risk-low);
}

.overview__status-dot--stale {
  background: var(--risk-medium);
  box-shadow: 0 0 6px var(--risk-medium);
}

.overview__status-dot--error {
  background: var(--risk-high);
  box-shadow: 0 0 6px var(--risk-high);
}

.overview__status-label {
  color: var(--text-primary);
  font-size: 13px;
}

.overview__status-sep {
  color: var(--text-muted);
  font-size: 12px;
}

.overview__status-item {
  font-size: 13px;
}

.overview__status-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.overview__status-result {
  font-size: 12px;
  font-weight: 600;
}

.overview__status-result--ok {
  color: var(--risk-low);
}

.overview__status-result--err {
  color: var(--risk-high);
}

.overview__refresh-btn {
  padding: 4px 14px;
  border: 1px solid var(--accent-primary);
  border-radius: 6px;
  background: transparent;
  color: var(--accent-primary);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.overview__refresh-btn:hover:not(:disabled) {
  background: var(--accent-primary);
  color: #fff;
}

.overview__refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@media (max-width: 1200px) {
  .overview__grid { grid-template-columns: 1fr; }
  .overview__bottom-row { grid-template-columns: 1fr; }
  .overview__status-bar { flex-direction: column; gap: 10px; }
  .chart-container-large { min-height: 300px; }
}

/* Model Signals */
.overview__signals {
  border-left: 3px solid var(--accent-primary);
}

.overview__signal-grid {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.overview__signal-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 12px;
  border-radius: 8px;
  background: rgba(139, 92, 246, 0.04);
  border: 1px solid var(--border-color);
}

.overview__signal-label {
  font-size: 11px;
  font-weight: 700;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.overview__signal-value {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
}

.overview__signal-direction {
  font-size: 13px;
  font-weight: 600;
}

.overview__signal-sub {
  font-size: 12px;
  color: var(--text-secondary);
}

.overview__signal-zone {
  font-size: 13px;
  font-weight: 600;
}

.signal--up {
  color: var(--risk-low);
}

.signal--down {
  color: var(--risk-high);
}
</style>
