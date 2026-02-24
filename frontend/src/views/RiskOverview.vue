<script setup lang="ts">
import { computed, ref, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRisk } from '@/composables/useRisk'
import { useTimeseries } from '@/composables/useTimeseries'
import { useAlerts } from '@/composables/useAlerts'
import { useRiskStore } from '@/stores/risk'
import { useTheme } from '@/composables/useTheme'
import { getAlerts } from '@/api/alert'
import { getRadarScores } from '@/api/factor'
import RiskGauge from '@/components/charts/RiskGauge.vue'
import PriceRiskChart from '@/components/charts/PriceRiskChart.vue'
import FactorBarChart from '@/components/charts/FactorBarChart.vue'
import RadarChart from '@/components/charts/RadarChart.vue'
import AlertCard from '@/components/common/AlertCard.vue'
import type { RadarScore } from '@/types/factor'

const { t } = useI18n()
const riskStore = useRiskStore()
const { isDark } = useTheme()
const { data: riskData, loading: riskLoading, error: riskError } = useRisk()
const { data: tsData, loading: tsLoading } = useTimeseries()
const { data: alertsData, loading: alertsLoading } = useAlerts({ page: 1, size: 3 })

const llmExpanded = ref(true)
const aiSummaryText = ref('')
const displayedAiSummary = ref('')
const radarScores = ref<RadarScore[]>([])
let typewriterTimer: any = null

const riskIndex = computed(() => riskData.value?.riskIndex ?? 0)
const riskLevel = computed(() => riskData.value?.riskLevel ?? 'Low')
const topFactors = computed(() => riskData.value?.topFactors ?? [])

const dates = computed(() => tsData.value?.dates ?? [])
const oilPrice = computed(() => tsData.value?.oilPrice ?? [])
const tsRiskIndex = computed(() => tsData.value?.riskIndex ?? [])
const tsAlerts = computed(() => tsData.value?.alerts ?? [])

const isLoading = computed(() => riskLoading.value || tsLoading.value || alertsLoading.value)

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
    const [alertRes, radarRes] = await Promise.all([
      getAlerts({ page: 1, size: 1 }),
      getRadarScores()
    ])

    const records = alertRes.data.data.records
    if (records.length > 0 && records[0].aiReport) {
      aiSummaryText.value = records[0].aiReport
      startTypewriter(aiSummaryText.value)
    }

    radarScores.value = radarRes.data.data
  } catch {
    // silent fail
  }
}

onMounted(fetchData)

watch(aiSummaryText, (newVal) => {
  if (llmExpanded.value) startTypewriter(newVal)
})
</script>

<template>
  <div class="overview">
    <div v-if="riskStore.stale" class="overview__stale-banner">
      {{ t('overview.staleWarning') }}
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
            <RadarChart :data="radarScores" :theme="isDark ? 'dark' : 'light'" />
          </div>
        </div>
      </div>

      <!-- Right Column -->
      <div class="overview__col-right">
        <div class="overview__card glass-card">
          <h3 class="overview__card-title">{{ t('overview.priceChart.title') }}</h3>
          <div class="chart-container-large">
            <PriceRiskChart
              :dates="dates"
              :oil-price="oilPrice"
              :risk-index="tsRiskIndex"
              :alerts="tsAlerts"
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
          </div>
          <button class="overview__llm-toggle">
            <span>{{ llmExpanded ? '\u2212' : '+' }}</span>
          </button>
        </div>
        <div v-show="llmExpanded" class="overview__llm-body">
          <div class="typewriter-container">
            <p v-if="displayedAiSummary" class="overview__llm-text">{{ displayedAiSummary }}<span class="cursor">|</span></p>
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
  grid-template-columns: 350px 1fr;
  gap: 20px;
}

.overview__col-left {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.overview__col-right {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.overview__bottom-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
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
  padding: 20px;
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
  height: 280px;
}

.chart-container-large {
  height: 400px;
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
  max-height: 280px;
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

@media (max-width: 1200px) {
  .overview__grid { grid-template-columns: 1fr; }
  .overview__bottom-row { grid-template-columns: 1fr; }
}
</style>
