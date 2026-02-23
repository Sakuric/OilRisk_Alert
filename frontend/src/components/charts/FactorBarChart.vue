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
  const colors = values.map((v) => (v >= 0 ? '#58a6ff' : '#f85149'))

  return {
    ...themeOpts,
    animationDuration: 800,
    animationEasing: 'cubicOut',
    tooltip: {
      ...themeOpts.tooltip,
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
    },
    grid: {
      left: 120,
      right: 30,
      top: 10,
      bottom: 10,
    },
    xAxis: {
      type: 'value',
      name: t('overview.factorChart.shapValue'),
      ...(themeOpts.xAxis as Record<string, unknown>),
    },
    yAxis: {
      type: 'category',
      data: names,
      ...(themeOpts.yAxis as Record<string, unknown>),
      axisLabel: {
        color: isDark.value ? '#8b949e' : '#57606a',
        fontSize: 12,
      },
    },
    series: [
      {
        type: 'bar',
        data: values.map((v, i) => ({
          value: v,
          itemStyle: { color: colors[i] },
        })),
        barWidth: '60%',
        label: {
          show: true,
          position: 'right',
          color: isDark.value ? '#e6edf3' : '#24292f',
          fontSize: 11,
          formatter: (params: unknown) => {
            const p = params as { value: number }
            return p.value.toFixed(3)
          },
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
