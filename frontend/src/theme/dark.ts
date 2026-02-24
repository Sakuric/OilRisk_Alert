import type { EChartsOption } from 'echarts'

const darkTheme: EChartsOption = {
  backgroundColor: 'transparent',
  textStyle: {
    color: '#f1f1f8',
  },
  title: {
    textStyle: {
      color: '#f1f1f8',
    },
  },
  legend: {
    textStyle: {
      color: '#b0b3d0',
    },
  },
  tooltip: {
    backgroundColor: 'rgba(8, 11, 26, 0.9)',
    borderColor: 'rgba(139, 92, 246, 0.2)',
    textStyle: {
      color: '#f1f1f8',
    },
  },
  xAxis: {
    axisLine: { lineStyle: { color: 'rgba(139, 92, 246, 0.15)' } },
    axisTick: { lineStyle: { color: 'rgba(139, 92, 246, 0.15)' } },
    axisLabel: { color: '#b0b3d0' },
    splitLine: { lineStyle: { color: 'rgba(139, 92, 246, 0.08)' } },
  },
  yAxis: {
    axisLine: { lineStyle: { color: 'rgba(139, 92, 246, 0.15)' } },
    axisTick: { lineStyle: { color: 'rgba(139, 92, 246, 0.15)' } },
    axisLabel: { color: '#b0b3d0' },
    splitLine: { lineStyle: { color: 'rgba(139, 92, 246, 0.08)' } },
  },
  categoryAxis: {
    axisLine: { lineStyle: { color: 'rgba(139, 92, 246, 0.15)' } },
    axisTick: { lineStyle: { color: 'rgba(139, 92, 246, 0.15)' } },
    axisLabel: { color: '#b0b3d0' },
    splitLine: { lineStyle: { color: 'rgba(139, 92, 246, 0.08)' } },
  },
  valueAxis: {
    axisLine: { lineStyle: { color: 'rgba(139, 92, 246, 0.15)' } },
    axisTick: { lineStyle: { color: 'rgba(139, 92, 246, 0.15)' } },
    axisLabel: { color: '#b0b3d0' },
    splitLine: { lineStyle: { color: 'rgba(139, 92, 246, 0.08)' } },
  },
}

export default darkTheme
