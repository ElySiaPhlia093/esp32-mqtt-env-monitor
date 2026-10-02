<template>
  <el-container class="layout">
    <el-aside width="220px" class="aside">
      <div class="logo">
        <h2>车间环境监测</h2>
        <p>智能监控系统</p>
      </div>
      <el-menu :default-active="activeMenu" router class="menu">
        <el-menu-item index="/dashboard">
          <el-icon><DataBoard /></el-icon>
          <span>实时概览</span>
        </el-menu-item>
        <el-menu-item index="/history">
          <el-icon><TrendCharts /></el-icon>
          <span>历史趋势</span>
        </el-menu-item>
        <el-menu-item index="/alerts">
          <el-icon><Warning /></el-icon>
          <span>告警记录</span>
        </el-menu-item>
        <el-menu-item index="/control">
          <el-icon><SwitchButton /></el-icon>
          <span>远程控制</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="page-title">{{ currentTitle }}</div>
        <el-tag v-if="deviceStatus" :type="deviceStatus === 'online' ? 'success' : 'danger'" size="large">
          {{ deviceStatus === 'online' ? '● 设备在线' : '○ 设备离线' }}
        </el-tag>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { DataBoard, TrendCharts, Warning, SwitchButton } from '@element-plus/icons-vue'
import { getDeviceStatus } from './api'

const route = useRoute()
const activeMenu = computed(() => route.path)
const currentTitle = computed(() => route.meta.title || '')

const deviceStatus = ref(null)
let timer = null

async function refreshStatus() {
  try {
    const res = await getDeviceStatus()
    deviceStatus.value = res.data.status
  } catch (e) {
    deviceStatus.value = 'offline'
  }
}

onMounted(() => {
  refreshStatus()
  timer = setInterval(refreshStatus, 10000) // 每 10 秒刷新在线状态
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: "Microsoft YaHei", sans-serif; background: #f0f2f5; }

.layout { height: 100vh; }
.aside { background: #001529; }
.logo { color: #fff; text-align: center; padding: 20px 0; }
.logo h2 { font-size: 18px; }
.logo p { font-size: 12px; color: #8c9bb5; margin-top: 4px; }
.menu { border-right: none; background: #001529; }
.menu .el-menu-item { color: #a6adb4; }
.menu .el-menu-item.is-active { color: #fff; background: #1677ff; }
.header {
  background: #fff;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
}
.page-title { font-size: 18px; font-weight: 600; }
.main { padding: 20px; overflow-y: auto; }
</style>
