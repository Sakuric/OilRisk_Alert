<script setup lang="ts">
import { ref, computed, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAppStore } from '@/stores/app'
import { useAlerts } from '@/composables/useAlerts'
import { getAlertDetail } from '@/api/alert'
import { createReportSSE } from '@/api/report'
import type { AlertRecord, AlertDetail, TriggerRule } from '@/types/alert'

const { t } = useI18n()
const appStore = useAppStore()
const isZh = computed(() => appStore.locale === 'zh-CN')

const page = ref(1)
const pageSize = ref(10)
const levelFilter = ref('')

const { data: alerts, total, loading, fetch: fetchAlerts } = useAlerts({
  page: page.value,
  size: pageSize.value,
})

function onPageChange(newPage: number) {
  page.value = newPage
  fetchAlerts({ page: newPage, size: pageSize.value, level: levelFilter.value || undefined })
}

function onLevelFilter(level: string) {
  levelFilter.value = level
  page.value = 1
  fetchAlerts({ page: 1, size: pageSize.value, level: level || undefined })
}

// Expanded row
const expandedId = ref<number | null>(null)
const detailLoading = ref(false)
const detailData = ref<AlertDetail | null>(null)

// AI report
const aiText = ref('')
const aiLoading = ref(false)
const aiError = ref(false)
const aiCache = ref<Record<number, string>>({})
let currentES: EventSource | null = null

function toggleExpand(alert: AlertRecord) {
  if (expandedId.value === alert.id) {
    expandedId.value = null
    detailData.value = null
    cancelAI()
    return
  }
  expandedId.value = alert.id
  aiText.value = ''
  aiLoading.value = false
  aiError.value = false
  loadDetail(alert.id)
}

async function loadDetail(id: number) {
  detailLoading.value = true
  try {
    const res = await getAlertDetail(id)
    detailData.value = res.data.data
    // If cached AI text available
    if (aiCache.value[id]) {
      aiText.value = aiCache.value[id]
    }
  } catch {
    detailData.value = null
  } finally {
    detailLoading.value = false
  }
}

function generateAI(alertId: number) {
  cancelAI()
  aiText.value = ''
  aiLoading.value = true
  aiError.value = false

  currentES = createReportSSE(
    alertId,
    (token) => {
      aiText.value += token
    },
    () => {
      aiLoading.value = false
      aiCache.value[alertId] = aiText.value
      currentES = null
    },
    () => {
      aiLoading.value = false
      aiError.value = true
      currentES = null
    },
  )
}

function cancelAI() {
  if (currentES) {
    currentES.close()
    currentES = null
  }
  aiLoading.value = false
}

function ruleBadgeClass(ruleType: TriggerRule['ruleType']): string {
  switch (ruleType) {
    case 'THRESHOLD':
      return 'badge--threshold'
    case 'TREND':
      return 'badge--trend'
    case 'ANOMALY':
      return 'badge--anomaly'
  }
}

function ruleBadgeText(ruleType: TriggerRule['ruleType']): string {
  switch (ruleType) {
    case 'THRESHOLD':
      return t('alertRecords.ruleThreshold')
    case 'TREND':
      return t('alertRecords.ruleTrend')
    case 'ANOMALY':
      return t('alertRecords.ruleAnomaly')
  }
}

function levelClass(level: string): string {
  return `level--${level.toLowerCase()}`
}

const totalPages = computed(() => Math.ceil(total.value / pageSize.value))
const hasAICache = computed(() =>
  expandedId.value !== null && !!aiCache.value[expandedId.value],
)

onUnmounted(() => {
  cancelAI()
})
</script>

