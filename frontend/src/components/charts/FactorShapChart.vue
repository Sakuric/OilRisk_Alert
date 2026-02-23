<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, computed } from 'vue'
import * as echarts from 'echarts'
import { useTheme } from '@/composables/useTheme'
import type { FactorDetail } from '@/types/factor'

const props = defineProps<{
  factors: FactorDetail[]
  locale: 'zh' | 'en'
}>()

const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null
const { isDark } = useTheme()

const topFactors = computed(() =>
  [...props.factors]
    .sort((a, b) => Math.abs(b.shap) - Math.abs(a.shap))
    .slice(0, 10)
    .reverse(),
)

function getOption(): echarts.EChartsOption {
  const names = topFactors.value.map((f) =>
    props.locale === 'zh' ? f.nameZh : f.name,
  )
  const values = topFactors.value.map((f) => f.shap)

  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: isDark.value ? '#1c2128' : '#fff',
      borderColor: isDark.value ? '#30363d' : '#d0d7de',
      textStyle: { color: isDark.value ? '#e6edf3' : '#24292f' },
    },
    grid: {
      left: 140,
      right: 40,
      top: 10,
      bottom: 10,
    },
    xAxis: {
      type: 'value',
      name: 'SHAP',
      axisLine: { lineStyle: { color: isDark.value ? '#30363d' : '#d0d7de' } },
      axisLabel: { color: isDark.value ? '#8b949e' : '#57606a' },
      splitLine: { lineStyle: { color: isDark.value ? '#21262d' : '#eaeef2' } },
    },
    yAxis: {
      type: 'category',
      data: names,
      axisLine: { lineStyle: { color: isDark.value ? '#30363d' : '#d0d7de' } },
      axisLabel: {
        color: isDark.value ? '#8b949e' : '#57606a',
        fontSize: 12,
      },
    },
    series: [
      {
        type: 'bar',
        data: values.map((v) => ({
          value: v,
          itemStyle: { color: v >= 0 ? '#4A90D9' : '#E74C3C' },
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
        animationDuration: 600,
      },
    ],
  }
}

function initChart() {
  if (!chartRef.value) return
  chart = echarts.init(chartRef.value)
  chart.setOption(getOption())
}

function updateChart() {
  if (!chart) return
  chart.setOption(getOption(), { notMerge: true })
}

function handleResize() {
  chart?.resize()
}

watch(() => [props.factors, props.locale, isDark.value], updateChart)

onMounted(() => {
  initChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
})
</script>

<template>
  <div ref="chartRef" class="factor-shap-chart"></div>
</template>

<style scoped>
.factor-shap-chart {
  width: 100%;
  height: 100%;
  min-height: 360px;
}
</style>
