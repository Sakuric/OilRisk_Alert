<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { useTheme } from '@/composables/useTheme'
import { useI18n } from 'vue-i18n'

export interface WeightDataPoint {
  date: string
  supplyDemand: number
  macro: number
  financial: number
  geopolitical: number
  sentiment: number
}

const props = defineProps<{
  data: WeightDataPoint[]
}>()

const emit = defineEmits<{
  (e: 'selectDate', date: string): void
}>()

const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null
const { isDark } = useTheme()
const { t } = useI18n()

const categoryColors: Record<string, string> = {
  supplyDemand: '#8b5cf6',
  macro: '#3b82f6',
  financial: '#10b981',
  geopolitical: '#f59e0b',
  sentiment: '#ef4444',
}

const categoryKeys = [
  { key: 'supplyDemand', i18nKey: 'Supply-Demand' },
  { key: 'macro', i18nKey: 'Macro' },
  { key: 'financial', i18nKey: 'Financial' },
  { key: 'geopolitical', i18nKey: 'Geopolitical' },
  { key: 'sentiment', i18nKey: 'Sentiment' },
] as const

function getOption(): any {
  const dark = isDark.value
  const textColor = dark ? '#b0b3d0' : '#4a4d6a'
  const gridColor = dark ? 'rgba(139, 92, 246, 0.08)' : 'rgba(0, 0, 0, 0.06)'
  const axisLineColor = dark ? 'rgba(139, 92, 246, 0.15)' : 'rgba(0, 0, 0, 0.08)'

  const series = categoryKeys.map((cat) => ({
    name: t(`factor.category.${cat.i18nKey}`),
    type: 'line',
    stack: 'Total',
    smooth: true,
    lineStyle: { width: 0 },
    showSymbol: false,
    areaStyle: {
      opacity: 0.8,
      color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: categoryColors[cat.key] },
        { offset: 1, color: categoryColors[cat.key] + '80' },
      ]),
    },
    emphasis: { focus: 'series' },
    data: props.data.map((d) => d[cat.key as keyof WeightDataPoint] as number),
  }))

  return {
    backgroundColor: 'transparent',
    animationDuration: 1000,
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        label: { backgroundColor: dark ? '#1c2128' : '#fff' },
      },
      backgroundColor: dark ? 'rgba(8, 11, 26, 0.9)' : 'rgba(255, 255, 255, 0.95)',
      borderColor: dark ? 'rgba(139, 92, 246, 0.2)' : 'rgba(0, 0, 0, 0.1)',
      textStyle: { color: dark ? '#f1f1f8' : '#1a1a2e' },
      formatter: (params: any[]) => {
        if (!params || params.length === 0) return ''
        const date = params[0].axisValue
        let html = `<div style="font-weight: bold; margin-bottom: 8px;">${date}</div>`
        params.forEach((p) => {
          html += `<div style="display: flex; align-items: center; margin: 4px 0;">
            <span style="display: inline-block; width: 10px; height: 10px; background: ${p.color}; border-radius: 50%; margin-right: 8px;"></span>
            <span style="flex: 1;">${p.seriesName}:</span>
            <span style="font-weight: bold;">${p.value?.toFixed(2) || 0}%</span>
          </div>`
        })
        return html
      },
    },
    legend: {
      data: categoryKeys.map((c) => t(`factor.category.${c.i18nKey}`)),
      textStyle: { color: textColor, fontSize: 11 },
      top: 0,
      itemWidth: 12,
      itemHeight: 12,
    },
    grid: {
      left: '3%',
      right: '4%',
      top: 50,
      bottom: 60,
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: props.data.map((d) => d.date),
      axisLine: { lineStyle: { color: axisLineColor } },
      axisLabel: {
        color: textColor,
        fontSize: 10,
        rotate: 45,
        formatter: (value: string) => {
          const date = new Date(value)
          return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
        },
      },
    },
    yAxis: {
      type: 'value',
      name: t('factorAnalysis.weightPercentage'),
      min: 0,
      max: 100,
      nameTextStyle: { color: textColor },
      axisLine: { lineStyle: { color: axisLineColor } },
      axisLabel: {
        color: textColor,
        formatter: '{value}%',
      },
      splitLine: { lineStyle: { color: gridColor } },
    },
    dataZoom: [
      {
        type: 'inside',
        start: 0,
        end: 100,
      },
      {
        start: 0,
        end: 100,
        height: 20,
        bottom: 10,
        textStyle: { color: textColor },
        borderColor: axisLineColor,
        fillerColor: dark ? 'rgba(139, 92, 246, 0.2)' : 'rgba(139, 92, 246, 0.1)',
        handleStyle: {
          color: dark ? '#8b5cf6' : '#7c3aed',
        },
      },
    ],
    series,
  }
}

function initChart() {
  if (!chartRef.value) return
  chart = echarts.init(chartRef.value)
  chart.setOption(getOption())

  chart.on('click', (params: any) => {
    if (params && params.name) {
      emit('selectDate', params.name)
    }
  })
}

function updateChart() {
  if (!chart) return
  chart.setOption(getOption(), { notMerge: true })
}

function handleResize() {
  chart?.resize()
}

watch(() => [props.data, isDark.value], updateChart, { deep: true })

onMounted(() => {
  initChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
  chart = null
})
</script>

<template>
  <div ref="chartRef" class="weight-area-chart"></div>
</template>

<style scoped>
.weight-area-chart {
  width: 100%;
  height: 100%;
  min-height: 360px;
}
</style>
