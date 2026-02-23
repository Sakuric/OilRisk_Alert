import { computed } from 'vue'
import { useAppStore } from '@/stores/app'
import darkTheme from '@/theme/dark'
import lightTheme from '@/theme/light'

export function useTheme() {
  const appStore = useAppStore()

  const isDark = computed(() => appStore.theme === 'dark')

  const echartsThemeConfig = computed(() =>
    isDark.value ? darkTheme : lightTheme,
  )

  function toggle() {
    appStore.toggleTheme()
  }

  return { isDark, echartsThemeConfig, toggle }
}
