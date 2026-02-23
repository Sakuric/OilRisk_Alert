<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { useTheme } from '@/composables/useTheme'
import { useI18n } from 'vue-i18n'

interface AlertPoint {
  date: string
  level: string
  riskIndex: number
}

const props = defineProps<{
  dates: string[]
  oilPrice: number[]
  riskIndex: number[]
  alerts: AlertPoint[]
}>()

const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null
const { echartsThemeConfig, isDark } = useTheme()
const { t } = useI18n()

function getAlertColor(level: string): string {
  if (level === 'Low') return '#3fb950'
  if (level === 'Medium') return '#d29922'
  return '#f85149'
}

function getOption(): echarts.EChartsOption {
  const themeOpts = echartsThemeConfig.value
  const alertData = props.alerts.map((a) => {
    const idx = props.dates.indexOf(a.date)
    return {
      value: [a.date, a.riskIndex],
      itemStyle: { color: getAlertColor(a.level) },
      _level: a.level,
      _dateIdx: idx,
    }
  })

  return {
    ...themeOpts,
    animationDuration: 800,
    animationEasing: 'cubicOut',
    tooltip: {
      ...themeOpts.tooltip,
      trigger: 'axis',
      axisPointer: { type: 'cross' },
    },
    legend: {
      ...themeOpts.legend,
      data: [
        t('overview.priceChart.oilPrice'),
        t('overview.priceChart.riskIndex'),
        t('overview.priceChart.alert'),
      ],
      top: 0,
    },
    grid: {
      left: 60,
      right: 60,
      top: 40,
      bottom: 60,
    },
    xAxis: {
      type: 'category',
      data: props.dates,
      ...(themeOpts.xAxis as Record<string, unknown>),
      boundaryGap: false,
    },
    yAxis: [
      {
        type: 'value',
        name: t('overview.priceChart.oilPrice'),
        position: 'left',
        ...(themeOpts.yAxis as Record<string, unknown>),
      },
      {
        type: 'value',
        name: t('overview.priceChart.riskIndex'),
        position: 'right',
        min: 0,
        max: 100,
        ...(themeOpts.yAxis as Record<string, unknown>),
      },
    ],
    dataZoom: [
      {
        type: 'inside',
        start: 0,
        end: 100,
      },
      {
        type: 'slider',
        start: 0,
        end: 100,
        height: 20,
        bottom: 8,
        borderColor: isDark.value ? '#30363d' : '#d0d7de',
        backgroundColor: isDark.value ? '#0d1117' : '#f6f8fa',
        fillerColor: isDark.value ? 'rgba(88,166,255,0.2)' : 'rgba(9,105,218,0.2)',
        handleStyle: {
          color: isDark.value ? '#58a6ff' : '#0969da',
        },
        textStyle: {
          color: isDark.value ? '#8b949e' : '#57606a',
        },
      },
    ],
    series: [
      {
        name: t('overview.priceChart.oilPrice'),
        type: 'line',
        yAxisIndex: 0,
        data: props.oilPrice,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2, color: '#58a6ff' },
        itemStyle: { color: '#58a6ff' },
      },
      {
        name: t('overview.priceChart.riskIndex'),
        type: 'line',
        yAxisIndex: 1,
        data: props.riskIndex,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2, color: '#d29922' },
        itemStyle: { color: '#d29922' },
      },
      {
        name: t('overview.priceChart.alert'),
        type: 'scatter',
        yAxisIndex: 1,
        data: alertData,
        symbolSize: 12,
        z: 10,
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

watch(
  () => [props.dates, props.oilPrice, props.riskIndex, props.alerts, isDark.value],
  updateChart,
)

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
  <div ref="chartRef" class="price-risk-chart"></div>
</template>

<style scoped>
.price-risk-chart {
  width: 100%;
  height: 100%;
  min-height: 340px;
}
</style>
