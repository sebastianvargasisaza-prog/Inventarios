"""Pantalla para asignar área de planta a cada producción próxima.

Sebastián 2-may-2026: Alejandro quiere organizar fabricaciones por sala
(FAB1, FYE2, etc.). Esta pantalla:
  1. Lista producciones próximas N días.
  2. Para cada una: dropdown con todas las áreas + sugerencia automática.
  3. Botones "Aplicar sugerencias" + "Confirmar cambios".
  4. Muestra warnings de conflicto (misma sala mismo día).
"""

ASIGNAR_AREAS_HTML = r'''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Asignar áreas · Producciones</title>
<style>
  * { box-sizing: border-box; }
  body {
    margin: 0; font-family: -apple-system, "Segoe UI", Roboto, sans-serif;
    background: #f5f5f5; color: #1f2937; padding: 20px;
  }
  .container { max-width: 1300px; margin: 0 auto; }
  h1 { font-size: 24px; margin: 0 0 4px 0; color: var(--cx-text); }
  .subtitle { font-size: 13px; color: var(--cx-text-mute); }
  .nav { font-size: 12px; margin: 8px 0 18px 0; }
  .nav a { color: #2B7A78; text-decoration: none; margin-right: 14px; }

  .resumen {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 12px; margin-bottom: 18px;
  }
  .pill {
    background: var(--cx-card); border: 1px solid var(--cx-border); border-radius: 10px;
    padding: 14px 16px; text-align: center;
  }
  .pill .num { font-size: 28px; font-weight: 800; line-height: 1; }
  .pill .lbl { font-size: 11px; color: var(--cx-text-mute); text-transform: uppercase;
                letter-spacing: 0.4px; margin-top: 6px; }
  .pill.warn    { border-left: 4px solid var(--cx-warn); }
  .pill.warn .num { color: var(--cx-warn-text); }
  .pill.info    { border-left: 4px solid var(--cx-info); }
  .pill.info .num { color: var(--cx-info-text); }

  .toolbar {
    background: var(--cx-card); border: 1px solid var(--cx-border); border-radius: 10px;
    padding: 12px 16px; margin-bottom: 14px;
    display: flex; flex-wrap: wrap; gap: 12px; align-items: center;
  }
  .toolbar label { font-size: 13px; color: var(--cx-text-soft); }
  .toolbar input[type="number"] {
    width: 70px; padding: 6px 8px; border: 1px solid var(--cx-border);
    border-radius: 6px; font-size: 14px;
  }
  .toolbar button {
    padding: 8px 14px; border: 0; border-radius: 6px; font-weight: 600;
    cursor: pointer; font-size: 13px;
  }
  .btn-primary { background: #2B7A78; color: #fff; }
  .btn-primary:hover { background: #1d5856; }
  .btn-primary:disabled { background: var(--cx-text-faint); cursor: not-allowed; }
  .btn-secondary { background: var(--cx-border); color: var(--cx-text-soft); }
  .btn-secondary:hover { background: var(--cx-border); }
  .btn-warn { background: var(--cx-warn); color: #fff; }
  .btn-warn:hover { background: var(--cx-accent-dark); }

  .ayuda {
    background: var(--cx-info-pale); border: 1px solid #bfdbfe; border-radius: 8px;
    padding: 12px 16px; margin-bottom: 14px; font-size: 13px; color: var(--cx-info-text);
  }
  .ayuda b { color: #1e3a8a; }
  .ayuda code {
    background: var(--cx-info-pale); padding: 1px 5px; border-radius: 3px;
    font-family: ui-monospace, "Courier New", monospace; font-size: 12px;
  }

  table {
    width: 100%; border-collapse: collapse; background: var(--cx-card);
    border: 1px solid var(--cx-border); border-radius: 10px; overflow: hidden;
  }
  th {
    background: var(--cx-bg-alt); padding: 10px 12px; text-align: left;
    font-size: 11px; font-weight: 600; color: var(--cx-text-soft);
    text-transform: uppercase; letter-spacing: 0.4px;
    border-bottom: 1px solid var(--cx-border);
  }
  td {
    padding: 10px 12px; border-bottom: 1px solid var(--cx-border-soft); font-size: 13px;
    vertical-align: middle;
  }
  tr:last-child td { border-bottom: 0; }
  tr.changed { background: #fef9c3; }
  tr.no-area { background: var(--cx-danger-pale); }
  tr.no-area:hover, tr.changed:hover { filter: brightness(0.97); }

  .producto { font-weight: 600; color: var(--cx-text); }
  .meta { font-size: 11px; color: var(--cx-text-mute); margin-top: 2px; }
  .badge {
    display: inline-block; padding: 2px 8px; border-radius: 4px;
    font-size: 10px; font-weight: 700; letter-spacing: 0.4px;
    text-transform: uppercase;
  }
  .badge.ale { background: var(--cx-warn-pale); color: var(--cx-warn-text); }
  .badge.cal { background: var(--cx-info-pale); color: var(--cx-info-text); }
  .badge.urg { background: var(--cx-danger-pale); color: var(--cx-danger-text); }
  .badge.sin { background: var(--cx-danger-pale); color: var(--cx-danger-text); }
  .badge.sug { background: var(--cx-success-pale); color: var(--cx-success-text); }

  select {
    padding: 6px 8px; border: 1px solid var(--cx-border); border-radius: 6px;
    font-size: 13px; background: var(--cx-card); min-width: 130px; max-width: 200px;
  }
  select.changed { border-color: var(--cx-warn); background: var(--cx-warn-pale); }

  .empty {
    text-align: center; padding: 40px 20px; color: var(--cx-text-mute);
    font-size: 14px;
  }

  .toast {
    position: fixed; bottom: 20px; right: 20px;
    background: var(--cx-success); color: #fff; padding: 12px 18px;
    border-radius: 8px; font-size: 14px; font-weight: 600;
    box-shadow: 0 4px 12px rgba(0,0,0,.15);
    opacity: 0; transition: opacity .25s; pointer-events: none;
  }
  .toast.show { opacity: 1; }
  .toast.err { background: var(--cx-danger); }

  .warnings {
    background: var(--cx-warn-pale); border: 1px solid #fcd34d; border-radius: 8px;
    padding: 12px 16px; margin: 14px 0; font-size: 13px; color: var(--cx-warn-text);
  }
  .warnings ul { margin: 6px 0 0 18px; padding: 0; }
</style>
</head>
<body>
<div class="container">
  <h1>Asignar áreas · Producciones</h1>
  <div class="subtitle">Pantalla para que Alejandro asigne sala a cada producción próxima.</div>
  <div class="nav">
    <a href="/inventarios">← Inventarios</a>
    <a href="/programacion-areas">Cronograma por área</a>
    <a href="/programacion-comparar">Alejandro vs Calendar</a>
  </div>

  <div class="ayuda">
    <b>Cómo usar:</b> Cada producción aparece con su área actual + una sugerencia
    (verde) calculada por fórmula y tamaño de lote. Cambiá lo que necesites con
    el dropdown - las filas modificadas se marcan en amarillo. Al final, click
    <b>Confirmar cambios</b>.<br>
    <b>Tip:</b> Si en Google Calendar empezás el evento con
    <code>[FAB1]</code>, <code>[FYE2]</code>, <code>[FYE3]</code>,
    <code>[ENV1]</code> o <code>[ENV2]</code>, el sistema lo asigna solo en
    el próximo sync.
  </div>

  <div id="resumen" class="resumen"></div>

  <div class="toolbar">
    <label>Horizonte:
      <input type="number" id="dias" min="1" max="180" value="30">
      días
    </label>
    <label>
      <input type="checkbox" id="solo_sin_area"> solo sin área
    </label>
    <button class="btn-secondary" onclick="cargar()">Recargar</button>
    <button class="btn-warn" onclick="aplicarSugerencias()" id="btn-sug">
      Aplicar sugerencias
    </button>
    <button class="btn-secondary" onclick="resetCambios()" id="btn-reset" disabled>
      Descartar cambios
    </button>
    <span style="flex:1"></span>
    <button class="btn-primary" onclick="confirmar()" id="btn-confirm" disabled>
      Confirmar cambios <span id="cnt-cambios"></span>
    </button>
  </div>

  <div id="warnings"></div>
  <div id="tabla-wrap"></div>
</div>

<div id="toast" class="toast"></div>

<script>
var DATOS = null;       // payload del GET
var CAMBIOS = {};       // {pid: nuevo_area_id_o_null}

function fmtFecha(iso) {
  if (!iso) return '';
  var d = new Date(iso + 'T00:00:00');
  var dias = ['Dom','Lun','Mar','Mié','Jue','Vie','Sáb'];
  var meses = ['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic'];
  return dias[d.getDay()] + ' ' + d.getDate() + ' ' + meses[d.getMonth()];
}

function fmtKg(kg) {
  if (!kg || kg <= 0) return '-';
  if (kg >= 1) return kg.toFixed(1).replace(/\.0$/, '') + ' kg';
  return Math.round(kg * 1000) + ' g';
}

function toast(msg, esError) {
  var el = document.getElementById('toast');
  el.textContent = msg;
  el.className = 'toast show' + (esError ? ' err' : '');
  setTimeout(function(){ el.className = 'toast'; }, 3000);
}

function actualizarBotones() {
  var n = Object.keys(CAMBIOS).length;
  var btn = document.getElementById('btn-confirm');
  var rst = document.getElementById('btn-reset');
  btn.disabled = (n === 0);
  rst.disabled = (n === 0);
  document.getElementById('cnt-cambios').textContent =
    n > 0 ? '(' + n + ')' : '';
}

function onCambio(pid, nuevoVal) {
  pid = parseInt(pid, 10);
  var nuevo = nuevoVal === '' ? null : parseInt(nuevoVal, 10);
  var item = DATOS.producciones.find(function(x){ return x.id === pid; });
  if (!item) return;
  var actual = item.area_id_actual;
  // Si vuelve al valor original, lo quita de cambios
  if (nuevo === actual || (nuevo === null && actual === null)) {
    delete CAMBIOS[pid];
  } else {
    CAMBIOS[pid] = nuevo;
  }
  // Marca visual
  var tr = document.getElementById('tr-' + pid);
  var sel = document.getElementById('sel-' + pid);
  if (CAMBIOS[pid] !== undefined) {
    tr.classList.add('changed');
    sel.classList.add('changed');
  } else {
    tr.classList.remove('changed');
    sel.classList.remove('changed');
  }
  actualizarBotones();
}

function aplicarSugerencias() {
  if (!DATOS) return;
  var aplicados = 0;
  DATOS.producciones.forEach(function(item) {
    if (item.area_id_actual === null && item.area_sugerida_id !== null) {
      CAMBIOS[item.id] = item.area_sugerida_id;
      var sel = document.getElementById('sel-' + item.id);
      if (sel) {
        sel.value = String(item.area_sugerida_id);
        sel.classList.add('changed');
      }
      var tr = document.getElementById('tr-' + item.id);
      if (tr) tr.classList.add('changed');
      aplicados++;
    }
  });
  toast(aplicados + ' sugerencias aplicadas (sin guardar todavía)');
  actualizarBotones();
}

function resetCambios() {
  CAMBIOS = {};
  if (!DATOS) return;
  DATOS.producciones.forEach(function(item) {
    var sel = document.getElementById('sel-' + item.id);
    if (sel) {
      sel.value = item.area_id_actual === null ? '' : String(item.area_id_actual);
      sel.classList.remove('changed');
    }
    var tr = document.getElementById('tr-' + item.id);
    if (tr) tr.classList.remove('changed');
  });
  actualizarBotones();
}

function buildOptions(item) {
  var opts = '<option value="">- sin área -</option>';
  DATOS.areas_disponibles.forEach(function(a) {
    var sel = (item.area_id_actual === a.id) ? ' selected' : '';
    var hint = '';
    if (a.especial) hint += ' · ' + a.especial;
    if (a.marmita_ml) hint += ' · ' + a.marmita_ml + 'ml';
    opts += '<option value="' + a.id + '"' + sel + '>' +
            a.codigo + ' (' + a.nombre + ')' + hint + '</option>';
  });
  return opts;
}

function render() {
  if (!DATOS) return;
  // Resumen
  var resumen = document.getElementById('resumen');
  resumen.innerHTML =
    '<div class="pill info"><div class="num">' + DATOS.total + '</div>' +
      '<div class="lbl">Producciones</div></div>' +
    '<div class="pill warn"><div class="num">' + DATOS.sin_area + '</div>' +
      '<div class="lbl">Sin área asignada</div></div>' +
    '<div class="pill info"><div class="num">' + DATOS.horizonte_dias + '</div>' +
      '<div class="lbl">Días horizonte</div></div>';

  // Tabla
  var wrap = document.getElementById('tabla-wrap');
  if (DATOS.producciones.length === 0) {
    wrap.innerHTML = '<div class="empty">No hay producciones en el horizonte.</div>';
    return;
  }
  var html = '<table><thead><tr>' +
    '<th>Fecha</th>' +
    '<th>Producto</th>' +
    '<th>Lotes / kg</th>' +
    '<th>Origen</th>' +
    '<th>Área actual</th>' +
    '<th>Sugerida</th>' +
    '<th>Asignar</th>' +
  '</tr></thead><tbody>';
  DATOS.producciones.forEach(function(item) {
    var sinArea = (item.area_id_actual === null);
    var sugBadge = item.area_sugerida_codigo
      ? '<span class="badge sug">' + item.area_sugerida_codigo + '</span>'
      : '-';
    var origen = item.origen === 'calendar'
      ? '<span class="badge cal">Calendar</span>'
      : '<span class="badge ale">Manual</span>';
    var areaActual = sinArea
      ? '<span class="badge sin">Sin área</span>'
      : (item.area_codigo_actual + ' · ' + (item.area_nombre_actual || ''));
    html += '<tr id="tr-' + item.id + '"' +
            (sinArea ? ' class="no-area"' : '') + '>' +
      '<td>' + fmtFecha(item.fecha) + '</td>' +
      '<td><div class="producto">' + (item.producto || '-') + '</div>' +
        '<div class="meta">id #' + item.id + ' · ' + item.estado + '</div></td>' +
      '<td>' + item.lotes + ' lote' + (item.lotes === 1 ? '' : 's') +
        '<div class="meta">' + fmtKg(item.cantidad_kg) + '</div></td>' +
      '<td>' + origen + '</td>' +
      '<td>' + areaActual + '</td>' +
      '<td>' + sugBadge + '</td>' +
      '<td><select id="sel-' + item.id + '" ' +
          'onchange="onCambio(' + item.id + ', this.value)">' +
        buildOptions(item) +
      '</select></td>' +
    '</tr>';
  });
  html += '</tbody></table>';
  wrap.innerHTML = html;
}

function csrf() {
  var m = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/);
  return m ? decodeURIComponent(m[1]) : '';
}

function cargar() {
  CAMBIOS = {};
  actualizarBotones();
  document.getElementById('warnings').innerHTML = '';
  var dias = document.getElementById('dias').value || '30';
  var solo = document.getElementById('solo_sin_area').checked ? '1' : '0';
  fetch('/api/planta/asignar-areas?dias=' + dias + '&solo_sin_area=' + solo, {
    credentials: 'same-origin'
  })
  .then(function(r){
    if (r.status === 401) { window.location = '/login?next=/asignar-areas'; throw 0; }
    return r.json();
  })
  .then(function(d){
    DATOS = d;
    render();
  })
  .catch(function(e){
    if (e === 0) return;
    toast('Error cargando datos', true);
    console.error(e);
  });
}

function confirmar() {
  var asignaciones = Object.keys(CAMBIOS).map(function(pid) {
    return { id: parseInt(pid, 10), area_id: CAMBIOS[pid] };
  });
  if (asignaciones.length === 0) return;
  var btn = document.getElementById('btn-confirm');
  btn.disabled = true;
  btn.textContent = 'Guardando...';
  fetch('/api/planta/asignar-areas', {
    method: 'POST',
    credentials: 'same-origin',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRF-Token': csrf()
    },
    body: JSON.stringify({ asignaciones: asignaciones })
  })
  .then(function(r){ return r.json().then(function(d){ return [r.status, d]; }); })
  .then(function(par){
    var status = par[0], d = par[1];
    if (status >= 400) {
      toast(d.error || 'Error guardando', true);
      btn.disabled = false;
      btn.innerHTML = 'Confirmar cambios <span id="cnt-cambios"></span>';
      actualizarBotones();
      return;
    }
    var msg = d.asignados + ' producciones asignadas';
    if (d.errores && d.errores.length) msg += ' · ' + d.errores.length + ' errores';
    toast(msg);
    // Mostrar warnings de conflicto si hay
    if (d.warnings && d.warnings.length) {
      var wHtml = '<div class="warnings"><b>Avisos de conflicto:</b><ul>';
      d.warnings.forEach(function(w){
        wHtml += '<li>' + w.producto + ' (' + w.fecha + ') · sala <b>' +
                 w.area_codigo + '</b> ya tiene: ' +
                 w.choca_con.map(function(x){ return x.producto; }).join(', ') +
                 '</li>';
      });
      wHtml += '</ul></div>';
      document.getElementById('warnings').innerHTML = wHtml;
    }
    if (d.errores && d.errores.length) {
      console.warn('Errores en asignaciones:', d.errores);
    }
    cargar();
  })
  .catch(function(e){
    toast('Error de red', true);
    btn.disabled = false;
    btn.innerHTML = 'Confirmar cambios <span id="cnt-cambios"></span>';
    actualizarBotones();
    console.error(e);
  });
}

document.getElementById('dias').addEventListener('change', cargar);
document.getElementById('solo_sin_area').addEventListener('change', cargar);
cargar();
</script>
</body>
</html>'''
