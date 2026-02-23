<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAppStore } from '@/stores/app'

const router = useRouter()
const route = useRoute()
const { t } = useI18n()
const appStore = useAppStore()

const collapsed = computed(() => appStore.sidebarCollapsed)

interface NavItem {
  key: string
  route: string
  icon: string
  labelKey: string
}

const navItems: NavItem[] = [
  { key: 'overview', route: '/', icon: '📊', labelKey: 'nav.overview' },
  { key: 'factors', route: '/factors', icon: '🔬', labelKey: 'nav.factors' },
  { key: 'alerts', route: '/alerts', icon: '🔔', labelKey: 'nav.alerts' },
  { key: 'backtest', route: '/backtest', icon: '📈', labelKey: 'nav.backtest' },
]

function isActive(item: NavItem): boolean {
  return route.path === item.route
}

function navigate(item: NavItem) {
  router.push(item.route)
}
</script>

<template>
  <aside class="sidebar" :class="{ 'sidebar--collapsed': collapsed }">
    <div class="sidebar__logo" @click="appStore.toggleSidebar()">
      <span class="sidebar__logo-icon">⛽</span>
      <span v-if="!collapsed" class="sidebar__logo-text">OilRisk Alert</span>
    </div>
    <nav class="sidebar__nav">
      <button
        v-for="item in navItems"
        :key="item.key"
        class="sidebar__item"
        :class="{ 'sidebar__item--active': isActive(item) }"
        @click="navigate(item)"
        :title="t(item.labelKey)"
      >
        <span class="sidebar__item-icon">{{ item.icon }}</span>
        <span v-if="!collapsed" class="sidebar__item-label">{{ t(item.labelKey) }}</span>
      </button>
    </nav>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 220px;
  height: 100vh;
  background: var(--sidebar-bg);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  transition: width 0.3s, background-color 0.3s;
  flex-shrink: 0;
  position: sticky;
  top: 0;
}

.sidebar--collapsed {
  width: 60px;
}

.sidebar__logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px;
  cursor: pointer;
  border-bottom: 1px solid var(--border-color);
  min-height: 56px;
}

.sidebar__logo-icon {
  font-size: 22px;
  flex-shrink: 0;
}

.sidebar__logo-text {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
  white-space: nowrap;
}

.sidebar__nav {
  display: flex;
  flex-direction: column;
  padding: 8px;
  gap: 2px;
}

.sidebar__item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 14px;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.2s, color 0.2s;
  text-align: left;
  white-space: nowrap;
}

.sidebar__item:hover {
  background: var(--hover-bg);
  color: var(--text-primary);
}

.sidebar__item--active {
  background: var(--hover-bg);
  color: var(--accent-blue);
  font-weight: 600;
}

.sidebar__item-icon {
  font-size: 18px;
  flex-shrink: 0;
  width: 24px;
  text-align: center;
}

.sidebar__item-label {
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
