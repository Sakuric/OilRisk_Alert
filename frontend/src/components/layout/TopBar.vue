<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAppStore } from '@/stores/app'

const { t } = useI18n()
const appStore = useAppStore()

const isDark = computed(() => appStore.theme === 'dark')
const isZh = computed(() => appStore.locale === 'zh-CN')

type TimePreset = '1y' | '2y' | '5y' | 'all'
const presets: TimePreset[] = ['1y', '2y', '5y', 'all']

function selectPreset(p: TimePreset) {
  appStore.setTimeRangeByPreset(p)
}
</script>

<template>
  <header class="topbar">
    <div class="topbar__left">
      <span class="topbar__time-label">{{ t('topbar.timeRange.label') }}:</span>
      <div class="topbar__presets">
        <button
          v-for="p in presets"
          :key="p"
          class="topbar__preset-btn"
          :class="{ 'topbar__preset-btn--active': appStore.timeRange.label === p }"
          @click="selectPreset(p)"
        >
          {{ t(`topbar.timeRange.${p}`) }}
        </button>
      </div>
    </div>
    <div class="topbar__right">
      <button class="topbar__btn" @click="appStore.toggleLocale()" :title="isZh ? 'Switch to English' : '切换中文'">
        {{ isZh ? 'EN' : '中' }}
      </button>
      <button class="topbar__btn" @click="appStore.toggleTheme()" :title="isDark ? t('topbar.themeLight') : t('topbar.themeDark')">
        {{ isDark ? '☀️' : '🌙' }}
      </button>
    </div>
  </header>
</template>

<style scoped>
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 48px;
  padding: 0 20px;
  background: var(--topbar-bg);
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
  transition: background-color 0.3s;
}

.topbar__left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.topbar__time-label {
  font-size: 13px;
  color: var(--text-secondary);
}

.topbar__presets {
  display: flex;
  gap: 4px;
}

.topbar__preset-btn {
  padding: 4px 12px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: transparent;
  color: var(--text-secondary);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.topbar__preset-btn:hover {
  color: var(--text-primary);
  border-color: var(--accent-blue);
}

.topbar__preset-btn--active {
  background: var(--accent-blue);
  color: #fff;
  border-color: var(--accent-blue);
}

.topbar__right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.topbar__btn {
  padding: 4px 12px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: transparent;
  color: var(--text-primary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  min-width: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.topbar__btn:hover {
  background: var(--hover-bg);
  border-color: var(--accent-blue);
}
</style>
