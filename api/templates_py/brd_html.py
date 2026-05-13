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
<link rel="stylesheet" href="/static/cortex.css?v=eos12">
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
  let html = '<div class="card">'
    + '<div class="card-title">' + escapeHtml(m.titulo || m.producto_nombre) + ' v' + m.version + ' <span class="estado estado-' + m.estado + '">' + m.estado + '</span></div>'
    + '<dl class="detail-grid">'
    + '<dt>Producto</dt><dd>' + escapeHtml(m.producto_nombre) + '</dd>'
    + '<dt>Lote ref</dt><dd>' + (m.lote_size_g ? m.lote_size_g.toLocaleString('es-CO') + ' g' : '—') + '</dd>'
    + '<dt>Tiempo est</dt><dd>' + (m.tiempo_total_estimado_min || 0) + ' min</dd>'
    + '<dt>Creado por</dt><dd>' + escapeHtml(m.creado_por) + ' · ' + fmtDate(m.creado_at_utc) + '</dd>'
    + (m.aprobado_por ? '<dt>Aprobado por</dt><dd>' + escapeHtml(m.aprobado_por) + ' · firma #' + m.aprobado_signature_id + '</dd>' : '')
    + (m.descripcion ? '<dt>Descripción</dt><dd>' + escapeHtml(m.descripcion) + '</dd>' : '')
    + '</dl></div>';
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
    let html = '<table><thead><tr><th>Lote</th><th>Estado</th><th>Iniciado</th><th>Yield</th><th>Liberado por</th><th></th></tr></thead><tbody>';
    items.forEach(function(e){
      const yld = e.yield_pct != null ? e.yield_pct.toFixed(1) + '%' : '—';
      html += '<tr>'
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
    + '</dl></div>';
  if (d.pasos && d.pasos.length) {
    html += '<div class="card"><div class="card-title">Pasos ejecutados (' + d.pasos.length + ')</div>';
    d.pasos.forEach(function(p){
      html += '<div class="paso-card ' + p.estado + '"><strong>Paso ' + p.orden + '</strong> · <span class="estado estado-' + p.estado + '">' + p.estado + '</span>'
        + '<br>' + escapeHtml(p.descripcion)
        + (p.operario_username ? '<br><span class="muted">Operario: ' + escapeHtml(p.operario_username) + (p.completado_at_utc ? ' · ' + fmtDate(p.completado_at_utc) : '') + '</span>' : '')
        + (p.observaciones ? '<br><em class="muted">"' + escapeHtml(p.observaciones) + '"</em>' : '')
        + (p.e_sign_id ? ' · <span class="muted">e-sign #' + p.e_sign_id + '</span>' : '')
        + '</div>';
    });
    html += '</div>';
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
