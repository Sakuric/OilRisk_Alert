<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { useI18n } from 'vue-i18n'
import type { RadarScore } from '@/types/factor'

const props = defineProps<{
  data: RadarScore[]
  theme: 'dark' | 'light'
  locale: 'zh' | 'en'
}>()

const { t } = useI18n()
const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

const categoryKeys = ['SUPPLY_DEMAND', 'MACRO', 'FINANCIAL', 'GEOPOLITICAL', 'SENTIMENT'] as const
const categoryI18nMap: Record<string, string> = {
  SUPPLY_DEMAND: 'Supply-Demand',
  MACRO: 'Macro',
  FINANCIAL: 'Financial',
  GEOPOLITICAL: 'Geopolitical',
  SENTIMENT: 'Sentiment',
}

function getOption(): echarts.EChartsOption {
  const isDark = props.theme === 'dark'
  const accentColor = '#8b5cf6'
  const axisColor = isDark ? 'rgba(139, 92, 246, 0.15)' : 'rgba(0, 0, 0, 0.08)'
  const textColor = isDark ? '#b0b3d0' : '#4a4d6a'

  const labels = categoryKeys.map((key) => t(`factor.category.${categoryI18nMap[key]}`))
  const values = categoryKeys.map((key) => {
    const item = props.data.find((d) => d.category === key)
    return item?.score ?? 0
  })

  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: isDark ? 'rgba(8, 11, 26, 0.95)' : 'rgba(255, 255, 255, 0.98)',
      borderColor: isDark ? 'rgba(139, 92, 246, 0.3)' : 'rgba(0, 0, 0, 0.1)',
      textStyle: { color: isDark ? '#f1f1f8' : '#1a1a2e', fontSize: 12 },
      extraCssText: 'max-width: 340px;',
      formatter: (params: unknown) => {
        const p = params as { value: number[] }
        let html = ''
        categoryKeys.forEach((key, idx) => {
          const label = labels[idx]
          const score = p.value[idx]
          const radarItem = props.data.find((d) => d.category === key)
          const top3 = (radarItem?.topFactors ?? [])
            .sort((a, b) => Math.abs(b.shap) - Math.abs(a.shap))
            .slice(0, 3)

          html += `<div style="margin-bottom:6px"><b>${label}</b>: ${score.toFixed(1)}`
          top3.forEach((f) => {
            const name = props.locale === 'zh' ? f.nameZh : f.name
            const shapVal = f.shap >= 0 ? `+${f.shap.toFixed(3)}` : f.shap.toFixed(3)
            const color = f.shap >= 0 ? '#4A90D9' : '#E74C3C'
            html += `<br/><span style="margin-left:8px;color:${color}">${name} ${shapVal}</span>`
          })
          html += '</div>'
        })
        return html
      },
    },
    radar: {
      indicator: labels.map((name) => ({ name, max: 100 })),
      axisLine: { lineStyle: { color: axisColor } },
      splitLine: { lineStyle: { color: axisColor } },
      splitArea: { show: false },
      axisName: {
        color: textColor,
        fontSize: 11,
        fontWeight: 'bold'
      },
      center: ['50%', '50%'],
      radius: '65%'
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: values,
            name: t('factorAnalysis.radarTitle'),
            areaStyle: {
              color: 'rgba(139, 92, 246, 0.2)',
            },
            lineStyle: {
              color: accentColor,
              width: 2,
              shadowBlur: 10,
              shadowColor: accentColor
            },
            itemStyle: {
              color: accentColor,
            },
            symbol: 'circle',
            symbolSize: 4
          },
        ],
        animationDuration: 800,
        animationEasing: 'cubicOut',
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
  chart.setOption(getOption())
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
