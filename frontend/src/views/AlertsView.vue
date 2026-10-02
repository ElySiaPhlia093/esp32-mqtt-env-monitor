<template>
  <div>
    <el-card shadow="hover">
      <template #header>
        <div class="header-bar">
          <b>告警记录</b>
          <el-radio-group v-model="filter" @change="loadData">
            <el-radio-button value="">全部</el-radio-button>
            <el-radio-button value="triggered">未解决</el-radio-button>
            <el-radio-button value="resolved">已解决</el-radio-button>
          </el-radio-group>
        </div>
      </template>

      <el-table :data="alerts" stripe style="width: 100%">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column label="告警类型" width="160">
          <template #default="{ row }">
            <el-tag :type="typeColor(row.alert_type)">{{ typeText(row.alert_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="alert_value" label="触发值" width="100" />
        <el-table-column prop="threshold" label="阈值" width="100" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'triggered' ? 'danger' : 'success'">
              {{ row.status === 'triggered' ? '未解决' : '已解决' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="触发时间">
          <template #default="{ row }">{{ fmtTime(row.triggered_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'triggered'"
              size="small"
              type="success"
              @click="handleResolve(row.id)"
            >确认解决</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getAlerts, resolveAlert } from '../api'

const alerts = ref([])
const filter = ref('')

const typeMap = {
  high_temp: { text: '温度过高', color: 'danger' },
  low_humidity: { text: '湿度过低', color: 'warning' },
  high_air: { text: '空气超标', color: 'danger' },
}
const typeText = (t) => typeMap[t]?.text || t
const typeColor = (t) => typeMap[t]?.color || 'info'
const fmtTime = (s) => s ? s.replace('T', ' ').slice(0, 19) : '--'

async function loadData() {
  try {
    const res = await getAlerts(filter.value)
    alerts.value = res.data
  } catch (e) { /* 忽略 */ }
}

async function handleResolve(id) {
  try {
    await resolveAlert(id)
    ElMessage.success('告警已解决')
    loadData()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

onMounted(loadData)
</script>

<style scoped>
.header-bar { display: flex; justify-content: space-between; align-items: center; }
</style>
