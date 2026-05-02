"""Template HTML de /admin/system-health · dashboard ejecutivo del CEO.

Una sola pantalla. Consume /api/admin/health-detailed. Auto-refresh cada 60s.
Diseño tipo cockpit: semáforos por sección + acción inmediata si algo está rojo.
"""

SYSTEM_HEALTH_HTML = r'''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>System Health · HHA Group</title>
<style>
  * { box-sizing: border-box; }
  body {
    margin: 0; font-family: -apple-system, "Segoe UI", Roboto, sans-serif;
    background: #0f172a; color: #e2e8f0; min-height: 100vh; padding: 20px;
  }
  .container { max-width: 1200px; margin: 0 auto; }
  .topbar {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 24px; padding-bottom: 14px; border-bottom: 1px solid #1e293b;
  }
  .topbar h1 { font-size: 22px; margin: 0; color: #fff; }
  .topbar .meta { font-size: 12px; color: #64748b; }
  .meta b { color: #cbd5e1; }
  .overall {
    display: inline-block; padding: 6px 14px; border-radius: 6px;
    font-weight: 700; font-size: 13px;
  }
  .ok    { background: #064e3b; color: #6ee7b7; }
  .warn  { background: #78350f; color: #fcd34d; }
  .err   { background: #7f1d1d; color: #fca5a5; }
  .grid {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 14px;
  }
  .card {
    background: #1e293b; border: 1px solid #334155; border-radius: 10px;
    padding: 16px; transition: transform 0.1s ease;
  }
  .card.error    { border-left: 4px solid #ef4444; }
  .card.warning  { border-left: 4px solid #f59e0b; }
  .card.ok       { border-left: 4px solid #22c55e; }
  .card-head {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 10px;
  }
  .card-title {
    font-size: 14px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.4px; color: #cbd5e1;
  }
  .badge {
    font-size: 10px; padding: 3px 8px; border-radius: 4px;
    font-weight: 700; letter-spacing: 0.3px;
  }
  .badge.ok    { background: #14532d; color: #86efac; }
  .badge.warn  { background: #713f12; color: #fde68a; }
  .badge.err   { background: #7f1d1d; color: #fecaca; }
  .stats {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(80px, 1fr));
    gap: 8px; font-size: 13px;
  }
  .stats .stat-row {
    display: flex; justify-content: space-between; padding: 4px 0;
    border-bottom: 1px solid #283347; font-size: 12px;
  }
  .stats .stat-row b { color: #f1f5f9; }
  .stats .stat-row.warn b { color: #fcd34d; }
  .stats .stat-row.err  b { color: #fca5a5; }
  .hint {
    margin-top: 10px; padding: 8px 10px; background: #0f172a;
    border-radius: 6px; font-size: 11px; color: #fcd34d; line-height: 1.5;
  }
  .hint.err { color: #fca5a5; }
  .footer { margin-top: 22px; text-align: center; color: #475569; font-size: 11px; }
  button.refresh {
    background: #3b82f6; color: #fff; border: none; padding: 8px 16px;
    border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 12px;
  }
  button.refresh:hover { background: #2563eb; }
  .spinner {
    display: inline-block; width: 14px; height: 14px;
    border: 2px solid #334155; border-top-color: #3b82f6;
    border-radius: 50%; animation: spin 0.8s linear infinite;
    margin-right: 6px; vertical-align: middle;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .empty { color: #64748b; font-size: 12px; font-style: italic; padding: 12px 0; }
  .nav { font-size: 12px; }
  .nav a { color: #7ACFCC; text-decoration: none; margin-right: 14px; }
  .nav a:hover { text-decoration: underline; }
  code { background: #0f172a; padding: 2px 6px; border-radius: 3px; font-size: 11px; }
</style>
</head>
<body>
<div class="container">
  <div class="topbar">
    <div>
      <h1 id="pageTitle">System Health Cockpit</h1>
      <div class="nav">
        <a href="/gerencia">Gerencia</a>
        <a href="/aseguramiento">Aseguramiento</a>
        <a href="/compras">Compras</a>
        <a href="/admin/audit-inventario">Admin</a>
      </div>
    </div>
    <div style="text-align:right">
      <div id="overallPill" class="overall ok">cargando…</div>
      <div class="meta" style="margin-top:6px">
        commit <b id="commit">—</b> · <span id="ts">—</span>
        &nbsp; <button class="refresh" onclick="loadHealth()">↻ Refresh</button>
      </div>
    </div>
  </div>

  <div id="grid" class="grid">
    <div class="card"><div class="empty"><span class="spinner"></span> Cargando salud del sistema…</div></div>
  </div>

  <div class="footer">
    Auto-refresh cada 60 segundos · Endpoint: <code>/api/admin/health-detailed</code>
  </div>
</div>

<script>
const SECTION_LABELS = {
  migrations: '🗃️ Migraciones DB',
  indexes: '🔍 Índices',
  helpers: '🧰 Helpers globales',
  crons: '⏰ Cron jobs registrados',
  audit_log: '📜 Audit log (7d)',
  asg_workflows: '📋 Workflows ASG',
  backups: '💾 Backups',
  sentry: '🚨 Sentry',
  invima: '🏛️ Registros INVIMA',
  recalls: '⚠️ Recalls activos',
  cuarentena: '⏳ Lotes en cuarentena',
  liberacion_pt: '✅ Liberación PT pendiente',
  hallazgos_vencidos: '❌ Hallazgos vencidos',
  caja: '💰 Caja vs commitments',
  salas: '🏭 Salas planta',
  mfa_admins: '🔐 MFA admins',
};

const SECTION_ORDER = [
  'invima', 'recalls', 'hallazgos_vencidos', 'cuarentena', 'liberacion_pt',
  'caja', 'salas', 'audit_log', 'backups', 'mfa_admins',
  'migrations', 'indexes', 'helpers', 'crons', 'asg_workflows', 'sentry',
];

function _esc(s){
  return String(s||'').replace(/[&<>"']/g, ch => (
    {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]
  ));
}

function fmt(v) {
  if (v === null || v === undefined) return '—';
  if (typeof v === 'boolean') return v ? '✓ sí' : '✗ no';
  if (typeof v === 'number') {
    if (Math.abs(v) >= 1000) return v.toLocaleString('es-CO');
    return String(v);
  }
  if (Array.isArray(v)) return v.length === 0 ? '(vacío)' : v.join(', ');
  return String(v);
}

function classFor(status) {
  if (status === 'error') return 'err';
  if (status === 'warning') return 'warn';
  return 'ok';
}

function buildCard(key, data) {
  const st = (data && data.status) || 'ok';
  const cls = st === 'error' ? 'error' : (st === 'warning' ? 'warning' : 'ok');
  const badgeCls = classFor(st);
  const label = SECTION_LABELS[key] || key;

  // Filtrar campos meta que no se muestran como rows
  const skipKeys = new Set(['status', 'hint', 'detail']);
  const rows = [];
  if (data && typeof data === 'object') {
    for (const [k, v] of Object.entries(data)) {
      if (skipKeys.has(k)) continue;
      let rowCls = '';
      if (st === 'error') rowCls = 'err';
      else if (st === 'warning' && (
        k.includes('vencidos') || k.includes('atrasados') || k.includes('sin_') ||
        k.includes('missing') || k.includes('clase_I')
      )) rowCls = 'warn';
      rows.push(`<div class="stat-row ${rowCls}"><span>${_esc(k)}</span><b>${_esc(fmt(v))}</b></div>`);
    }
  }

  let body = rows.join('') || '<div class="empty">Sin datos</div>';
  if (data && data.detail) {
    body += `<div class="hint err">${_esc(data.detail)}</div>`;
  }
  if (data && data.hint) {
    body += `<div class="hint ${st === 'error' ? 'err' : ''}">${_esc(data.hint)}</div>`;
  }

  return `
    <div class="card ${cls}">
      <div class="card-head">
        <div class="card-title">${_esc(label)}</div>
        <span class="badge ${badgeCls}">${_esc(st.toUpperCase())}</span>
      </div>
      <div class="stats">${body}</div>
    </div>`;
}

async function loadHealth() {
  const grid = document.getElementById('grid');
  grid.innerHTML = '<div class="card"><div class="empty"><span class="spinner"></span> Consultando…</div></div>';
  try {
    const r = await fetch('/api/admin/health-detailed');
    if (!r.ok) {
      const err = await r.text();
      grid.innerHTML = `<div class="card error"><div class="card-title">Error ${r.status}</div><div class="hint err">${_esc(err.slice(0,200))}</div></div>`;
      return;
    }
    const d = await r.json();

    // Topbar metadata
    document.getElementById('commit').textContent = d.commit || '—';
    document.getElementById('ts').textContent = (d.timestamp || '').slice(0, 19).replace('T', ' ') + ' UTC';
    const overall = d.overall || 'ok';
    const pill = document.getElementById('overallPill');
    pill.className = 'overall ' + (overall === 'ok' ? 'ok' : (overall === 'error' ? 'err' : 'warn'));
    pill.textContent = overall.toUpperCase();

    // Update page title to reflect status (so the browser tab shows urgency)
    document.title = (overall === 'ok' ? '🟢' : '🔴') + ' System Health · HHA';

    const sections = d.sections || {};
    const cards = [];
    // Render in operational priority order, then any extra sections
    for (const key of SECTION_ORDER) {
      if (sections[key] !== undefined) {
        cards.push(buildCard(key, sections[key]));
      }
    }
    for (const [k, v] of Object.entries(sections)) {
      if (!SECTION_ORDER.includes(k)) cards.push(buildCard(k, v));
    }
    grid.innerHTML = cards.join('');
  } catch (e) {
    grid.innerHTML = `<div class="card error"><div class="card-title">Error de red</div><div class="hint err">${_esc(e.message)}</div></div>`;
  }
}

loadHealth();
setInterval(loadHealth, 60000);
</script>
</body>
</html>'''
