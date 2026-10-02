<template>
  <div>
    <!-- 四个数据卡片 -->
    <el-row :gutter="20">
      <el-col :span="6" v-for="card in cards" :key="card.key">
        <el-card class="data-card" shadow="hover">
          <div class="card-label">{{ card.label }}</div>
          <div class="card-value" :style="{ color: card.color }">
            {{ card.value }} <span class="unit">{{ card.unit }}</span>
          </div>
          <div class="card-status">{{ card.status }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 设备状态 + 继电器状态 -->
    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><b>继电器状态（本地自动控制）</b></template>
          <div class="relay-status">
            <el-tag :type="relayOn ? 'warning' : 'info'" size="large">
              {{ relayOn ? '🔴 继电器已开启（通风散热中）' : '⚪ 继电器关闭（环境正常）' }}
            </el-tag>
            <div class="status-text">{{ controlStatus }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><b>最后更新时间</b></template>
          <div class="last-time">{{ lastUpdate }}</div>
          <el-alert
            v-if="warningMsg"
            :title="warningMsg"
            type="warning"
            show-icon
            :closable="false"
            style="margin-top: 12px"
          />
          <el-alert
            v-else
            title="车间环境正常"
            type="success"
            show-icon
            :closable="false"
            style="margin-top: 12px"
          />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { getLatestData } from '../api'

const latest = ref({})
let timer = null

const cards = computed(() => [
  { key: 'temp', label: '车间温度', value: format(latest.value.temp), unit: '℃',
    color: '#f56c6c', status: tempStatus },
  { key: 'humidity', label: '车间湿度', value: format(latest.value.humidity), unit: '%',
    color: '#409eff', status: '目标 40-70%' },
  { key: 'lux', label: '光照强度', value: format(latest.value.lux), unit: 'lx',
    color: '#e6a23c', status: '光照环境' },
  { key: 'air', label: '空气质量', value: format(latest.value.air), unit: 'ADC',
    color: '#67c23a', status: airStatus },
])

const tempStatus = computed(() =>
  latest.value.temp > 35 ? '⚠ 温度过高' : '正常')
const airStatus = computed(() =>
  latest.value.air > 400 ? '⚠ 空气较差' : '正常')

const relayOn = computed(() => Boolean(latest.value.relay))
const controlStatus = computed(() => {
  const map = {
    normal: '环境正常，无需干预',
    temp_alarm: '温度超标，本地已自动开启风扇',
    air_alarm: '空气质量超标，本地已自动开启排风',
  }
  return map[latest.value.status] || '未知状态'
})
const warningMsg = computed(() => {
  if (latest.value.status === 'temp_alarm') return '⚠ 温度过高告警，已自动开启风扇'
  if (latest.value.status === 'air_alarm') return '⚠ 空气质量告警，已自动开启排风'
  return ''
})
const lastUpdate = computed(() =>
  latest.value.report_time ? formatTime(latest.value.report_time) : '暂无数据')

function format(v) { return v === null || v === undefined ? '--' : v }
function formatTime(s) { return s ? s.replace('T', ' ').slice(0, 19) : '--' }

async function refresh() {
  try {
    const res = await getLatestData()
    latest.value = res.data
  } catch (e) { /* 忽略 */ }
}

onMounted(() => {
  refresh()
  timer = setInterval(refresh, 5000) // 每 5 秒刷新
})
onUnmounted(() => { if (timer) clearInterval(timer) })
</script>

<style scoped>
.data-card { text-align: center; }
.card-label { color: #666; font-size: 14px; }
.card-value { font-size: 40px; font-weight: 700; margin: 12px 0; }
.unit { font-size: 16px; font-weight: 400; }
.card-status { color: #999; font-size: 12px; }
.relay-status { text-align: center; }
.status-text { margin-top: 12px; color: #666; }
.last-time { font-size: 18px; font-weight: 600; }
</style>
