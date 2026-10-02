import axios from 'axios'

// 统一封装 axios，后端接口地址由 vite 代理到 /api
const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

// ============ 数据接口 ============
export const getDeviceStatus = () => api.get('/device/status')
export const getLatestData = () => api.get('/data/latest')
export const getHistoryData = (hours = 24) => api.get('/data/history', { params: { hours } })

// ============ 告警接口 ============
export const getAlerts = (status = '') => api.get('/alerts', { params: { status } })
export const resolveAlert = (id) => api.post(`/alerts/${id}/resolve`)

// ============ 控制接口 ============
export const sendControl = (command) => api.post('/device/control', { command, source: 'cloud' })
export const getControlLogs = (limit = 50) => api.get('/control/logs', { params: { limit } })

export default api
