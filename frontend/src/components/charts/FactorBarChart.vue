<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, computed } from 'vue'
import * as echarts from 'echarts'
import { useTheme } from '@/composables/useTheme'
import { useI18n } from 'vue-i18n'
import { useAppStore } from '@/stores/app'
import type { TopFactor } from '@/types/risk'

const props = defineProps<{
  factors: TopFactor[]
}>()

const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null
const { echartsThemeConfig, isDark } = useTheme()
const { t } = useI18n()
const appStore = useAppStore()

const isZh = computed(() => appStore.locale === 'zh-CN')

const sorted = computed(() =>
  [...props.factors].sort((a, b) => Math.abs(a.shap) - Math.abs(b.shap)),
)

function getOption(): echarts.EChartsOption {
  const themeOpts = echartsThemeConfig.value
  const names = sorted.value.map((f) => (isZh.value ? f.nameZh : f.name))
  const values = sorted.value.map((f) => f.shap)
  const posColor = '#8b5cf6'
  const negColor = '#f43f5e'

  return {
    backgroundColor: 'transparent',
    animationDuration: 1200,
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: isDark.value ? 'rgba(8, 11, 26, 0.9)' : 'rgba(255, 255, 255, 0.95)',
      borderColor: isDark.value ? 'rgba(139, 92, 246, 0.2)' : 'rgba(0, 0, 0, 0.1)',
      textStyle: { color: isDark.value ? '#f1f1f8' : '#1a1a2e' }
    },
    grid: {
      left: '5%',
      right: '10%',
      top: 10,
      bottom: 10,
      containLabel: true
    },
    xAxis: {
      type: 'value',
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: isDark.value ? 'rgba(139, 92, 246, 0.08)' : 'rgba(0, 0, 0, 0.06)' } },
      axisLabel: { color: isDark.value ? '#b0b3d0' : '#4a4d6a', fontSize: 10 }
    },
    yAxis: {
      type: 'category',
      data: names,
      axisLine: { lineStyle: { color: isDark.value ? 'rgba(139, 92, 246, 0.15)' : 'rgba(0, 0, 0, 0.08)' } },
      axisTick: { show: false },
      axisLabel: {
        color: isDark.value ? '#f1f1f8' : '#1a1a2e',
        fontSize: 11,
      },
    },
    series: [
      {
        type: 'bar',
        data: values.map((v) => ({
          value: v,
          itemStyle: {
            color: v >= 0 ? posColor : negColor,
            borderRadius: v >= 0 ? [0, 4, 4, 0] : [4, 0, 0, 4],
            shadowBlur: 8,
            shadowColor: v >= 0 ? posColor : negColor,
          },
        })),
        barWidth: 14,
        label: {
          show: true,
          position: 'right',
          color: isDark.value ? '#b0b3d0' : '#4a4d6a',
          fontSize: 10,
          formatter: (params: any) => params.value.toFixed(3),
        },
      },
    ],
  }
}

function initChart() {
  if (!chartRef.value) return
  chart = echarts.init(chartRef.value)
  chart.setOption(getOption(), { notMerge: false })
}

function updateChart() {
  if (!chart) return
  chart.setOption(getOption(), { notMerge: false })
}

watch(() => [props.factors, isDark.value, appStore.locale], updateChart)

onMounted(() => {
  initChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
})

function handleResize() {
  chart?.resize()
}
</script>

<template>
  <div ref="chartRef" class="factor-bar-chart"></div>
</template>

<style scoped>
.factor-bar-chart {
  width: 100%;
  height: 100%;
  min-height: 240px;
}
</style>
