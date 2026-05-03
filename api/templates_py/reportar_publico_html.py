"""Portal publico /reportar para empleados.

Sebastian 3-may-2026: empleados sin login pueden reportar permisos /
salud / incapacidad / cita medica desde el celular validando cedula.
Mobile-first. Sin password.
"""

HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>Reportar a RH · HHA Group</title>
<style>
  * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
  body {
    margin: 0; font-family: -apple-system, "Segoe UI", Roboto, sans-serif;
    background: #f1f5f9; color: #0f172a; padding: 0; min-height: 100vh;
  }
  .header {
    background: linear-gradient(135deg, #0c4a6e, #0e7490);
    color: #fff; padding: 22px 18px; text-align: center;
    box-shadow: 0 2px 12px rgba(0,0,0,.15);
  }
  .header h1 { margin: 0; font-size: 20px; font-weight: 700; }
  .header .sub { margin-top: 6px; font-size: 13px; color: #a5f3fc; }
  .container { max-width: 520px; margin: 0 auto; padding: 18px; }
  .card {
    background: #fff; border-radius: 14px; padding: 20px;
    box-shadow: 0 4px 18px rgba(0,0,0,.08); margin-bottom: 14px;
  }
  label {
    display: block; font-size: 12px; font-weight: 700; color: #475569;
    text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;
  }
  input, textarea, select {
    width: 100%; padding: 14px 14px; font-size: 16px;
    border: 1px solid #cbd5e1; border-radius: 10px; background: #fff;
    color: #0f172a; -webkit-appearance: none;
  }
  input:focus, textarea:focus, select:focus {
    outline: none; border-color: #0e7490; box-shadow: 0 0 0 3px rgba(14,116,144,.15);
  }
  textarea { resize: vertical; min-height: 80px; }
  .field { margin-bottom: 14px; }
  .row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  .tipos {
    display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px;
    margin-bottom: 6px;
  }
  .tipo-btn {
    padding: 18px 12px; border: 2px solid #cbd5e1; background: #fff;
    border-radius: 12px; cursor: pointer; text-align: center;
    font-size: 14px; font-weight: 600; color: #475569;
    transition: all 0.15s; display: flex; flex-direction: column;
    align-items: center; gap: 6px;
  }
  .tipo-btn .icon { font-size: 26px; }
  .tipo-btn:active { transform: scale(0.97); }
  .tipo-btn.active {
    border-color: #0e7490; background: #ecfeff; color: #0c4a6e;
    box-shadow: 0 4px 12px rgba(14,116,144,.2);
  }
  .submit {
    width: 100%; padding: 18px; background: #0e7490; color: #fff;
    border: none; border-radius: 12px; font-size: 17px; font-weight: 700;
    cursor: pointer; box-shadow: 0 4px 14px rgba(14,116,144,.3);
  }
  .submit:disabled { background: #94a3b8; }
  .submit:active:not(:disabled) { transform: scale(0.98); }
  .msg {
    padding: 14px; border-radius: 10px; font-size: 14px;
    margin-bottom: 14px; font-weight: 500;
  }
  .msg.ok { background: #dcfce7; color: #166534; border: 1px solid #86efac; }
  .msg.err { background: #fef2f2; color: #991b1b; border: 1px solid #fca5a5; }
  .help { font-size: 12px; color: #64748b; margin-top: 4px; }
  @media (max-width: 480px) {
    .container { padding: 12px; }
    .card { padding: 16px; }
    .row { grid-template-columns: 1fr; gap: 0; }
    .row > div + div { margin-top: 14px; }
  }
</style>
</head>
<body>
  <div class="header">
    <h1>📋 Reportar a RH</h1>
    <div class="sub">Permisos · Salud · Citas · HHA Group</div>
  </div>

  <div class="container">
    <div id="resultado" style="display:none;"></div>

    <form id="form" class="card" autocomplete="off">
      <!-- Cédula -->
      <div class="field">
        <label>Tu cédula *</label>
        <input id="cedula" type="tel" inputmode="numeric" pattern="[0-9]*" placeholder="Solo números" maxlength="20" required>
        <div class="help">Validamos contra el registro de empleados.</div>
      </div>

      <!-- Tipo (botones grandes) -->
      <div class="field">
        <label>¿Qué quieres reportar? *</label>
        <div class="tipos" id="tipos">
          <button type="button" class="tipo-btn" data-tipo="permiso"><span class="icon">🗓️</span><span>Permiso</span></button>
          <button type="button" class="tipo-btn" data-tipo="cita_medica"><span class="icon">🏥</span><span>Cita médica</span></button>
          <button type="button" class="tipo-btn" data-tipo="salud"><span class="icon">💊</span><span>Estado salud</span></button>
          <button type="button" class="tipo-btn" data-tipo="enfermedad"><span class="icon">🤒</span><span>Enfermedad</span></button>
          <button type="button" class="tipo-btn" data-tipo="licencia"><span class="icon">📄</span><span>Licencia</span></button>
          <button type="button" class="tipo-btn" data-tipo="otro"><span class="icon">📝</span><span>Otro</span></button>
        </div>
      </div>

      <!-- Asunto -->
      <div class="field">
        <label>Asunto / título *</label>
        <input id="asunto" type="text" placeholder="Ej: Permiso para cita el viernes 9 de mayo" maxlength="200" required>
      </div>

      <!-- Fechas -->
      <div class="field row">
        <div>
          <label>Desde</label>
          <input id="fecha_inicio" type="date">
        </div>
        <div>
          <label>Hasta</label>
          <input id="fecha_fin" type="date">
        </div>
      </div>

      <!-- Descripción -->
      <div class="field">
        <label>Descripción / detalles</label>
        <textarea id="descripcion" placeholder="Cuéntanos los detalles..." maxlength="2000"></textarea>
      </div>

      <!-- Adjunto URL -->
      <div class="field">
        <label>Link de evidencia (opcional)</label>
        <input id="adjunto_url" type="url" placeholder="https://... incapacidad, cita, etc.">
        <div class="help">Sube la foto a Drive/imgur y pega el link aquí.</div>
      </div>

      <button type="submit" class="submit" id="btn-submit">📨 Enviar reporte</button>
    </form>

    <div style="text-align:center;color:#64748b;font-size:11px;padding:20px 10px;">
      Sistema EOS · HHA Group<br>
      Si tu reporte es URGENTE llama directo a RH.
    </div>
  </div>

<script>
var TIPO_SELECCIONADO = '';

document.querySelectorAll('.tipo-btn').forEach(function(b){
  b.addEventListener('click', function(){
    document.querySelectorAll('.tipo-btn').forEach(function(x){ x.classList.remove('active'); });
    b.classList.add('active');
    TIPO_SELECCIONADO = b.dataset.tipo;
  });
});

function showMsg(html, ok) {
  var el = document.getElementById('resultado');
  el.className = 'msg ' + (ok ? 'ok' : 'err');
  el.innerHTML = html;
  el.style.display = 'block';
  window.scrollTo(0, 0);
}

document.getElementById('form').addEventListener('submit', async function(ev){
  ev.preventDefault();
  var btn = document.getElementById('btn-submit');
  btn.disabled = true;
  btn.textContent = 'Enviando...';

  if (!TIPO_SELECCIONADO) {
    showMsg('Selecciona un tipo de reporte', false);
    btn.disabled = false; btn.textContent = '📨 Enviar reporte';
    return;
  }

  var payload = {
    cedula: (document.getElementById('cedula').value || '').replace(/\D/g, ''),
    tipo: TIPO_SELECCIONADO,
    asunto: document.getElementById('asunto').value.trim(),
    descripcion: document.getElementById('descripcion').value.trim(),
    fecha_inicio: document.getElementById('fecha_inicio').value || null,
    fecha_fin: document.getElementById('fecha_fin').value || null,
    adjunto_url: document.getElementById('adjunto_url').value.trim() || null,
  };

  try {
    var r = await fetch('/api/publico/empleado-reporte', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload),
    });
    var d = await r.json();
    if (r.ok && d.ok) {
      showMsg('✓ ' + (d.mensaje || 'Reporte enviado correctamente'), true);
      // Limpiar formulario
      document.getElementById('form').reset();
      document.querySelectorAll('.tipo-btn').forEach(function(x){ x.classList.remove('active'); });
      TIPO_SELECCIONADO = '';
      btn.textContent = '✓ Enviado';
    } else {
      showMsg('⚠ ' + (d.error || 'No se pudo enviar'), false);
      btn.disabled = false;
      btn.textContent = '📨 Enviar reporte';
    }
  } catch(e) {
    showMsg('⚠ Error de conexión. Revisa tu internet e intenta de nuevo.', false);
    btn.disabled = false;
    btn.textContent = '📨 Enviar reporte';
  }
});
</script>
</body>
</html>
"""
