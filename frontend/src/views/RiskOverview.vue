<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRisk } from '@/composables/useRisk'
import { useTimeseries } from '@/composables/useTimeseries'
import { useAlerts } from '@/composables/useAlerts'
import { useRiskStore } from '@/stores/risk'
import { getAlerts } from '@/api/alert'
import RiskGauge from '@/components/charts/RiskGauge.vue'
import PriceRiskChart from '@/components/charts/PriceRiskChart.vue'
import FactorBarChart from '@/components/charts/FactorBarChart.vue'
import AlertCard from '@/components/common/AlertCard.vue'

const { t } = useI18n()
const riskStore = useRiskStore()
const { data: riskData, loading: riskLoading, error: riskError } = useRisk()
const { data: tsData, loading: tsLoading } = useTimeseries()
const { data: alertsData, loading: alertsLoading } = useAlerts({ page: 1, size: 3 })

const llmExpanded = ref(false)
const aiSummaryText = ref('')

const riskIndex = computed(() => riskData.value?.riskIndex ?? 0)
const riskLevel = computed(() => riskData.value?.riskLevel ?? 'Low')
const topFactors = computed(() => riskData.value?.topFactors ?? [])

const dates = computed(() => tsData.value?.dates ?? [])
const oilPrice = computed(() => tsData.value?.oilPrice ?? [])
const tsRiskIndex = computed(() => tsData.value?.riskIndex ?? [])
const tsAlerts = computed(() => tsData.value?.alerts ?? [])

const isLoading = computed(() => riskLoading.value || tsLoading.value || alertsLoading.value)

async function fetchAISummary() {
  try {
    const res = await getAlerts({ page: 1, size: 1 })
    const records = res.data.data.records
    if (records.length > 0 && records[0].aiReport) {
      aiSummaryText.value = records[0].aiReport
    }
  } catch {
    // silent fail - non-critical feature
  }
}

onMounted(fetchAISummary)
</script>

<template>
  <div class="overview">
    <!-- Stale data warning -->
    <div v-if="riskStore.stale" class="overview__stale-banner">
      {{ t('overview.staleWarning') }}
    </div>

    <!-- Loading overlay -->
    <div v-if="isLoading" class="overview__loading">
      {{ t('common.loading') }}
    </div>

    <!-- Error state -->
    <div v-if="riskError" class="overview__error">
      {{ t('common.error') }}: {{ riskError }}
    </div>

    <!-- Main grid -->
    <div class="overview__grid">
      <!-- Row 1: Gauge + Price Chart -->
      <div class="overview__card overview__card--gauge">
        <h3 class="overview__card-title">{{ t('overview.gauge.title') }}</h3>
        <RiskGauge :risk-index="riskIndex" :risk-level="riskLevel" />
      </div>

      <div class="overview__card overview__card--price">
        <h3 class="overview__card-title">{{ t('overview.priceChart.title') }}</h3>
        <PriceRiskChart
          :dates="dates"
          :oil-price="oilPrice"
          :risk-index="tsRiskIndex"
          :alerts="tsAlerts"
        />
      </div>

      <!-- Row 2: Factor Bar + Alert Cards -->
      <div class="overview__card overview__card--factor">
        <h3 class="overview__card-title">{{ t('overview.factorChart.title') }}</h3>
        <FactorBarChart :factors="topFactors" />
      </div>

      <div class="overview__card overview__card--alerts">
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

      <!-- Row 3: LLM Summary (collapsible) -->
      <div class="overview__card overview__card--llm">
        <div class="overview__llm-header" @click="llmExpanded = !llmExpanded">
          <h3 class="overview__card-title">{{ t('overview.aiSummary') }}</h3>
          <button class="overview__llm-toggle">
            {{ llmExpanded ? t('overview.llmSummary.collapse') : t('overview.llmSummary.expand') }}
          </button>
        </div>
        <div v-if="llmExpanded" class="overview__llm-body">
          <p v-if="aiSummaryText" class="overview__llm-text">{{ aiSummaryText }}</p>
          <p v-else class="overview__llm-placeholder">{{ t('overview.noAISummary') }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.overview {
  max-width: 1400px;
  margin: 0 auto;
}

.overview__stale-banner {
  background: var(--risk-medium);
  color: #fff;
  text-align: center;
  padding: 8px;
  border-radius: 6px;
  margin-bottom: 16px;
  font-size: 13px;
  font-weight: 600;
}

.overview__loading {
  text-align: center;
  padding: 20px;
  color: var(--text-secondary);
  font-size: 14px;
}

.overview__error {
  background: rgba(248, 81, 73, 0.1);
  border: 1px solid var(--risk-high);
  color: var(--risk-high);
  padding: 12px 16px;
  border-radius: 6px;
  margin-bottom: 16px;
  font-size: 13px;
}

.overview__grid {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 16px;
}

.overview__card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 16px;
  transition: background-color 0.3s, border-color 0.3s;
}

.overview__card-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 12px;
}

.overview__card--gauge {
  grid-column: 1;
  grid-row: 1;
}

.overview__card--price {
  grid-column: 2;
  grid-row: 1;
}

.overview__card--factor {
  grid-column: 1;
  grid-row: 2;
}

.overview__card--alerts {
  grid-column: 2;
  grid-row: 2;
}

.overview__card--llm {
  grid-column: 1 / -1;
  grid-row: 3;
}

.overview__alerts-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.overview__no-data {
  color: var(--text-secondary);
  font-size: 13px;
  text-align: center;
  padding: 20px;
}

.overview__llm-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
}

.overview__llm-header .overview__card-title {
  margin-bottom: 0;
}

.overview__llm-toggle {
  background: transparent;
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.overview__llm-toggle:hover {
  color: var(--text-primary);
  border-color: var(--accent-blue);
}

.overview__llm-body {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-color);
}

.overview__llm-placeholder {
  color: var(--text-secondary);
  font-size: 13px;
  font-style: italic;
}

.overview__llm-text {
  color: var(--text-primary);
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
}
</style>
