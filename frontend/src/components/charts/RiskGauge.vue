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
  if (props.riskIndex < 40) return '#34d399'
  if (props.riskIndex < 70) return '#fbbf24'
  return '#f43f5e'
})

function getOption(): echarts.EChartsOption {
  const themeOpts = echartsThemeConfig.value
  return {
    backgroundColor: 'transparent',
    animationDuration: 1500,
    animationEasing: 'elasticOut',
    series: [
      {
        type: 'gauge',
        startAngle: 210,
        endAngle: -30,
        min: 0,
        max: 100,
        splitNumber: 10,
        radius: '100%',
        progress: {
          show: true,
          width: 12,
          roundCap: true,
          itemStyle: {
            color: riskColor.value,
            shadowBlur: 15,
            shadowColor: riskColor.value,
          },
        },
        pointer: {
          show: true,
          length: '60%',
          width: 4,
          itemStyle: {
            color: riskColor.value,
          },
        },
        axisLine: {
          lineStyle: {
            width: 12,
            color: [[1, 'rgba(139, 92, 246, 0.1)']],
          },
          roundCap: true,
        },
        axisTick: { show: false },
        splitLine: {
          show: true,
          length: 4,
          lineStyle: {
            width: 2,
            color: 'rgba(139, 92, 246, 0.2)',
          },
        },
        axisLabel: {
          show: true,
          distance: 20,
          color: 'var(--chart-text, rgba(176, 179, 208, 0.5))',
          fontSize: 10,
        },
        anchor: {
          show: true,
          showAbove: true,
          size: 15,
          itemStyle: {
            borderWidth: 3,
            borderColor: riskColor.value,
            color: '#080b1a',
          },
        },
        title: {
          show: true,
          offsetCenter: [0, '70%'],
          fontSize: 12,
          fontWeight: 'bold',
          color: riskColor.value,
          backgroundColor: 'rgba(255, 255, 255, 0.03)',
          borderRadius: 4,
          padding: [4, 8],
        },
        detail: {
          valueAnimation: true,
          fontSize: 36,
          fontWeight: '800',
          offsetCenter: [0, '25%'],
          color: '#fff',
          formatter: '{value}',
          fontFamily: 'Inter',
        },
        data: [
          {
            value: props.riskIndex,
            name: t(`risk.level.${props.riskLevel}`).toUpperCase(),
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
