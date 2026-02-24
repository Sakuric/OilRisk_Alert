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
  width: 240px;
  height: 100vh;
  background: var(--sidebar-bg);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  flex-shrink: 0;
  position: sticky;
  top: 0;
  z-index: 100;
}

.sidebar--collapsed {
  width: 68px;
}

.sidebar__logo {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 24px 20px;
  cursor: pointer;
  min-height: 80px;
  border-bottom: 1px solid var(--border-subtle);
}

.sidebar__logo-icon {
  font-size: 24px;
  filter: drop-shadow(0 0 8px var(--accent-primary));
}

.sidebar__logo-text {
  font-size: 16px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 1px;
  background: linear-gradient(90deg, #fff, var(--accent-primary));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.sidebar__nav {
  display: flex;
  flex-direction: column;
  padding: 20px 12px;
  gap: 8px;
}

.sidebar__item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 500;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: left;
  position: relative;
}

.sidebar__item:hover {
  background: var(--hover-bg);
  color: var(--text-primary);
}

.sidebar__item--active {
  background: var(--accent-primary-dim);
  color: var(--accent-primary);
  font-weight: 600;
}

.sidebar__item--active::after {
  content: "";
  position: absolute;
  left: 0;
  top: 20%;
  bottom: 20%;
  width: 3px;
  background: var(--accent-primary);
  box-shadow: 0 0 10px var(--accent-primary);
  border-radius: 0 4px 4px 0;
}

.sidebar__item-icon {
  font-size: 20px;
  width: 24px;
  text-align: center;
  opacity: 0.8;
}

.sidebar__item--active .sidebar__item-icon {
  opacity: 1;
  filter: drop-shadow(0 0 5px var(--accent-primary));
}
</style>
