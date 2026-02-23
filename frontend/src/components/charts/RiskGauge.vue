<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, computed } from 'vue'
import * as echarts from 'echarts'
import { useTheme } from '@/composables/useTheme'
import { useI18n } from 'vue-i18n'
import type { RiskLevel } from '@/types/risk'

const props = defineProps<{
  riskIndex: number
  riskLevel: RiskLevel
}>()

const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null
const { echartsThemeConfig, isDark } = useTheme()
const { t } = useI18n()

const riskColor = computed(() => {
  if (props.riskIndex < 40) return isDark.value ? '#3fb950' : '#1a7f37'
  if (props.riskIndex < 70) return isDark.value ? '#d29922' : '#bf8700'
  return isDark.value ? '#f85149' : '#cf222e'
})

function getOption(): echarts.EChartsOption {
  const themeOpts = echartsThemeConfig.value
  return {
    ...themeOpts,
    animationDuration: 800,
    animationEasing: 'cubicOut',
    series: [
      {
        type: 'gauge',
        startAngle: 220,
        endAngle: -40,
        min: 0,
        max: 100,
        radius: '90%',
        progress: {
          show: true,
          width: 18,
          roundCap: true,
          itemStyle: {
            color: riskColor.value,
          },
        },
        pointer: { show: false },
        axisLine: {
          lineStyle: {
            width: 18,
            color: [[1, isDark.value ? '#21262d' : '#eaeef2']],
          },
          roundCap: true,
        },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        anchor: { show: false },
        title: {
          show: true,
          offsetCenter: [0, '65%'],
          fontSize: 14,
          color: isDark.value ? '#8b949e' : '#57606a',
        },
        detail: {
          valueAnimation: true,
          fontSize: 40,
          fontWeight: 'bold',
          offsetCenter: [0, '15%'],
          color: riskColor.value,
          formatter: '{value}',
        },
        data: [
          {
            value: props.riskIndex,
            name: t(`risk.level.${props.riskLevel}`),
          },
        ],
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

watch(() => [props.riskIndex, props.riskLevel, isDark.value], updateChart)

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
  <div ref="chartRef" class="risk-gauge-chart"></div>
</template>

<style scoped>
.risk-gauge-chart {
  width: 100%;
  height: 100%;
  min-height: 260px;
}
</style>
