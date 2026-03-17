<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, computed } from 'vue'
import * as echarts from 'echarts'
import { useTheme } from '@/composables/useTheme'
import { useI18n } from 'vue-i18n'
import type { TimeseriesPoint } from '@/types/risk'

/**
 * 综合图表组件 - 油价、风险指数与预警时间线
 *
 * 功能：
 * - 展示油价走势（紫色面积图）
 * - 展示风险指数走势（黄色虚线）
 * - 叠加预警事件标记（按级别显示不同颜色和大小的散点）
 * - 支持时间轴缩放
 * - 支持点击预警查看详情
 */

const props = defineProps<{
  dates: string[]
  oilPrice: number[]
  riskIndex: number[]
  alerts: TimeseriesPoint[]
}>()

const emit = defineEmits<{
  (e: 'selectAlert', alert: TimeseriesPoint): void
}>()

const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null
const { isDark } = useTheme()
const { t } = useI18n()

// 当前可见数据范围（百分比），用于自适应标签密度
const visibleStart = ref(80)
const visibleEnd = ref(100)

// 预警级别颜色配置 - 行业标准色
const ALERT_COLORS = {
  Low: '#4CAF50',
  Medium: '#FFC107',
  High: '#F44336',
}

// 处理预警数据，按级别分组
const alertDataByLevel = computed(() => {
  const result = {
    Low: [] as any[],
    Medium: [] as any[],
    High: [] as any[],
  }

  props.alerts.forEach((alert) => {
    const level = alert.level as keyof typeof ALERT_COLORS
    const color = ALERT_COLORS[level] || '#94a3b8'
    const size = level === 'High' ? 18 : level === 'Medium' ? 14 : 10

    result[level].push({
      value: [alert.date, alert.riskIndex],
      itemStyle: {
        color: color,
        shadowBlur: 12,
        shadowColor: color,
      },
      symbolSize: size,
      _alert: alert,
    })
  })

  return result
})

/**
 * 根据当前可见范围计算时间粒度：
 * - 可见天数 > 365 → 年粒度
 * - 可见天数 > 90  → 月粒度
 * - 否则           → 日粒度
 */
function getTimeGranularity(): 'year' | 'month' | 'day' {
  const total = props.dates.length
  if (total === 0) return 'year'
  const visibleCount = Math.max(1, Math.round(total * (visibleEnd.value - visibleStart.value) / 100))
  const first = new Date(props.dates[Math.floor(total * visibleStart.value / 100)] || props.dates[0])
  const last = new Date(props.dates[Math.min(total - 1, Math.ceil(total * visibleEnd.value / 100))] || props.dates[total - 1])
  const daySpan = Math.abs(last.getTime() - first.getTime()) / 86400000
  if (daySpan > 365) return 'year'
  if (daySpan > 90) return 'month'
  return 'day'
}

