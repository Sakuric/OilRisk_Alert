import type { EChartsOption } from 'echarts'

const lightTheme: EChartsOption = {
  backgroundColor: 'transparent',
  textStyle: {
    color: '#24292f',
  },
  title: {
    textStyle: {
      color: '#24292f',
    },
  },
  legend: {
    textStyle: {
      color: '#57606a',
    },
  },
  tooltip: {
    backgroundColor: '#ffffff',
    borderColor: '#d0d7de',
    textStyle: {
      color: '#24292f',
    },
  },
  xAxis: {
    axisLine: { lineStyle: { color: '#d0d7de' } },
    axisTick: { lineStyle: { color: '#d0d7de' } },
    axisLabel: { color: '#57606a' },
    splitLine: { lineStyle: { color: '#eaeef2' } },
  },
  yAxis: {
    axisLine: { lineStyle: { color: '#d0d7de' } },
    axisTick: { lineStyle: { color: '#d0d7de' } },
    axisLabel: { color: '#57606a' },
    splitLine: { lineStyle: { color: '#eaeef2' } },
  },
  categoryAxis: {
    axisLine: { lineStyle: { color: '#d0d7de' } },
    axisTick: { lineStyle: { color: '#d0d7de' } },
    axisLabel: { color: '#57606a' },
    splitLine: { lineStyle: { color: '#eaeef2' } },
  },
  valueAxis: {
    axisLine: { lineStyle: { color: '#d0d7de' } },
    axisTick: { lineStyle: { color: '#d0d7de' } },
    axisLabel: { color: '#57606a' },
    splitLine: { lineStyle: { color: '#eaeef2' } },
  },
}

export default lightTheme