<template>
  <div class="alert-records">
    <!-- Filter bar -->
    <div class="alert-records__filter">
      <button
        v-for="lv in ['', 'High', 'Medium', 'Low']"
        :key="lv"
        :class="['alert-records__filter-btn', { active: levelFilter === lv }]"
        @click="onLevelFilter(lv)"
      >
        {{ lv || 'All' }}
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="alert-records__loading">
      {{ t('common.loading') }}
    </div>

    <!-- Table -->
    <div class="alert-records__table-wrap">
      <table class="alert-records__table">
        <thead>
          <tr>
            <th>{{ t('alert.date') }}</th>
            <th>{{ t('alert.level') }}</th>
            <th>{{ t('alert.riskIndex') }}</th>
            <th>{{ t('alert.triggerFactor') }}</th>
            <th>{{ isZh ? 'Summary' : 'Summary' }}</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="alert in alerts" :key="alert.id">
            <tr
              :class="['alert-records__row', { 'alert-records__row--expanded': expandedId === alert.id }]"
              @click="toggleExpand(alert)"
            >
              <td>{{ alert.date }}</td>
              <td>
                <span :class="['alert-records__level', levelClass(alert.level)]">
                  {{ alert.level }}
                </span>
              </td>
              <td>{{ alert.riskIndex.toFixed(1) }}</td>
              <td>{{ isZh ? alert.triggerFactorZh : alert.triggerFactor }}</td>
              <td class="alert-records__summary">
                {{ isZh ? alert.summary : alert.summaryEn }}
              </td>
            </tr>

            <!-- Expanded detail row -->
            <tr v-if="expandedId === alert.id" class="alert-records__detail-row">
              <td colspan="5">
                <div class="alert-records__detail">
                  <!-- Loading detail -->
                  <div v-if="detailLoading" class="alert-records__detail-loading">
                    {{ t('common.loading') }}
                  </div>

                  <!-- Trigger Rules -->
                  <template v-if="detailData && detailData.triggerRules">
                    <h4 class="alert-records__section-title">{{ t('alertRecords.triggerRules') }}</h4>
                    <div class="alert-records__rules">
                      <div
                        v-for="(rule, idx) in detailData.triggerRules"
                        :key="idx"
                        class="alert-records__rule"
                      >
                        <span :class="['alert-records__badge', ruleBadgeClass(rule.ruleType)]">
                          {{ ruleBadgeText(rule.ruleType) }}
                        </span>
                        <span class="alert-records__rule-factor">
                          {{ isZh ? rule.factorZh : rule.factor }}
                        </span>
                        <span class="alert-records__rule-values">
                          {{ rule.currentValue.toFixed(2) }} &rarr; {{ rule.threshold.toFixed(2) }}
                        </span>
                        <span class="alert-records__rule-desc">{{ rule.description }}</span>
                      </div>
                    </div>
                  </template>

                  <!-- AI Report -->
                  <div class="alert-records__ai-section">
                    <button
                      v-if="!aiLoading"
                      class="alert-records__ai-btn"
                      @click.stop="generateAI(alert.id)"
                    >
                      {{ hasAICache ? t('alertRecords.regenerateAI') : t('alertRecords.generateAI') }}
                    </button>
                    <button
                      v-if="aiLoading"
                      class="alert-records__ai-btn alert-records__ai-btn--cancel"
                      @click.stop="cancelAI"
                    >
                      {{ t('alertRecords.cancelAI') }}
                    </button>

                    <div v-if="aiLoading" class="alert-records__ai-spinner">
                      <span class="spinner"></span>
                    </div>

                    <div v-if="aiError" class="alert-records__ai-error">
                      {{ t('alertRecords.aiUnavailable') }}
                    </div>

                    <div v-if="aiText" class="alert-records__ai-text">{{ aiText }}</div>
                  </div>
                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <!-- Pagination -->
    <div v-if="totalPages > 1" class="alert-records__pagination">
      <button
        :disabled="page <= 1"
        class="alert-records__page-btn"
        @click="onPageChange(page - 1)"
      >
        &laquo;
      </button>
      <span class="alert-records__page-info">{{ page }} / {{ totalPages }}</span>
      <button
        :disabled="page >= totalPages"
        class="alert-records__page-btn"
        @click="onPageChange(page + 1)"
      >
        &raquo;
      </button>
    </div>
  </div>
