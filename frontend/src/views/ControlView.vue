<template>
  <div>
    <el-card shadow="hover">
      <template #header><b>远程控制（通过 OneNET 下发指令到 ESP32）</b></template>
      <div class="control-panel">
        <div class="control-btns">
          <el-button
            type="warning"
            size="large"
            :loading="sending"
            :disabled="relayOn"
            @click="send('relay_on')"
          >🔴 开启通风（继电器）</el-button>
          <el-button
            type="info"
            size="large"
            :loading="sending"
            :disabled="!relayOn"
            @click="send('relay_off')"
          >⚪ 关闭通风</el-button>
        </div>
        <el-alert
          :title="relayOn ? '继电器当前：开启' : '继电器当前：关闭'"
          :type="relayOn ? 'warning' : 'info'"
          show-icon
          :closable="false"
        />
      </div>
    </el-card>

    <el-card shadow="hover" style="margin-top: 20px">
      <template #header><b>控制日志</b></template>
      <el-table :data="logs" stripe style="width: 100%">
        <el-table-column label="指令" width="200">
          <template #default="{ row }">
            <el-tag :type="row.command === 'relay_on' ? 'warning' : 'info'">
              {{ row.command === 'relay_on' ? '开启通风' : '关闭通风' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="来源" width="120">
          <template #default="{ row }">
            <el-tag :type="row.source === 'auto' ? 'success' : 'primary'" effect="plain">
              {{ row.source === 'auto' ? '本地自动' : '云端远程' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="时间">
          <template #default="{ row }">{{ fmtTime(row.created_at) }}</template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getLatestData, getControlLogs, sendControl } from '../api'

const sending = ref(false)
const latest = ref({})
const logs = ref([])
const relayOn = computed(() => Boolean(latest.value.relay))
const fmtTime = (s) => s ? s.replace('T', ' ').slice(0, 19) : '--'

let timer = null

async function loadLatest() {
  try {
    const res = await getLatestData()
    latest.value = res.data
  } catch (e) { /* 忽略 */ }
}

async function loadLogs() {
  try {
    const res = await getControlLogs()
    logs.value = res.data
  } catch (e) { /* 忽略 */ }
}

async function send(command) {
  sending.value = true
  try {
    const res = await sendControl(command)
    if (res.data.success) {
      ElMessage.success(command === 'relay_on' ? '指令已下发，继电器已开启' : '指令已下发，继电器已关闭')
    } else {
      ElMessage.error(res.data.message || '下发失败')
    }
  } catch (e) {
    ElMessage.error('请求失败，请检查后端服务')
  } finally {
    sending.value = false
    loadLatest()
    loadLogs()
  }
}

onMounted(() => {
  loadLatest()
  loadLogs()
  timer = setInterval(loadLatest, 5000)
})
onUnmounted(() => { if (timer) clearInterval(timer) })
</script>

<style scoped>
.control-panel { text-align: center; padding: 20px 0; }
.control-btns { margin-bottom: 20px; }
.control-btns .el-button { margin: 0 15px; }
</style>
