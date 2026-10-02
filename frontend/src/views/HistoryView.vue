<template>
  <div>
    <el-card shadow="hover">
      <template #header>
        <div class="header-bar">
          <b>环境数据历史趋势</b>
          <el-radio-group v-model="hours" @change="loadData">
            <el-radio-button :value="1">1小时</el-radio-button>
            <el-radio-button :value="6">6小时</el-radio-button>
            <el-radio-button :value="24">24小时</el-radio-button>
            <el-radio-button :value="72">3天</el-radio-button>
          </el-radio-group>
        </div>
      </template>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="温度 / 湿度" name="temp">
          <div ref="chart1" class="chart"></div>
        </el-tab-pane>
        <el-tab-pane label="光照 / 空气" name="air">
          <div ref="chart2" class="chart"></div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { nextTick, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { getHistoryData } from '../api'

const hours = ref(24)
const activeTab = ref('temp')
const chart1 = ref(null)
const chart2 = ref(null)
let charts = {}

function fmtTime(s) {
  const d = new Date(s)
  return d.toLocaleTimeString('zh-CN', { hour12: false })
}

function renderCharts(records) {
  const times = records.map(r => fmtTime(r.report_time))
  const tempData = records.map(r => r.temp)
  const humiData = records.map(r => r.humidity)
  const luxData = records.map(r => r.lux)
  const airData = records.map(r => r.air)

  charts.chart1?.dispose()
  charts.chart2?.dispose()

  charts.chart1 = echarts.init(chart1.value)
  charts.chart1.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['温度(℃)', '湿度(%)'] },
    grid: { left: 50, right: 30, top: 50, bottom: 40 },
    xAxis: { type: 'category', data: times, axisLabel: { interval: 'auto', rotate: 30 } },
    yAxis: { type: 'value' },
    series: [
      { name: '温度(℃)', type: 'line', data: tempData, smooth: true, lineStyle: { color: '#f56c6c' }, itemStyle: { color: '#f56c6c' } },
      { name: '湿度(%)', type: 'line', data: humiData, smooth: true, lineStyle: { color: '#409eff' }, itemStyle: { color: '#409eff' } },
    ],
  })

  charts.chart2 = echarts.init(chart2.value)
  charts.chart2.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['光照(lx)', '空气(ADC)'] },
    grid: { left: 50, right: 30, top: 50, bottom: 40 },
    xAxis: { type: 'category', data: times, axisLabel: { interval: 'auto', rotate: 30 } },
    yAxis: { type: 'value' },
    series: [
      { name: '光照(lx)', type: 'line', data: luxData, smooth: true, lineStyle: { color: '#e6a23c' }, itemStyle: { color: '#e6a23c' } },
      { name: '空气(ADC)', type: 'line', data: airData, smooth: true, lineStyle: { color: '#67c23a' }, itemStyle: { color: '#67c23a' } },
    ],
  })
}

async function loadData() {
  try {
    const res = await getHistoryData(hours.value)
    await nextTick()
    renderCharts(res.data)
  } catch (e) { /* 忽略 */ }
}

onMounted(loadData)
</script>

<style scoped>
.header-bar { display: flex; justify-content: space-between; align-items: center; }
.chart { width: 100%; height: 420px; }
</style>
