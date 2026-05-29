"""Template HTML del módulo BRD (Batch Record Digital).

Sebastián 12-may-2026 · Fase 1 BRD UI v1 (read-only listings).

Pestañas:
- Dashboard BRD (KPIs · MBRs por estado, EBRs activos, alertas)
- MBR Templates (listado · click abre detalle con pasos)
- EBR Ejecuciones (listado · click abre detalle con pasos+IPCs+pesajes)
- Cleaning Log (listado por equipo)

Acciones (crear MBR, agregar paso, firmar, ejecutar, liberar, etc.) se
hacen vía endpoints API. Esta v1 es solo VISIBILIDAD — la creación se
hará en v2 cuando definamos el flujo UX con Calidad.
"""

BRD_HTML = r'''<!DOCTYPE html>
<html lang="es" translate="no">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Batch Record Digital · EOS</title>
<link rel="stylesheet" href="/static/cortex.css?v=eos15">
<style>
body{font-family:system-ui,-apple-system,sans-serif;background:#f8fafc;margin:0;color:#0f172a}
header{background:#0f172a;color:#f1f5f9;padding:14px 24px;display:flex;justify-content:space-between;align-items:center}
.logo{font-weight:800;letter-spacing:.5px;font-size:1.05em;color:#7ACFCC}
.tabs{display:flex;gap:0;background:#1e293b;border-bottom:1px solid #334155;padding:0 24px;flex-wrap:wrap}
.tab{padding:11px 20px;font-size:.78em;font-weight:700;letter-spacing:.5px;color:#64748b;cursor:pointer;border-bottom:2px solid transparent;text-transform:uppercase}
.tab.active{color:#7ACFCC;border-bottom-color:#7ACFCC}
.tab:hover{color:#cbd5e1}
.main{padding:18px 24px;max-width:1400px;margin:0 auto}
.pane{display:none}.pane.active{display:block}
.card{background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:14px;margin-bottom:14px;box-shadow:0 1px 2px rgba(0,0,0,.04)}
.card-title{font-size:1em;font-weight:700;color:#0f172a;margin-bottom:8px}
.kpi-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin-bottom:14px}
.kpi{background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:12px;text-align:center}
.kpi-label{font-size:.72em;color:#64748b;text-transform:uppercase;letter-spacing:.5px}
.kpi-val{font-size:1.8em;font-weight:800;color:#0f172a;margin-top:2px}
.kpi-val.good{color:#15803d}.kpi-val.warn{color:#fbbf24}.kpi-val.crit{color:#ef4444}
.kpi-val.muted{color:#94a3b8}
table{width:100%;border-collapse:collapse;font-size:.85em}
th,td{padding:8px 10px;border-bottom:1px solid #f1f5f9;text-align:left;vertical-align:top}
th{background:#f8fafc;font-weight:700;color:#475569;font-size:.76em;text-transform:uppercase;letter-spacing:.5px}
tr:hover{background:#fafafa}
.empty{text-align:center;color:#94a3b8;padding:20px;font-style:italic}
.estado{display:inline-block;padding:2px 8px;border-radius:4px;font-size:.78em;font-weight:600;text-transform:uppercase}
.estado-draft{background:#fef3c7;color:#92400e}
.estado-en_revision{background:#dbeafe;color:#1e40af}
.estado-aprobado{background:#d1fae5;color:#065f46}
.estado-obsoleto{background:#f3f4f6;color:#6b7280}
.estado-iniciado,.estado-en_proceso{background:#fef3c7;color:#92400e}
.estado-completado{background:#dbeafe;color:#1e40af}
.estado-liberado{background:#d1fae5;color:#065f46}
.estado-rechazado{background:#fee2e2;color:#991b1b}
.btn{padding:6px 14px;border:none;border-radius:6px;cursor:pointer;font-size:.85em;font-weight:600;text-decoration:none;display:inline-block}
.btn-primary{background:#7ACFCC;color:#0f172a}.btn-primary:hover{background:#5fb8b5}
.btn-sm{padding:4px 10px;font-size:.78em}
.muted{color:#94a3b8;font-size:.85em}
.detail-grid{display:grid;grid-template-columns:140px 1fr;gap:6px 14px;font-size:.88em}
.detail-grid dt{color:#64748b;font-weight:600}
.detail-grid dd{margin:0;color:#0f172a}
.paso-card{background:#f8fafc;border-left:3px solid #cbd5e1;padding:8px 12px;margin-bottom:6px;border-radius:0 4px 4px 0}
.paso-card.completado{border-left-color:#15803d}
.paso-card.en_proceso{border-left-color:#fbbf24}
.action-bar{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}
.btn-success{background:#15803d;color:#fff}.btn-success:hover{background:#166534}
.btn-danger{background:#dc2626;color:#fff}.btn-danger:hover{background:#b91c1c}
.modal-bg{position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,.6);display:none;align-items:center;justify-content:center;z-index:9999;padding:20px}
.modal-bg.open{display:flex}
.modal{background:#fff;border-radius:8px;padding:20px;max-width:420px;width:100%;box-shadow:0 10px 40px rgba(0,0,0,.3)}
.modal h3{margin:0 0 12px 0;font-size:1.1em}
.modal label{display:block;font-size:.82em;color:#475569;font-weight:600;margin:8px 0 2px}
.modal input,.modal textarea{width:100%;padding:8px 10px;border:1px solid #cbd5e1;border-radius:4px;font-size:.95em;box-sizing:border-box;font-family:inherit}
.modal-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:14px}
.modal-error{color:#dc2626;font-size:.85em;margin-top:8px;min-height:1em}
.modal-meaning{background:#eff6ff;border:1px solid #bfdbfe;border-radius:4px;padding:8px;font-size:.85em;margin-bottom:8px;color:#1e3a8a}
</style>
</head>
<body>
<header>
  <div class="logo">EOS · BATCH RECORD DIGITAL</div>
  <div><a href="/modulos" style="color:#cbd5e1;font-size:.85em;text-decoration:none">← Módulos</a></div>
</header>

<div class="tabs">
  <div class="tab active" data-pane="dash">Dashboard</div>
  <div class="tab" data-pane="mbr">MBR Templates</div>
  <div class="tab" data-pane="ebr">EBR Ejecuciones</div>
  <div class="tab" data-pane="cleaning">Cleaning Log</div>
</div>

<div class="main">

  <!-- DASHBOARD -->
  <div id="pane-dash" class="pane active">
    <div class="kpi-row" id="kpi-row">
      <div class="kpi"><div class="kpi-label">MBR Aprobados</div><div class="kpi-val good" id="kpi-mbr-aprob">·</div><div class="muted">vigentes</div></div>
      <div class="kpi"><div class="kpi-label">MBR Draft</div><div class="kpi-val warn" id="kpi-mbr-draft">·</div><div class="muted">pendientes revisión QA</div></div>
      <div class="kpi"><div class="kpi-label">EBR Activos</div><div class="kpi-val" id="kpi-ebr-act">·</div><div class="muted">en proceso</div></div>
      <div class="kpi"><div class="kpi-label">EBR Esperando QC</div><div class="kpi-val warn" id="kpi-ebr-qc">·</div><div class="muted">a liberar</div></div>
      <div class="kpi"><div class="kpi-label">EBR Liberados</div><div class="kpi-val good" id="kpi-ebr-lib">·</div><div class="muted">completados OK</div></div>
      <div class="kpi"><div class="kpi-label">EBR Rechazados</div><div class="kpi-val crit" id="kpi-ebr-rej">·</div><div class="muted">no conformes</div></div>
    </div>
    <div class="card">
      <div class="card-title">Evidencia regulatoria · Part 11 / INVIMA</div>
      <p class="muted" style="font-size:.88em">
        Este módulo reemplaza MYBATCH como sistema de batch records digitales.
        Cumple Part 11 §11.10(e) (audit trail inmutable), §11.50/11.70/11.200
        (firmas electrónicas con re-auth + identity binding + linking) y la
        práctica GMP típica que INVIMA usa como benchmark en auditorías de
        seguimiento.
      </p>
      <p class="muted" style="font-size:.88em">
        <strong>Workflow:</strong> Calidad crea/aprueba MBR (procedimiento) →
        operario inicia EBR (lote real) → ejecuta pasos paso a paso (con
        e-signature en pasos críticos) → reporta IPCs y pesajes →
        Calidad libera con firma. PDF auditable disponible para INVIMA.
      </p>
    </div>
  </div>

  <!-- MBR -->
  <div id="pane-mbr" class="pane">
    <div class="card">
      <div class="card-title">Master Batch Records (procedimientos)</div>
      <div id="mbr-tabla">Cargando…</div>
    </div>
    <div id="mbr-detail" style="display:none"></div>
  </div>

  <!-- EBR -->
  <div id="pane-ebr" class="pane">
    <div class="card">
      <div class="card-title">Executed Batch Records (lotes en ejecución)</div>
      <div id="ebr-tabla">Cargando…</div>
    </div>
    <div id="ebr-detail" style="display:none"></div>
  </div>

  <!-- CLEANING -->
  <div id="pane-cleaning" class="pane">
    <div class="card">
      <div class="card-title">Cleaning Log · limpiezas de equipos</div>
      <div id="cleaning-tabla">Cargando…</div>
    </div>
  </div>

</div>

<!-- Modal de firma electrónica reusable -->
<div id="signModal" class="modal-bg">
  <div class="modal">
    <h3 id="signTitle">Firma electrónica</h3>
    <div class="modal-meaning" id="signMeaning">…</div>
    <label>Tu password (re-autenticación · Part 11 §11.200)</label>
    <input type="password" id="signPwd" autocomplete="current-password">
    <label>Código MFA (si tenés activo · 6 dígitos)</label>
    <input type="text" id="signTotp" inputmode="numeric" maxlength="6" placeholder="opcional">
    <label>Comentario (queda en el record)</label>
    <textarea id="signComment" rows="2" placeholder="Razón de la firma"></textarea>
    <div class="modal-error" id="signError"></div>
    <div class="modal-actions">
      <button class="btn btn-sm" onclick="closeSignModal()">Cancelar</button>
      <button class="btn btn-primary btn-sm" id="signSubmit" onclick="submitSign()">Firmar</button>
    </div>
  </div>
</div>

<script>
// ── tabs ──
document.querySelectorAll('.tab').forEach(function(t){
  t.addEventListener('click', function(){
    document.querySelectorAll('.tab').forEach(function(x){x.classList.remove('active')});
    document.querySelectorAll('.pane').forEach(function(x){x.classList.remove('active')});
    t.classList.add('active');
    document.getElementById('pane-'+t.dataset.pane).classList.add('active');
    if(t.dataset.pane==='mbr') loadMbrs();
    if(t.dataset.pane==='ebr') loadEbrs();
    if(t.dataset.pane==='cleaning') loadCleaning();
  });
});

// ── helpers ──
function escapeHtml(s){return String(s||'').replace(/[&<>"']/g, function(c){return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]})}
function fmtDate(s){if(!s) return '—';return s.substring(0,16).replace('T',' ');}

// CSRF defense-in-depth (mismo patrón que aseguramiento_html.py)
function _csrf(){var m=document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/);return m?decodeURIComponent(m[1]):'';}
function _fetchOpts(method, body){
  var headers = {}; var tok = _csrf();
  if (tok) headers['X-CSRF-Token'] = tok;
  var opts = {method: method||'GET', headers: headers, credentials: 'same-origin'};
  if (body !== undefined && body !== null) {
    headers['Content-Type'] = 'application/json';
    opts.body = (typeof body === 'string') ? body : JSON.stringify(body);
  }
  return opts;
}
fetch('/api/csrf-token', {credentials: 'same-origin'}).catch(function(){});

// ── Modal e-signature reusable ──
// onSigned(signature_id) callback se llama con el ID si la firma fue ok.
let _signCtx = null;
function openSignModal(opts) {
  // opts: {title, meaning, recordTable, recordId, onSigned}
  _signCtx = opts;
  document.getElementById('signTitle').textContent = opts.title || 'Firma electrónica';
  document.getElementById('signMeaning').innerHTML =
    'Vas a firmar como <strong>' + opts.meaning + '</strong> sobre <code>'
    + opts.recordTable + ' #' + opts.recordId + '</code>. La firma quedará '
    + 'inmutable en el audit trail (Part 11 §11.50).';
  document.getElementById('signPwd').value = '';
  document.getElementById('signTotp').value = '';
  document.getElementById('signComment').value = '';
  document.getElementById('signError').textContent = '';
  document.getElementById('signSubmit').disabled = false;
  document.getElementById('signModal').classList.add('open');
  setTimeout(()=>document.getElementById('signPwd').focus(), 50);
}
function closeSignModal() {
  document.getElementById('signModal').classList.remove('open');
  _signCtx = null;
}
async function submitSign() {
  if (!_signCtx) return;
  const btn = document.getElementById('signSubmit');
  const errDiv = document.getElementById('signError');
  btn.disabled = true;
  errDiv.textContent = '';
  try {
    // Paso 1: challenge (re-auth password+TOTP)
    const ch = await fetch('/api/sign/challenge', _fetchOpts('POST', {
      password: document.getElementById('signPwd').value,
      totp_token: document.getElementById('signTotp').value || undefined,
    }));
    const chData = await ch.json();
    if (!ch.ok) { errDiv.textContent = 'Auth: ' + (chData.error || ch.status); btn.disabled=false; return; }

    // Paso 2: sign
    const sig = await fetch('/api/sign', _fetchOpts('POST', {
      record_table: _signCtx.recordTable,
      record_id: String(_signCtx.recordId),
      meaning: _signCtx.meaning,
      comment: document.getElementById('signComment').value,
      challenge_token: chData.token,
    }));
    const sigData = await sig.json();
    if (!sig.ok) { errDiv.textContent = 'Firma: ' + (sigData.error || sig.status); btn.disabled=false; return; }

    // Callback con signature_id
    const cb = _signCtx.onSigned;
    closeSignModal();
    if (cb) await cb(sigData.signature_id);
  } catch(e) {
    errDiv.textContent = 'Error: ' + e.message;
    btn.disabled = false;
  }
}
document.addEventListener('keydown', function(e){
  if (e.key === 'Escape' && document.getElementById('signModal').classList.contains('open')) closeSignModal();
});

// ── dashboard KPIs ──
async function loadDash(){
  try {
    const r = await fetch('/api/brd/mbr');
    const mbrs = (await r.json()).items || [];
    document.getElementById('kpi-mbr-aprob').textContent = mbrs.filter(m=>m.estado==='aprobado').length;
    document.getElementById('kpi-mbr-draft').textContent = mbrs.filter(m=>m.estado==='draft' || m.estado==='en_revision').length;

    const r2 = await fetch('/api/brd/ebr');
    const ebrs = (await r2.json()).items || [];
    document.getElementById('kpi-ebr-act').textContent = ebrs.filter(e=>['iniciado','en_proceso'].includes(e.estado)).length;
    document.getElementById('kpi-ebr-qc').textContent = ebrs.filter(e=>['completado','en_revision_qc'].includes(e.estado)).length;
    document.getElementById('kpi-ebr-lib').textContent = ebrs.filter(e=>e.estado==='liberado').length;
    document.getElementById('kpi-ebr-rej').textContent = ebrs.filter(e=>e.estado==='rechazado').length;
  } catch(e) {
    console.error('loadDash error', e);
  }
}
loadDash();

// ── MBR list + detail ──
async function loadMbrs(){
  const div = document.getElementById('mbr-tabla');
  div.innerHTML = 'Cargando…';
  try {
    const r = await fetch('/api/brd/mbr');
    const items = (await r.json()).items || [];
    if (!items.length) { div.innerHTML = '<div class="empty">Sin MBRs creados todavía.</div>'; return; }
    let html = '<table><thead><tr><th>Producto</th><th>v</th><th>Estado</th><th>Lote ref (g)</th><th>Creado por</th><th>Aprobado</th><th></th></tr></thead><tbody>';
    items.forEach(function(m){
      html += '<tr>'
        + '<td><strong>' + escapeHtml(m.producto_nombre) + '</strong></td>'
        + '<td>v' + m.version + '</td>'
        + '<td><span class="estado estado-' + m.estado + '">' + m.estado + '</span></td>'
        + '<td>' + (m.lote_size_g ? m.lote_size_g.toLocaleString('es-CO') : '—') + '</td>'
        + '<td>' + escapeHtml(m.creado_por) + '</td>'
        + '<td>' + (m.aprobado_por ? escapeHtml(m.aprobado_por) + '<br><span class="muted">' + fmtDate(m.aprobado_at_utc) + '</span>' : '—') + '</td>'
        + '<td><button class="btn btn-primary btn-sm" onclick="showMbrDetail(' + m.id + ')">Ver</button></td>'
        + '</tr>';
    });
    div.innerHTML = html + '</tbody></table>';
  } catch(e) { div.innerHTML = '<div class="empty">Error: ' + escapeHtml(e.message) + '</div>'; }
}
async function showMbrDetail(id){
  const div = document.getElementById('mbr-detail');
  div.style.display = 'block';
  div.innerHTML = '<div class="card">Cargando MBR ' + id + '…</div>';
  const r = await fetch('/api/brd/mbr/' + id);
  const m = await r.json();

  // Botones de acción contextual según estado
  let actions = '';
  if (m.estado === 'draft') {
    actions = '<div class="action-bar">'
      + '<button class="btn btn-primary btn-sm" onclick="submitMbr(' + id + ')">Submit a revisión</button>'
      + '</div>';
  } else if (m.estado === 'en_revision') {
    actions = '<div class="action-bar">'
      + '<button class="btn btn-success btn-sm" onclick="aprobarMbr(' + id + ')">Firmar y aprobar</button>'
      + '</div>';
  } else if (m.estado === 'aprobado') {
    actions = '<div class="action-bar">'
      + '<button class="btn btn-danger btn-sm" onclick="obsoletarMbr(' + id + ')">Obsoletar (motivo)</button>'
      + '</div>';
  }

  let html = '<div class="card">'
    + '<div class="card-title">' + escapeHtml(m.titulo || m.producto_nombre) + ' v' + m.version + ' <span class="estado estado-' + m.estado + '">' + m.estado + '</span></div>'
    + '<dl class="detail-grid">'
    + '<dt>Producto</dt><dd>' + escapeHtml(m.producto_nombre) + '</dd>'
    + '<dt>Lote ref</dt><dd>' + (m.lote_size_g ? m.lote_size_g.toLocaleString('es-CO') + ' g' : '—') + '</dd>'
    + '<dt>Tiempo est</dt><dd>' + (m.tiempo_total_estimado_min || 0) + ' min</dd>'
    + '<dt>Creado por</dt><dd>' + escapeHtml(m.creado_por) + ' · ' + fmtDate(m.creado_at_utc) + '</dd>'
    + (m.aprobado_por ? '<dt>Aprobado por</dt><dd>' + escapeHtml(m.aprobado_por) + ' · firma #' + m.aprobado_signature_id + '</dd>' : '')
    + (m.descripcion ? '<dt>Descripción</dt><dd>' + escapeHtml(m.descripcion) + '</dd>' : '')
    + '</dl>'
    + actions
    + '</div>';
  if (m.pasos && m.pasos.length) {
    html += '<div class="card"><div class="card-title">Pasos del procedimiento (' + m.pasos.length + ')</div>';
    m.pasos.forEach(function(p){
      html += '<div class="paso-card"><strong>Paso ' + p.orden + '</strong>'
        + (p.fase ? ' · <span class="muted">' + escapeHtml(p.fase) + '</span>' : '')
        + (p.tipo_paso !== 'otro' ? ' · <span class="muted">' + p.tipo_paso + '</span>' : '')
        + '<br>' + escapeHtml(p.descripcion)
        + (p.equipo_requerido ? '<br><span class="muted">Equipo: ' + escapeHtml(p.equipo_requerido) + '</span>' : '')
        + (p.requiere_e_sign ? ' <span class="estado estado-en_revision">e-sign</span>' : '')
        + (p.requiere_qc ? ' <span class="estado estado-en_revision">QC</span>' : '')
        + '</div>';
    });
    html += '</div>';
  }
  div.innerHTML = html;
}

// ── EBR list + detail ──
async function loadEbrs(){
  const div = document.getElementById('ebr-tabla');
  div.innerHTML = 'Cargando…';
  try {
    const r = await fetch('/api/brd/ebr');
    const items = (await r.json()).items || [];
    if (!items.length) { div.innerHTML = '<div class="empty">Sin EBRs ejecutados todavía. Iniciá uno desde un MBR aprobado.</div>'; return; }
    let html = '<table><thead><tr><th>OP</th><th>Lote</th><th>Estado</th><th>Iniciado</th><th>Yield</th><th>Liberado por</th><th></th></tr></thead><tbody>';
    items.forEach(function(e){
      const yld = e.yield_pct != null ? e.yield_pct.toFixed(1) + '%' : '—';
      const op = e.numero_op || '—';
      html += '<tr>'
        + '<td><span class="muted" style="font-family:monospace;font-size:12px">' + escapeHtml(op) + '</span></td>'
        + '<td><strong>' + escapeHtml(e.lote) + '</strong></td>'
        + '<td><span class="estado estado-' + e.estado + '">' + e.estado + '</span></td>'
        + '<td>' + escapeHtml(e.iniciado_por) + '<br><span class="muted">' + fmtDate(e.iniciado_at_utc) + '</span></td>'
        + '<td>' + yld + '</td>'
        + '<td>' + (e.liberado_por ? escapeHtml(e.liberado_por) : '—') + '</td>'
        + '<td><button class="btn btn-primary btn-sm" onclick="showEbrDetail(' + e.id + ')">Ver</button>'
        + (['liberado','rechazado','completado'].includes(e.estado) ? ' <a class="btn btn-sm" href="/api/brd/ebr/' + e.id + '/pdf" target="_blank">PDF</a>' : '')
        + '</td>'
        + '</tr>';
    });
    div.innerHTML = html + '</tbody></table>';
  } catch(e) { div.innerHTML = '<div class="empty">Error: ' + escapeHtml(e.message) + '</div>'; }
}
async function showEbrDetail(id){
  const div = document.getElementById('ebr-detail');
  div.style.display = 'block';
  div.innerHTML = '<div class="card">Cargando EBR ' + id + '…</div>';
  const [d, ipc, rec] = await Promise.all([
    fetch('/api/brd/ebr/' + id).then(r=>r.json()),
    fetch('/api/brd/ebr/' + id + '/ipc-resultados').then(r=>r.json()).catch(()=>({items:[]})),
    fetch('/api/brd/ebr/' + id + '/reconciliacion').then(r=>r.json()).catch(()=>null),
  ]);

  // Acciones contextuales según estado
  let actions = '';
  if (d.estado === 'completado' || d.estado === 'en_revision_qc') {
    actions = '<div class="action-bar">'
      + '<button class="btn btn-success btn-sm" onclick="liberarEbr(' + id + ')">Firmar y liberar</button>'
      + '<button class="btn btn-danger btn-sm" onclick="rechazarEbr(' + id + ')">Firmar y rechazar</button>'
      + '</div>';
  } else if (['liberado','rechazado'].includes(d.estado)) {
    actions = '<div class="action-bar">'
      + '<a class="btn btn-primary btn-sm" href="/api/brd/ebr/' + id + '/pdf" target="_blank">Descargar PDF auditable</a>'
      + '</div>';
  }

  let html = '<div class="card">'
    + '<div class="card-title">EBR ' + escapeHtml(d.lote) + ' <span class="estado estado-' + d.estado + '">' + d.estado + '</span></div>'
    + '<dl class="detail-grid">'
    + '<dt>MBR</dt><dd>v' + d.mbr_version + ' (id ' + d.mbr_template_id + ')</dd>'
    + '<dt>Iniciado por</dt><dd>' + escapeHtml(d.iniciado_por) + ' · ' + fmtDate(d.iniciado_at_utc) + '</dd>'
    + (d.completado_at_utc ? '<dt>Completado</dt><dd>' + fmtDate(d.completado_at_utc) + '</dd>' : '')
    + '<dt>Cantidad obj</dt><dd>' + d.cantidad_objetivo_g.toLocaleString('es-CO') + ' g</dd>'
    + (d.cantidad_real_g != null ? '<dt>Cantidad real</dt><dd>' + d.cantidad_real_g.toLocaleString('es-CO') + ' g · yield ' + d.yield_pct.toFixed(2) + '%</dd>' : '')
    + (d.liberado_por ? '<dt>Liberado por</dt><dd>' + escapeHtml(d.liberado_por) + ' · firma #' + d.liberado_signature_id + '</dd>' : '')
    + (d.rechazado_motivo ? '<dt>Rechazo</dt><dd style="color:#991b1b">' + escapeHtml(d.rechazado_motivo) + '</dd>' : '')
    + '</dl>'
    + actions
    + '</div>';
  if (d.pasos && d.pasos.length) {
    html += '<div class="card"><div class="card-title">Pasos ejecutados (' + d.pasos.length + ')</div>';
    const ebrEditable = ['iniciado','en_proceso'].includes(d.estado);
    d.pasos.forEach(function(p){
      // Acciones del paso según estado y flags requiere_*
      let pasoActions = '';
      if (ebrEditable) {
        if (p.estado === 'pendiente') {
          pasoActions = '<button class="btn btn-primary btn-sm" onclick="iniciarPasoEbr(' + id + ',' + p.orden + ')">Iniciar</button>';
        } else if (p.estado === 'en_proceso') {
          if (p.requiere_e_sign) {
            pasoActions = '<button class="btn btn-success btn-sm" onclick="completarPasoEbrConFirma(' + id + ',' + p.orden + ',' + p.id + ',' + p.requiere_qc + ')">Firmar y completar</button>';
          } else {
            pasoActions = '<button class="btn btn-success btn-sm" onclick="completarPasoEbrSimple(' + id + ',' + p.orden + ')">Completar</button>';
          }
        }
      }
      html += '<div class="paso-card ' + p.estado + '"><strong>Paso ' + p.orden + '</strong> · <span class="estado estado-' + p.estado + '">' + p.estado + '</span>'
        + (p.requiere_e_sign ? ' <span class="estado estado-en_revision">e-sign</span>' : '')
        + (p.requiere_qc ? ' <span class="estado estado-en_revision">QC</span>' : '')
        + '<br>' + escapeHtml(p.descripcion)
        + (p.operario_username ? '<br><span class="muted">Operario: ' + escapeHtml(p.operario_username) + (p.completado_at_utc ? ' · ' + fmtDate(p.completado_at_utc) : '') + '</span>' : '')
        + (p.observaciones ? '<br><em class="muted">"' + escapeHtml(p.observaciones) + '"</em>' : '')
        + (p.e_sign_id ? ' · <span class="muted">e-sign #' + p.e_sign_id + '</span>' : '')
        + (pasoActions ? '<div class="action-bar" style="margin-top:6px">' + pasoActions + '</div>' : '')
        + '</div>';
    });
    // Acción global: completar EBR si todos los pasos están completados
    const allCompletados = d.pasos.every(function(p){ return p.estado === 'completado' || p.estado === 'omitido'; });
    if (ebrEditable && allCompletados && d.pasos.length > 0) {
      html += '<div class="action-bar" style="margin-top:10px"><button class="btn btn-primary btn-sm" onclick="completarEbr(' + id + ')">Completar EBR (reportar cantidad real)</button></div>';
    }
    html += '</div>';
  }
  // Mostrar IPCs pendientes (specs sin resultado todavía) + acciones
  const ebrEditable2 = ['iniciado','en_proceso'].includes(d.estado);
  if (ebrEditable2) {
    try {
      const sr = await fetch('/api/brd/mbr/' + d.mbr_template_id + '/ipc-specs').then(r=>r.json());
      const yaReportados = new Set((ipc.items || []).map(x => x.ipc_spec_id));
      const pendientes = (sr.items || []).filter(s => !yaReportados.has(s.id));
      if (pendientes.length) {
        html += '<div class="card"><div class="card-title">IPCs pendientes (' + pendientes.length + ')</div>';
        pendientes.forEach(function(s){
          const rango = (s.valor_min !== null || s.valor_max !== null) ? (s.valor_min + ' – ' + s.valor_max + ' ' + s.unidad) : 'cualitativo';
          html += '<div class="paso-card"><strong>' + escapeHtml(s.parametro) + '</strong> · <span class="muted">rango: ' + escapeHtml(rango) + '</span>'
            + (s.obligatorio ? ' <span class="estado estado-en_revision">obligatorio</span>' : '')
            + '<div class="action-bar" style="margin-top:6px"><button class="btn btn-primary btn-sm" onclick="reportarIpc(' + id + ',' + s.id + ',\'' + escapeHtml(s.parametro) + '\',' + (s.valor_min===null?'null':s.valor_min) + ',' + (s.valor_max===null?'null':s.valor_max) + ',\'' + escapeHtml(s.unidad||'') + '\')">Reportar medición</button></div>'
            + '</div>';
        });
        html += '</div>';
      }

      // Pesajes faltantes (MPs de la fórmula que aún no se pesaron)
      const recRes = rec || {};
      if (recRes.no_pesados && recRes.no_pesados.length) {
        html += '<div class="card"><div class="card-title">Pesajes pendientes (' + recRes.no_pesados.length + ' MPs)</div>'
          + '<table><thead><tr><th>MP</th><th>Teórico (g)</th><th></th></tr></thead><tbody>';
        recRes.no_pesados.forEach(function(mp){
          html += '<tr><td>' + escapeHtml(mp.material_id) + ' · ' + escapeHtml(mp.material_nombre || '') + '</td>'
            + '<td>' + mp.cantidad_teorica_g.toFixed(2) + '</td>'
            + '<td><button class="btn btn-primary btn-sm" onclick="reportarPesaje(' + id + ',\'' + escapeHtml(mp.material_id) + '\',\'' + escapeHtml(mp.material_nombre||'') + '\',' + mp.cantidad_teorica_g + ')">Reportar</button></td></tr>';
        });
        html += '</tbody></table></div>';
      }
    } catch(e) { /* ignorar errores de listados auxiliares */ }
  }

  if (ipc.items && ipc.items.length) {
    html += '<div class="card"><div class="card-title">In-Process Controls (' + ipc.items.length + ')</div>'
      + '<table><thead><tr><th>Parámetro</th><th>Medido</th><th>Rango</th><th>Conforme</th><th>Por</th></tr></thead><tbody>';
    ipc.items.forEach(function(i){
      const conf = i.conforme === 1 ? '<span class="estado estado-aprobado">SÍ</span>' :
                   i.conforme === 0 ? '<span class="estado estado-rechazado">NO</span>' : '<span class="muted">pendiente</span>';
      const rango = (i.spec.valor_min != null || i.spec.valor_max != null) ? (i.spec.valor_min + ' – ' + i.spec.valor_max + ' ' + i.spec.unidad) : '—';
      html += '<tr><td>' + escapeHtml(i.spec.parametro) + '</td><td>' + (i.valor_medido != null ? i.valor_medido + ' ' + i.spec.unidad : escapeHtml(i.valor_texto)) + '</td><td>' + escapeHtml(rango) + '</td><td>' + conf + '</td><td>' + escapeHtml(i.medido_por) + '</td></tr>';
    });
    html += '</tbody></table></div>';
  }
  if (rec && rec.outliers && (rec.outliers.length || rec.no_pesados.length)) {
    html += '<div class="card"><div class="card-title">Reconciliación · ' + (rec.outliers.length) + ' outlier(s) · ' + rec.no_pesados.length + ' MP(s) sin pesar</div>';
    if (rec.outliers.length) {
      html += '<table><thead><tr><th>MP</th><th>Teórico (g)</th><th>Real (g)</th><th>Δ%</th></tr></thead><tbody>';
      rec.outliers.forEach(function(x){
        html += '<tr><td>' + escapeHtml(x.material_id) + ' · ' + escapeHtml(x.material_nombre || '') + '</td><td>' + x.cantidad_teorica_g.toFixed(2) + '</td><td>' + x.cantidad_real_g.toFixed(2) + '</td><td style="color:#991b1b;font-weight:700">' + x.delta_pct.toFixed(1) + '%</td></tr>';
      });
      html += '</tbody></table>';
    }
    html += '</div>';
  }
  div.innerHTML = html;
}

// ── Acciones MBR ──
async function submitMbr(id) {
  if (!confirm('Submit MBR a revisión QA · ya no se podrá editar como draft.')) return;
  const r = await fetch('/api/brd/mbr/' + id + '/submit', _fetchOpts('POST', {}));
  const d = await r.json();
  if (!r.ok) { alert('Error: ' + (d.error||r.status)); return; }
  showMbrDetail(id);
  loadMbrs();
}
function aprobarMbr(id) {
  openSignModal({
    title: 'Aprobar MBR (firma QA)',
    meaning: 'aprueba',
    recordTable: 'mbr_templates',
    recordId: id,
    onSigned: async function(sigId) {
      const r = await fetch('/api/brd/mbr/' + id + '/aprobar', _fetchOpts('POST', {signature_id: sigId}));
      const d = await r.json();
      if (!r.ok) { alert('Error aprobando: ' + (d.error||r.status)); return; }
      showMbrDetail(id);
      loadMbrs();
    },
  });
}
async function obsoletarMbr(id) {
  const motivo = prompt('Motivo de obsoletar este MBR (queda en audit):');
  if (!motivo || motivo.trim().length < 3) return;
  const r = await fetch('/api/brd/mbr/' + id + '/obsoletar', _fetchOpts('POST', {motivo: motivo.trim()}));
  const d = await r.json();
  if (!r.ok) { alert('Error: ' + (d.error||r.status)); return; }
  showMbrDetail(id);
  loadMbrs();
}

// ── Acciones EBR ──
function liberarEbr(id) {
  openSignModal({
    title: 'Liberar EBR (firma QC)',
    meaning: 'libera',
    recordTable: 'ebr_ejecuciones',
    recordId: id,
    onSigned: async function(sigId) {
      const r = await fetch('/api/brd/ebr/' + id + '/liberar', _fetchOpts('POST', {signature_id: sigId}));
      const d = await r.json();
      if (!r.ok) { alert('Error liberando: ' + (d.error||r.status)); return; }
      showEbrDetail(id);
      loadEbrs();
    },
  });
}
function rechazarEbr(id) {
  const motivo = prompt('Motivo del rechazo (queda en audit):');
  if (!motivo || motivo.trim().length < 3) return;
  openSignModal({
    title: 'Rechazar EBR (firma QC)',
    meaning: 'rechaza',
    recordTable: 'ebr_ejecuciones',
    recordId: id,
    onSigned: async function(sigId) {
      const r = await fetch('/api/brd/ebr/' + id + '/rechazar', _fetchOpts('POST', {signature_id: sigId, motivo: motivo.trim()}));
      const d = await r.json();
      if (!r.ok) { alert('Error rechazando: ' + (d.error||r.status)); return; }
      showEbrDetail(id);
      loadEbrs();
    },
  });
}

// ── Acciones de pasos EBR (B1.2) ──
async function iniciarPasoEbr(ebrId, orden) {
  const r = await fetch('/api/brd/ebr/' + ebrId + '/pasos/' + orden + '/iniciar', _fetchOpts('POST', {}));
  const d = await r.json();
  if (!r.ok) { alert('Error iniciar paso: ' + (d.error||r.status)); return; }
  showEbrDetail(ebrId);
}

async function completarPasoEbrSimple(ebrId, orden) {
  const obs = prompt('Observaciones del paso (opcional):', '') || '';
  const r = await fetch('/api/brd/ebr/' + ebrId + '/pasos/' + orden + '/completar',
    _fetchOpts('POST', {observaciones: obs}));
  const d = await r.json();
  if (!r.ok) { alert('Error completar paso: ' + (d.error||r.status)); return; }
  showEbrDetail(ebrId);
}

function completarPasoEbrConFirma(ebrId, orden, pasoId, requiereQc) {
  // Primero pedir e-sign del operario (meaning='ejecuta' sobre ebr_pasos_ejecutados)
  const obs = prompt('Observaciones del paso (queda en audit):', '') || '';
  openSignModal({
    title: 'Firmar y completar paso ' + orden,
    meaning: 'ejecuta',
    recordTable: 'ebr_pasos_ejecutados',
    recordId: pasoId,
    onSigned: async function(opSigId) {
      const body = {observaciones: obs, signature_id: opSigId};
      // Si requiere QC, pedir segunda firma con meaning='supervisa'
      if (requiereQc) {
        // Cierra el modal anterior y abre el de QC
        openSignModal({
          title: 'Firma QC para paso ' + orden,
          meaning: 'supervisa',
          recordTable: 'ebr_pasos_ejecutados',
          recordId: pasoId,
          onSigned: async function(qcSigId) {
            body.qc_signature_id = qcSigId;
            const r = await fetch('/api/brd/ebr/' + ebrId + '/pasos/' + orden + '/completar', _fetchOpts('POST', body));
            const d = await r.json();
            if (!r.ok) { alert('Error completar paso: ' + (d.error||r.status)); return; }
            showEbrDetail(ebrId);
          },
        });
        return;
      }
      const r = await fetch('/api/brd/ebr/' + ebrId + '/pasos/' + orden + '/completar', _fetchOpts('POST', body));
      const d = await r.json();
      if (!r.ok) { alert('Error completar paso: ' + (d.error||r.status)); return; }
      showEbrDetail(ebrId);
    },
  });
}

// ── Reportar IPC y pesaje (B1.3) ──
async function reportarIpc(ebrId, specId, parametro, vmin, vmax, unidad) {
  const tieneRango = (vmin !== null && vmin !== undefined) || (vmax !== null && vmax !== undefined);
  let valorRaw;
  if (tieneRango) {
    valorRaw = prompt('Reportar ' + parametro + ' (' + unidad + ') · rango: ' + vmin + ' – ' + vmax + ':', '');
    if (!valorRaw) return;
    const v = parseFloat(valorRaw);
    if (isNaN(v)) { alert('Valor inválido'); return; }
    const r = await fetch('/api/brd/ebr/' + ebrId + '/ipc-resultados',
      _fetchOpts('POST', {ipc_spec_id: specId, valor_medido: v}));
    const d = await r.json();
    if (!r.ok) { alert('Error: ' + (d.error||r.status)); return; }
    if (d.conforme === 0) {
      alert('IPC fuera de spec · medido ' + v + ' fuera de [' + vmin + ',' + vmax + ']. Documentar desviación.');
    }
  } else {
    valorRaw = prompt('Reportar ' + parametro + ' (cualitativo · ej. "conforme/no conforme/turbio/etc"):', '');
    if (!valorRaw) return;
    const r = await fetch('/api/brd/ebr/' + ebrId + '/ipc-resultados',
      _fetchOpts('POST', {ipc_spec_id: specId, valor_texto: valorRaw}));
    const d = await r.json();
    if (!r.ok) { alert('Error: ' + (d.error||r.status)); return; }
  }
  showEbrDetail(ebrId);
}

async function reportarPesaje(ebrId, materialId, materialNombre, teorico) {
  const realRaw = prompt('Pesaje real de ' + materialNombre + ' (' + materialId + ') · teórico: ' + teorico.toFixed(2) + ' g:', teorico.toFixed(2));
  if (!realRaw) return;
  const real = parseFloat(realRaw);
  if (isNaN(real) || real < 0) { alert('Valor inválido'); return; }
  const lote = prompt('Lote del MP (opcional · ej. ' + materialId + '-2026-001):', '') || '';
  const r = await fetch('/api/brd/ebr/' + ebrId + '/pesajes',
    _fetchOpts('POST', {material_id: materialId, cantidad_real_g: real, lote_mp: lote}));
  const d = await r.json();
  if (!r.ok) { alert('Error pesaje: ' + (d.error||r.status)); return; }
  if (Math.abs(d.delta_pct) > 5) {
    alert('Outlier: delta ' + d.delta_pct.toFixed(1) + '% · documentar desviación si aplica.');
  }
  showEbrDetail(ebrId);
}

async function completarEbr(ebrId) {
  const cant = prompt('Cantidad real producida (g) · calcula yield:', '');
  if (!cant) return;
  const cantF = parseFloat(cant);
  if (isNaN(cantF) || cantF <= 0) { alert('Cantidad inválida'); return; }
  const r = await fetch('/api/brd/ebr/' + ebrId + '/completar',
    _fetchOpts('POST', {cantidad_real_g: cantF}));
  const d = await r.json();
  if (!r.ok) { alert('Error completar EBR: ' + (d.error||r.status)); return; }
  alert('EBR completado · yield: ' + (d.yield_pct || '-') + '% · listo para liberación QC');
  showEbrDetail(ebrId);
  loadEbrs();
}

// ── Cleaning list ──
async function loadCleaning(){
  const div = document.getElementById('cleaning-tabla');
  div.innerHTML = 'Cargando…';
  try {
    const r = await fetch('/api/brd/cleaning');
    const items = (await r.json()).items || [];
    if (!items.length) { div.innerHTML = '<div class="empty">Sin registros de limpieza.</div>'; return; }
    let html = '<table><thead><tr><th>Equipo</th><th>Tipo</th><th>Lote ant→sig</th><th>Operario</th><th>Iniciado</th><th>Completado</th><th>QC visual</th></tr></thead><tbody>';
    items.forEach(function(c){
      const visual = c.visual_ok === 1 ? '<span class="estado estado-aprobado">OK</span>' :
                     c.visual_ok === 0 ? '<span class="estado estado-rechazado">NO</span>' :
                     '<span class="muted">pendiente</span>';
      html += '<tr>'
        + '<td><strong>' + escapeHtml(c.equipo_codigo) + '</strong></td>'
        + '<td>' + escapeHtml(c.tipo_limpieza) + '</td>'
        + '<td>' + escapeHtml(c.lote_anterior || '—') + ' → ' + escapeHtml(c.lote_siguiente || '—') + '</td>'
        + '<td>' + escapeHtml(c.operario_username) + '</td>'
        + '<td>' + fmtDate(c.iniciado_at_utc) + '</td>'
        + '<td>' + (c.completado_at_utc ? fmtDate(c.completado_at_utc) : '—') + '</td>'
        + '<td>' + visual + (c.qc_username ? '<br><span class="muted">' + escapeHtml(c.qc_username) + '</span>' : '') + '</td>'
        + '</tr>';
    });
    div.innerHTML = html + '</tbody></table>';
  } catch(e) { div.innerHTML = '<div class="empty">Error: ' + escapeHtml(e.message) + '</div>'; }
}
</script>
</body>
</html>
'''


def render_brd_dashboard():
    """Endpoint helper · returns the HTML string."""
    return BRD_HTML
