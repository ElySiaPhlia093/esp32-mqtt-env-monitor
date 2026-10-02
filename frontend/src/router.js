import { createRouter, createWebHistory } from 'vue-router'
import DashboardView from './views/DashboardView.vue'
import HistoryView from './views/HistoryView.vue'
import AlertsView from './views/AlertsView.vue'
import ControlView from './views/ControlView.vue'

const routes = [
  { path: '/', redirect: '/dashboard' },
  { path: '/dashboard', name: 'dashboard', component: DashboardView, meta: { title: '实时概览' } },
  { path: '/history', name: 'history', component: HistoryView, meta: { title: '历史趋势' } },
  { path: '/alerts', name: 'alerts', component: AlertsView, meta: { title: '告警记录' } },
  { path: '/control', name: 'control', component: ControlView, meta: { title: '远程控制' } },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
