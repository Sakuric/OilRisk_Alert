import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export type ThemeMode = 'dark' | 'light'
export type LocaleCode = 'zh-CN' | 'en-US'

export interface TimeRange {
  label: string
  start: string
  end: string
}

function getDefaultTimeRange(): TimeRange {
  const end = new Date()
  const start = new Date()
  start.setFullYear(start.getFullYear() - 2)
  return {
    label: '2y',
    start: start.toISOString().slice(0, 10),
    end: end.toISOString().slice(0, 10),
  }
}

export const useAppStore = defineStore('app', () => {
  const theme = ref<ThemeMode>(
    (localStorage.getItem('theme') as ThemeMode) || 'dark',
  )
  const locale = ref<LocaleCode>(
    (localStorage.getItem('locale') as LocaleCode) || 'zh-CN',
  )
  const timeRange = ref<TimeRange>(getDefaultTimeRange())
  const sidebarCollapsed = ref(false)

  function setTheme(mode: ThemeMode) {
    theme.value = mode
    localStorage.setItem('theme', mode)
    document.documentElement.setAttribute('data-theme', mode)
  }

  function toggleTheme() {
    setTheme(theme.value === 'dark' ? 'light' : 'dark')
  }

  function setLocale(code: LocaleCode) {
    locale.value = code
    localStorage.setItem('locale', code)
  }

  function toggleLocale() {
    setLocale(locale.value === 'zh-CN' ? 'en-US' : 'zh-CN')
  }

  function setTimeRange(label: string, start: string, end: string) {
    timeRange.value = { label, start, end }
  }

  function setTimeRangeByPreset(preset: '1y' | '2y' | '5y' | 'all') {
    const end = new Date()
    const start = new Date()
    switch (preset) {
      case '1y':
        start.setFullYear(start.getFullYear() - 1)
        break
      case '2y':
        start.setFullYear(start.getFullYear() - 2)
        break
      case '5y':
        start.setFullYear(start.getFullYear() - 5)
        break
      case 'all':
        start.setFullYear(2015, 0, 1)
        break
    }
    timeRange.value = {
      label: preset,
      start: start.toISOString().slice(0, 10),
      end: end.toISOString().slice(0, 10),
    }
  }

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  // Initialize theme on document
  watch(theme, (val) => {
    document.documentElement.setAttribute('data-theme', val)
  }, { immediate: true })

  return {
    theme,
    locale,
    timeRange,
    sidebarCollapsed,
    setTheme,
    toggleTheme,
    setLocale,
    toggleLocale,
    setTimeRange,
    setTimeRangeByPreset,
    toggleSidebar,
  }
})
