<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, computed } from 'vue'
import * as echarts from 'echarts'
import { useTheme } from '@/composables/useTheme'
import { useI18n } from 'vue-i18n'
import type { TimeseriesPoint } from '@/types/risk'

const props = defineProps<{
  dates: string[]
  oilPrice: number[]
  alerts: TimeseriesPoint[]
}>()

const emit = defineEmits<{
  (e: 'selectAlert', alert: TimeseriesPoint): void
}>()

const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null
const { isDark } = useTheme()
const { t } = useI18n()

const RISK_COLORS = {
  Low: '#4CAF50',
  Medium: '#FFC107',
  High: '#F44336',
}

const alertData = computed(() => {
  return props.alerts.map((alert) => {
    const level = alert.level as keyof typeof RISK_COLORS
    const color = RISK_COLORS[level] || '#94a3b8'
    return {
      value: [alert.date, alert.riskIndex],
      itemStyle: {
        color,
        shadowBlur: 15,
        shadowColor: color,
      },
      symbolSize: level === 'High' ? 20 : level === 'Medium' ? 16 : 12,
      _alert: alert,
    }
  })
})

function getOption(): any {
  const dark = isDark.value
  const textColor = dark ? '#b0b3d0' : '#4a4d6a'
  const gridColor = dark ? 'rgba(139, 92, 246, 0.08)' : 'rgba(0, 0, 0, 0.06)'
  const axisLineColor = dark ? 'rgba(139, 92, 246, 0.15)' : 'rgba(0, 0, 0, 0.08)'

  return {
    backgroundColor: 'transparent',
    animationDuration: 1000,
    tooltip: {
      trigger: 'item',
      backgroundColor: dark ? 'rgba(8, 11, 26, 0.9)' : 'rgba(255, 255, 255, 0.95)',
      borderColor: dark ? 'rgba(139, 92, 246, 0.2)' : 'rgba(0, 0, 0, 0.1)',
      textStyle: { color: dark ? '#f1f1f8' : '#1a1a2e' },
      formatter: (params: any) => {
        const alert = params.data._alert as TimeseriesPoint
        if (!alert) return ''
        const color = RISK_COLORS[alert.level as keyof typeof RISK_COLORS]
        return `
          <div style="font-weight: bold; margin-bottom: 8px;">${alert.date}</div>
          <div style="display: flex; align-items: center; gap: 8px;">
            <span style="display: inline-block; width: 12px; height: 12px; background: ${color}; border-radius: 50%;"></span>
            <span>${t('risk.level.' + alert.level)}</span>
          </div>
          <div style="margin-top: 8px; color: ${textColor};">
            ${t('overview.priceChart.riskIndex')}: ${alert.riskIndex.toFixed(1)}
          </div>
        `
      },
    },
    legend: {
      data: [
        t('overview.priceChart.oilPrice'),
        t('risk.level.Low'),
        t('risk.level.Medium'),
        t('risk.level.High'),
      ],
      textStyle: { color: textColor, fontSize: 11 },
      top: 0,
    },
    grid: {
      left: '3%',
      right: '3%',
      top: 50,
      bottom: 60,
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: props.dates,
      axisLine: { lineStyle: { color: axisLineColor } },
      axisLabel: {
        color: textColor,
        fontSize: 10,
        rotate: 45,
      },
      boundaryGap: false,
    },
    yAxis: {
      type: 'value',
      name: 'WTI ($)',
      nameTextStyle: { color: textColor },
      axisLine: { lineStyle: { color: axisLineColor } },
      axisLabel: { color: textColor },
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
    series: [
      {
        name: t('overview.priceChart.oilPrice'),
        type: 'line',
        data: props.oilPrice,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2, color: '#8b5cf6' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(139, 92, 246, 0.2)' },
            { offset: 1, color: 'rgba(139, 92, 246, 0)' },
          ]),
        },
      },
      {
        name: t('risk.level.Low'),
        type: 'scatter',
        data: alertData.value.filter((d) => d._alert.level === 'Low'),
        symbol: 'circle',
        symbolSize: 12,
        itemStyle: { color: RISK_COLORS.Low },
        z: 10,
      },
      {
        name: t('risk.level.Medium'),
        type: 'scatter',
        data: alertData.value.filter((d) => d._alert.level === 'Medium'),
        symbol: 'circle',
        symbolSize: 16,
        itemStyle: { color: RISK_COLORS.Medium },
        z: 10,
      },
      {
        name: t('risk.level.High'),
        type: 'scatter',
        data: alertData.value.filter((d) => d._alert.level === 'High'),
        symbol: 'circle',
        symbolSize: 20,
        itemStyle: { color: RISK_COLORS.High },
        z: 10,
      },
    ],
  }
}

function initChart() {
  if (!chartRef.value) return
  chart = echarts.init(chartRef.value)
  chart.setOption(getOption())

  chart.on('click', (params: any) => {
    if (params?.data?._alert) {
      emit('selectAlert', params.data._alert)
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

watch(
  () => [props.dates, props.oilPrice, props.alerts, isDark.value],
  updateChart,
  { deep: true },
)

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
  <div ref="chartRef" class="alert-timeline-chart"></div>
</template>

<style scoped>
.alert-timeline-chart {
  width: 100%;
  height: 100%;
  min-height: 340px;
}
</style>
