<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { useI18n } from 'vue-i18n'
import type { RadarScore } from '@/types/factor'

const props = defineProps<{
  data: RadarScore[]
  theme: 'dark' | 'light'
}>()

const { t } = useI18n()
const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

const categoryKeys = ['Supply-Demand', 'Macro', 'Financial', 'Geopolitical', 'Sentiment'] as const

function getOption(): echarts.EChartsOption {
  const isDark = props.theme === 'dark'
  const axisColor = isDark ? '#444' : '#ddd'
  const textColor = isDark ? '#ccc' : '#333'

  const labels = categoryKeys.map((key) => t(`factor.category.${key}`))
  const values = categoryKeys.map((key) => {
    const item = props.data.find(
      (d) => d.category === key || d.categoryZh === t(`factor.category.${key}`),
    )
    return item?.score ?? 0
  })

  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: isDark ? '#1c2128' : '#fff',
      borderColor: isDark ? '#30363d' : '#d0d7de',
      textStyle: { color: isDark ? '#e6edf3' : '#24292f' },
    },
    radar: {
      indicator: labels.map((name) => ({ name, max: 100 })),
      axisLine: { lineStyle: { color: axisColor } },
      splitLine: { lineStyle: { color: axisColor } },
      splitArea: { show: false },
      axisName: {
        color: textColor,
        fontSize: 13,
      },
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: values,
            name: t('factorAnalysis.radarTitle'),
            areaStyle: {
              color: isDark
                ? 'rgba(88,166,255,0.25)'
                : 'rgba(9,105,218,0.2)',
            },
            lineStyle: {
              color: isDark ? '#58a6ff' : '#0969da',
              width: 2,
            },
            itemStyle: {
              color: isDark ? '#58a6ff' : '#0969da',
            },
          },
        ],
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

watch(() => [props.data, props.theme], updateChart)

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
  <div ref="chartRef" class="radar-chart"></div>
</template>

<style scoped>
.radar-chart {
  width: 100%;
  height: 100%;
  min-height: 300px;
}
</style>