function getOption(): echarts.EChartsOption {
  const dark = isDark.value
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
        lineStyle: {
          color: dark ? 'rgba(139, 92, 246, 0.3)' : 'rgba(0, 0, 0, 0.15)',
          type: 'dashed',
        },
      },
      backgroundColor: dark ? 'rgba(8, 11, 26, 0.95)' : 'rgba(255, 255, 255, 0.95)',
      borderColor: dark ? 'rgba(139, 92, 246, 0.2)' : 'rgba(0, 0, 0, 0.1)',
      textStyle: { color: dark ? '#f1f1f8' : '#1a1a2e' },
      formatter: (params: any) => {
        if (!Array.isArray(params) || params.length === 0) return ''

        const date = params[0].axisValue
        let html = `<div style="font-weight: bold; margin-bottom: 8px; font-size: 14px;">${date}</div>`

        params.forEach((param: any) => {
          if (param.seriesType === 'line') {
            const color = param.color
            const value = typeof param.value === 'number' ? param.value.toFixed(2) : param.value
            html += `
              <div style="display: flex; align-items: center; gap: 8px; margin: 4px 0;">
                <span style="display: inline-block; width: 10px; height: 10px; background: ${color}; border-radius: 50%;"></span>
                <span>${param.seriesName}: <strong>${value}</strong></span>
              </div>
            `
          }
        })

        const alertParams = params.filter((p: any) => p.seriesType === 'scatter' && p.value)
        if (alertParams.length > 0) {
          html += `<div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid ${dark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)'};">`
          html += `<div style="font-size: 12px; color: ${textColor}; margin-bottom: 4px;">${t('overview.priceChart.alert')}:</div>`

          alertParams.forEach((param: any) => {
            const alert = param.data._alert as TimeseriesPoint
            const color = ALERT_COLORS[alert.level as keyof typeof ALERT_COLORS]
            html += `
              <div style="display: flex; align-items: center; gap: 8px; margin: 2px 0;">
                <span style="display: inline-block; width: 10px; height: 10px; background: ${color}; border-radius: 50%;"></span>
                <span style="font-size: 12px;">${t('risk.level.' + alert.level)}: ${alert.riskIndex.toFixed(1)}</span>
              </div>
            `
          })
          html += '</div>'
        }

        return html
      },
    },
    legend: {
      data: [
        t('overview.priceChart.oilPrice'),
        t('overview.priceChart.riskIndex'),
        t('risk.level.Low'),
        t('risk.level.Medium'),
        t('risk.level.High'),
      ],
      textStyle: { color: textColor, fontSize: 11 },
      top: 0,
      itemGap: 15,
    },
    grid: {
      left: '3%',
      right: '3%',
      top: 50,
      bottom: 80,
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: props.dates,
      axisLine: { lineStyle: { color: axisLineColor } },
      axisLabel: {
        color: textColor,
        fontSize: 10,
        rotate: 30,
        formatter: (value: string) => {
          const d = new Date(value)
          if (isNaN(d.getTime())) return value
          const granularity = getTimeGranularity()
          if (granularity === 'day') {
            return `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
          }
          if (granularity === 'month') {
            return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
          }
          return `${d.getFullYear()}`
        },
        interval: (index: number) => {
          if (index === 0) return true
          const curr = props.dates[index]
          const prev = props.dates[index - 1]
          if (!curr || !prev) return false
          const granularity = getTimeGranularity()
          if (granularity === 'day') {
            // 日粒度：每7天显示一个标签
            const currDate = new Date(curr)
            const prevDate = new Date(prev)
            return Math.abs(currDate.getTime() - prevDate.getTime()) >= 6 * 86400000
              || curr.slice(0, 7) !== prev.slice(0, 7)
          }
          if (granularity === 'month') {
            return curr.slice(0, 7) !== prev.slice(0, 7)
          }
          // 年粒度
          return new Date(curr).getFullYear() !== new Date(prev).getFullYear()
        },
      },
      axisTick: { alignWithLabel: true },
      boundaryGap: false,
    },
    yAxis: [
      {
        type: 'value',
        name: 'WTI ($)',
        position: 'left',
        nameTextStyle: { color: textColor, fontSize: 11 },
        axisLine: { show: false },
        axisLabel: { color: textColor, fontSize: 10 },
        splitLine: { lineStyle: { color: gridColor } },
      },
      {
        type: 'value',
        name: t('overview.priceChart.riskIndex'),
        position: 'right',
        min: 0,
        max: 100,
        nameTextStyle: { color: textColor, fontSize: 11 },
        axisLine: { show: false },
        axisLabel: { color: textColor, fontSize: 10 },
        splitLine: { show: false },
      },
    ],
    dataZoom: [
      {
        type: 'inside',
        start: visibleStart.value,
        end: visibleEnd.value,
      },
      {
        type: 'slider',
        start: visibleStart.value,
        end: visibleEnd.value,
        height: 25,
        bottom: 10,
        textStyle: { color: textColor },
        borderColor: axisLineColor,
        fillerColor: dark ? 'rgba(139, 92, 246, 0.2)' : 'rgba(139, 92, 246, 0.1)',
        handleStyle: {
          color: dark ? '#8b5cf6' : '#7c3aed',
        },
        dataBackground: {
          lineStyle: { color: axisLineColor },
          areaStyle: { color: gridColor },
        },
        selectedDataBackground: {
          lineStyle: { color: '#8b5cf6' },
          areaStyle: { color: 'rgba(139, 92, 246, 0.2)' },
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
        lineStyle: { width: 3, color: '#8b5cf6' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(139, 92, 246, 0.3)' },
            { offset: 1, color: 'rgba(139, 92, 246, 0)' },
          ]),
        },
        emphasis: { focus: 'series' },
      },
      {
        name: t('overview.priceChart.riskIndex'),
        type: 'line',
        yAxisIndex: 1,
        data: props.riskIndex,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2, color: '#fbbf24', type: 'dashed' },
        emphasis: { focus: 'series' },
      },
      {
        name: t('risk.level.Low'),
        type: 'scatter',
        yAxisIndex: 1,
        data: alertDataByLevel.value.Low,
        z: 10,
        itemStyle: { color: ALERT_COLORS.Low },
        emphasis: { focus: 'series', scale: 1.5 },
      },
      {
        name: t('risk.level.Medium'),
        type: 'scatter',
        yAxisIndex: 1,
        data: alertDataByLevel.value.Medium,
        z: 11,
        itemStyle: { color: ALERT_COLORS.Medium },
        emphasis: { focus: 'series', scale: 1.5 },
      },
      {
        name: t('risk.level.High'),
        type: 'scatter',
        yAxisIndex: 1,
        data: alertDataByLevel.value.High,
        z: 12,
        itemStyle: { color: ALERT_COLORS.High },
        emphasis: { focus: 'series', scale: 1.5 },
      },
    ],
  }
}

let updatingFromZoom = false

function initChart() {
  if (!chartRef.value) return
  chart = echarts.init(chartRef.value)
  chart.setOption(getOption(), { notMerge: false })

  chart.on('click', (params: any) => {
    if (params.seriesType === 'scatter' && params.data._alert) {
      emit('selectAlert', params.data._alert)
    }
  })

  // 监听缩放事件，自适应标签粒度
  chart.on('datazoom', () => {
    if (updatingFromZoom) return
    const opt = chart?.getOption() as any
    if (opt?.dataZoom?.[0]) {
      visibleStart.value = opt.dataZoom[0].start ?? 80
      visibleEnd.value = opt.dataZoom[0].end ?? 100
    }
    updatingFromZoom = true
    updateChart()
    updatingFromZoom = false
  })
}

function updateChart() {
  if (!chart) return
  chart.setOption(getOption(), { notMerge: false })
}

function handleResize() {
  chart?.resize()
}

watch(
  [() => props.dates, () => props.oilPrice, () => props.riskIndex, () => props.alerts, isDark],
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
  <div ref="chartRef" class="price-risk-alert-chart"></div>
</template>

<style scoped>
.price-risk-alert-chart {
  width: 100%;
  height: 100%;
  min-height: 400px;
}
</style>
