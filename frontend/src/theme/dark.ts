import type { EChartsOption } from 'echarts'

const darkTheme: EChartsOption = {
  backgroundColor: 'transparent',
  textStyle: {
    color: '#e6edf3',
  },
  title: {
    textStyle: {
      color: '#e6edf3',
    },
  },
  legend: {
    textStyle: {
      color: '#8b949e',
    },
  },
  tooltip: {
    backgroundColor: '#1c2128',
    borderColor: '#30363d',
    textStyle: {
      color: '#e6edf3',
    },
  },
  xAxis: {
    axisLine: { lineStyle: { color: '#30363d' } },
    axisTick: { lineStyle: { color: '#30363d' } },
    axisLabel: { color: '#8b949e' },
    splitLine: { lineStyle: { color: '#21262d' } },
  },
  yAxis: {
    axisLine: { lineStyle: { color: '#30363d' } },
    axisTick: { lineStyle: { color: '#30363d' } },
    axisLabel: { color: '#8b949e' },
    splitLine: { lineStyle: { color: '#21262d' } },
  },
  categoryAxis: {
    axisLine: { lineStyle: { color: '#30363d' } },
    axisTick: { lineStyle: { color: '#30363d' } },
    axisLabel: { color: '#8b949e' },
    splitLine: { lineStyle: { color: '#21262d' } },
  },
  valueAxis: {
    axisLine: { lineStyle: { color: '#30363d' } },
    axisTick: { lineStyle: { color: '#30363d' } },
    axisLabel: { color: '#8b949e' },
    splitLine: { lineStyle: { color: '#21262d' } },
  },
}

export default darkTheme
