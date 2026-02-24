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
  if (level === 'Low') return '#34d399'
  if (level === 'Medium') return '#fbbf24'
  return '#f43f5e'
}

function getOption(): echarts.EChartsOption {
  const dark = isDark.value
  const alertData = props.alerts.map((a) => {
    return {
      value: [a.date, a.riskIndex],
      itemStyle: {
        color: getAlertColor(a.level),
        shadowBlur: 10,
        shadowColor: getAlertColor(a.level)
      },
      _level: a.level,
    }
  })

  const textColor = dark ? '#b0b3d0' : '#4a4d6a'
  const gridColor = dark ? 'rgba(139, 92, 246, 0.08)' : 'rgba(0, 0, 0, 0.06)'
  const axisLineColor = dark ? 'rgba(139, 92, 246, 0.15)' : 'rgba(0, 0, 0, 0.08)'

  return {
    backgroundColor: 'transparent',
    animationDuration: 1000,
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'line',
        lineStyle: { color: dark ? 'rgba(139, 92, 246, 0.3)' : 'rgba(0, 0, 0, 0.15)', type: 'dashed' }
      },
      backgroundColor: dark ? 'rgba(8, 11, 26, 0.9)' : 'rgba(255, 255, 255, 0.95)',
      borderColor: dark ? 'rgba(139, 92, 246, 0.2)' : 'rgba(0, 0, 0, 0.1)',
      textStyle: { color: dark ? '#f1f1f8' : '#1a1a2e' }
    },
    legend: {
      data: [
        t('overview.priceChart.oilPrice'),
        t('overview.priceChart.riskIndex')
      ],
      textStyle: { color: textColor, fontSize: 12 },
      top: 0,
    },
    grid: {
      left: '3%',
      right: '3%',
      top: 50,
      bottom: 60,
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: props.dates,
      axisLine: { lineStyle: { color: axisLineColor } },
      axisLabel: { color: textColor, fontSize: 11 },
      boundaryGap: false,
    },
    yAxis: [
      {
        type: 'value',
        name: 'WTI ($)',
        position: 'left',
        splitLine: { lineStyle: { color: gridColor } },
        axisLabel: { color: textColor },
        nameTextStyle: { color: textColor }
      },
      {
        type: 'value',
        name: 'Risk',
        position: 'right',
        min: 0,
        max: 100,
        splitLine: { show: false },
        axisLabel: { color: textColor },
        nameTextStyle: { color: textColor }
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
        lineStyle: { width: 3, color: '#8b5cf6' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(139, 92, 246, 0.25)' },
            { offset: 1, color: 'rgba(139, 92, 246, 0)' }
          ])
        }
      },
      {
        name: t('overview.priceChart.riskIndex'),
        type: 'line',
        yAxisIndex: 1,
        data: props.riskIndex,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2, color: '#fbbf24', type: 'dashed' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(251, 191, 36, 0.12)' },
            { offset: 1, color: 'rgba(251, 191, 36, 0)' }
          ])
        }
      },
      {
        name: t('overview.priceChart.alert'),
        type: 'scatter',
        yAxisIndex: 1,
        data: alertData,
        symbolSize: 10,
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