</template>

<style scoped>
.alert-records {
  max-width: 1400px;
  margin: 0 auto;
}

.alert-records__filter {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.alert-records__filter-btn {
  padding: 4px 14px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.alert-records__filter-btn.active,
.alert-records__filter-btn:hover {
  border-color: var(--accent-blue, #58a6ff);
  color: var(--text-primary);
}

.alert-records__loading {
  text-align: center;
  padding: 20px;
  color: var(--text-secondary);
}

.alert-records__table-wrap {
  overflow-x: auto;
}

.alert-records__table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.alert-records__table th {
  text-align: left;
  padding: 10px 12px;
  border-bottom: 2px solid var(--border-color);
  color: var(--text-secondary);
  font-weight: 600;
  white-space: nowrap;
}

.alert-records__table td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-color);
  color: var(--text-primary);
}

.alert-records__row {
  cursor: pointer;
  transition: background-color 0.15s;
}

.alert-records__row:hover {
  background: rgba(88, 166, 255, 0.05);
}

.alert-records__row--expanded {
  background: rgba(88, 166, 255, 0.08);
}

.alert-records__summary {
  max-width: 400px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.alert-records__level {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}

.level--high {
  background: rgba(248, 81, 73, 0.15);
  color: #f85149;
}

.level--medium {
  background: rgba(210, 153, 34, 0.15);
  color: #d29922;
}

.level--low {
  background: rgba(63, 185, 80, 0.15);
  color: #3fb950;
}

.alert-records__detail-row td {
  padding: 0;
}

.alert-records__detail {
  padding: 16px 20px;
  background: rgba(88, 166, 255, 0.03);
  border-bottom: 2px solid var(--border-color);
}

.alert-records__detail-loading {
  color: var(--text-secondary);
  font-size: 13px;
  padding: 8px 0;
}

.alert-records__section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 10px;
}

.alert-records__rules {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}

.alert-records__rule {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  padding: 6px 0;
  border-left: 3px solid var(--border-color);
  padding-left: 12px;
}

.alert-records__badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
}

.badge--threshold {
  background: rgba(210, 153, 34, 0.15);
  color: #d29922;
}

.badge--trend {
  background: rgba(88, 166, 255, 0.15);
  color: #58a6ff;
}

.badge--anomaly {
  background: rgba(248, 81, 73, 0.15);
  color: #f85149;
}

.alert-records__rule-factor {
  font-weight: 500;
  color: var(--text-primary);
}

.alert-records__rule-values {
  font-family: monospace;
  color: var(--text-secondary);
}

.alert-records__rule-desc {
  color: var(--text-secondary);
  font-size: 12px;
}

.alert-records__ai-section {
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 10px;
}

.alert-records__ai-btn {
  padding: 6px 16px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}

.alert-records__ai-btn:hover {
  border-color: var(--accent-blue, #58a6ff);
  color: var(--text-primary);
}

.alert-records__ai-btn--cancel {
  border-color: var(--risk-high);
  color: var(--risk-high);
}

.alert-records__ai-spinner {
  display: flex;
  align-items: center;
}

.spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid var(--border-color);
  border-top-color: var(--accent-blue, #58a6ff);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.alert-records__ai-error {
  width: 100%;
  padding: 8px 12px;
  background: rgba(248, 81, 73, 0.1);
  border: 1px solid var(--risk-high);
  border-radius: 6px;
  color: var(--risk-high);
  font-size: 13px;
}

.alert-records__ai-text {
  width: 100%;
  padding: 12px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-primary);
  white-space: pre-wrap;
}

.alert-records__pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-top: 16px;
}

.alert-records__page-btn {
  padding: 4px 12px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: transparent;
  color: var(--text-secondary);
  font-size: 14px;
  cursor: pointer;
}

.alert-records__page-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.alert-records__page-info {
  font-size: 13px;
  color: var(--text-secondary);
}
</style>
