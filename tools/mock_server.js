/**
 * 车间环境智能监测与控制系统 —— 演示用模拟数据服务
 *
 * 用途：在没有 Python 后端 / 没有 ESP32 硬件 / 没有 OneNET 账号的情况下，
 *      生成模拟数据，让 Web 看板能够正常预览和演示。
 *
 * 启动：node tools/mock_server.js      （监听 8000 端口，与前端 vite 代理配置一致）
 * 注意：正式部署时应启动 backend 里的 FastAPI 服务，本文件仅用于预览/演示。
 */

const http = require('http');

const PORT = 8000;

// ---------------- 工具函数 ----------------
function fmtTime(ms) {
  // 输出 "2026-09-17T10:30:00" 格式，与后端 datetime 序列化格式一致
  const d = new Date(ms);
  const p = (n) => String(n).padStart(2, '0');
  return (
    d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate()) +
    'T' + p(d.getHours()) + ':' + p(d.getMinutes()) + ':' + p(d.getSeconds())
  );
}

// ---------------- 生成 24 小时历史数据（每 5 分钟一条） ----------------
function genHistory() {
  const list = [];
  const now = Date.now();
  const step = 5 * 60 * 1000;
  let id = 1;

  for (let t = now - 24 * 3600 * 1000; t <= now; t += step) {
    const h = new Date(t).getHours();
    // 昼高夜低的温度曲线
    const dayFactor = Math.sin(((h - 6) / 24) * Math.PI * 2);

    let temp = 29 + dayFactor * 6.5 + (Math.random() - 0.5) * 1.6;
    temp = Math.round(temp * 10) / 10;

    let humidity = 55 - dayFactor * 24 + (Math.random() - 0.5) * 5;
    humidity = Math.round(humidity * 10) / 10;
    if (humidity < 0) humidity = 0;

    let lux = Math.round(380 + dayFactor * 320 + (Math.random() - 0.5) * 60);
    if (lux < 0) lux = 0;

    let air = Math.round(180 + dayFactor * 220 + (Math.random() - 0.5) * 80);
    if (air < 0) air = 0;

    let relay = false;
    let status = 'normal';
    if (temp > 35) {
      relay = true;
      status = 'temp_alarm';
    } else if (air > 400) {
      relay = true;
      status = 'air_alarm';
    }

    list.push({
      id: id++,
      temp: temp,
      humidity: humidity,
      lux: lux,
      air: air,
      relay: relay,
      status: status,
      report_time: fmtTime(t),
    });
  }
  return list;
}

let history = genHistory();

// ---------------- 由历史数据推导告警记录 ----------------
let alerts = [];
(function buildAlerts() {
  const open = {}; // 记录各类型是否已有未解决告警
  for (const row of history) {
    const rules = [];
    if (row.temp > 35) rules.push(['high_temp', row.temp, 35.0]);
    if (row.humidity < 30) rules.push(['low_humidity', row.humidity, 30.0]);
    if (row.air > 400) rules.push(['high_air', row.air, 400]);

    if (rules.length === 0) {
      // 环境恢复正常，允许后续再次触发
      Object.keys(open).forEach((k) => delete open[k]);
      continue;
    }
    for (const rule of rules) {
      const type = rule[0];
      if (open[type]) continue;
      if (alerts.length >= 10) continue;
      alerts.push({
        id: alerts.length + 1,
        alert_type: type,
        alert_value: rule[1],
        threshold: rule[2],
        status: 'triggered',
        triggered_at: row.report_time,
        resolved_at: null,
      });
      open[type] = true;
    }
  }
  // 把较早的几条标记为已解决，便于展示两种状态
  alerts.slice(0, Math.max(0, alerts.length - 2)).forEach((a) => {
    a.status = 'resolved';
    a.resolved_at = a.triggered_at;
  });
})();

// ---------------- 控制日志 ----------------
let controlLogs = [
  { id: 1, command: 'relay_on', source: 'auto', created_at: fmtTime(Date.now() - 6 * 3600 * 1000) },
  { id: 2, command: 'relay_off', source: 'auto', created_at: fmtTime(Date.now() - 5.5 * 3600 * 1000) },
  { id: 3, command: 'relay_on', source: 'cloud', created_at: fmtTime(Date.now() - 3 * 3600 * 1000) },
  { id: 4, command: 'relay_off', source: 'cloud', created_at: fmtTime(Date.now() - 2.8 * 3600 * 1000) },
  { id: 5, command: 'relay_on', source: 'auto', created_at: fmtTime(Date.now() - 40 * 60 * 1000) },
];

// ---------------- 路由处理 ----------------
function send(res, code, obj) {
  const body = JSON.stringify(obj);
  res.writeHead(code, {
    'Content-Type': 'application/json; charset=utf-8',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
    'Access-Control-Allow-Headers': '*',
  });
  res.end(body);
}

const server = http.createServer((req, res) => {
  const url = req.url.split('?')[0];
  const query = new URLSearchParams(req.url.split('?')[1] || '');

  if (req.method === 'OPTIONS') {
    return send(res, 200, {});
  }

  // 设备状态
  if (url === '/api/device/status') {
    const last = history[history.length - 1];
    return send(res, 200, {
      id: 1,
      device_name: 'env_monitor',
      status: 'online',
      last_report: last.report_time,
    });
  }

  // 最新数据
  if (url === '/api/data/latest') {
    return send(res, 200, history[history.length - 1]);
  }

  // 历史数据
  if (url === '/api/data/history') {
    const hours = parseInt(query.get('hours') || '24', 10);
    const since = Date.now() - hours * 3600 * 1000;
    const rows = history.filter((r) => new Date(r.report_time).getTime() >= since);
    return send(res, 200, rows);
  }

  // 告警列表
  if (url === '/api/alerts' && req.method === 'GET') {
    const status = query.get('status') || '';
    const rows = status ? alerts.filter((a) => a.status === status) : alerts;
    return send(res, 200, rows.slice().reverse());
  }

  // 确认解决告警
  const m = url.match(/^\/api\/alerts\/(\d+)\/resolve$/);
  if (m && req.method === 'POST') {
    const id = parseInt(m[1], 10);
    const a = alerts.find((x) => x.id === id);
    if (a) {
      a.status = 'resolved';
      a.resolved_at = fmtTime(Date.now());
    }
    return send(res, 200, a || {});
  }

  // 控制日志
  if (url === '/api/control/logs') {
    const limit = parseInt(query.get('limit') || '50', 10);
    return send(res, 200, controlLogs.slice().reverse().slice(0, limit));
  }

  // 远程控制
  if (url === '/api/device/control' && req.method === 'POST') {
    let body = '';
    req.on('data', (c) => (body += c));
    req.on('end', () => {
      let cmd = 'relay_on';
      try {
        cmd = JSON.parse(body).command || cmd;
      } catch (e) { /* 忽略 */ }

      const on = cmd === 'relay_on';
      history[history.length - 1].relay = on;
      controlLogs.push({
        id: controlLogs.length + 1,
        command: cmd,
        source: 'cloud',
        created_at: fmtTime(Date.now()),
      });
      send(res, 200, { success: true, message: '指令已下发（模拟）' });
    });
    return;
  }

  send(res, 404, { detail: 'not found' });
});

server.listen(PORT, () => {
  console.log('[模拟服务] 已启动: http://localhost:' + PORT);
  console.log('[模拟服务] 提供 /api/device/status、/api/data/latest、/api/data/history、');
  console.log('           /api/alerts、/api/control/logs、/api/device/control');
});
