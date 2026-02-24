<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAppStore } from '@/stores/app'
import type { AlertRecord } from '@/types/alert'

const props = defineProps<{
  alert: AlertRecord
}>()

const { t } = useI18n()
const appStore = useAppStore()

const isZh = computed(() => appStore.locale === 'zh-CN')

const levelColor = computed(() => {
  if (props.alert.level === 'Low') return 'var(--risk-low)'
  if (props.alert.level === 'Medium') return 'var(--risk-medium)'
  return 'var(--risk-high)'
})

const summary = computed(() =>
  isZh.value ? props.alert.summary : props.alert.summaryEn,
)

const factorName = computed(() =>
  isZh.value ? props.alert.triggerFactorZh : props.alert.triggerFactor,
)
</script>

<template>
  <div class="alert-card">
    <div class="alert-card__stripe" :style="{ backgroundColor: levelColor }"></div>
    <div class="alert-card__body">
      <div class="alert-card__header">
        <span class="alert-card__date">{{ props.alert.date }}</span>
        <span class="alert-card__badge" :style="{ backgroundColor: levelColor }">
          {{ t(`risk.level.${props.alert.level}`) }}
        </span>
      </div>
      <div class="alert-card__meta">
        <span class="alert-card__factor">
          {{ t('alert.triggerFactor') }}: {{ factorName }}
        </span>
        <span class="alert-card__type">
          {{ t(`alert.triggerType.${props.alert.triggerType}`) }}
        </span>
      </div>
      <p class="alert-card__summary">{{ summary }}</p>
    </div>
  </div>
</template>

<style scoped>
.alert-card {
  display: flex;
  border: 1px solid var(--bg-card-border);
  border-radius: 10px;
  overflow: hidden;
  background: var(--bg-card);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  transition: background-color 0.3s, border-color 0.3s;
}

.alert-card__stripe {
  width: 4px;
  flex-shrink: 0;
}

.alert-card__body {
  flex: 1;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.alert-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.alert-card__date {
  font-size: 13px;
  color: var(--text-secondary);
}

.alert-card__badge {
  font-size: 11px;
  color: #fff;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 600;
}

.alert-card__meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: var(--text-secondary);
}

.alert-card__factor {
  font-weight: 500;
  color: var(--text-primary);
}

.alert-card__type {
  background: var(--badge-bg);
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 11px;
  color: var(--text-secondary);
}

.alert-card__summary {
  font-size: 13px;
  line-height: 1.5;
  color: var(--text-primary);
}
</style>
