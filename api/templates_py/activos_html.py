"""Libro de activos · CEO (gerencia) + Tesorería · Sebastián 30-jul.

*"Esto es trazabilidad y plata, pero a la vez nos permite hacer seguimientos · como CEO debo
verlo, Tesorería también, y todo lo que llegue se debe recepcionar"*.

El maestro vivía en un Excel: el valor de la empresa dependía de que nadie perdiera un archivo.
Materias primas y envases NO están acá (decisión suya): son inventario VIVO que varía con el uso
y ya tienen su kardex.

`valor_en_libros` se DERIVA del estado — un activo de baja, hurtado o fuera de uso deja de sumar
y la fila se conserva con su motivo. Un total tecleado queda viejo el día que alguien se olvida.
"""

ACTIVOS_HTML = r'''<!DOCTYPE html>
<html lang="es" translate="no">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Libro de activos · EOS</title>
<link rel="stylesheet" href="/static/cortex.css?v=eos15">
<style>
body{font-family:"Inter",system-ui,-apple-system,Arial,sans-serif;background:var(--cx-bg);color:var(--cx-text);margin:0;padding:22px 2vw 60px}
.wrap{width:96vw;max-width:1720px;margin:0 auto}
.hero{display:flex;align-items:center;gap:15px;margin-bottom:4px}
.hero .ic{width:50px;height:50px;border-radius:15px;background:var(--cx-primary-grad);display:flex;align-items:center;justify-content:center;font-size:24px;flex-shrink:0}
.hero h1{margin:0;font-size:23px;letter-spacing:-.02em;font-weight:800}
.hero .who{margin-left:auto;font-size:12px;color:var(--cx-text-mute);text-align:right}
.sub{color:var(--cx-text-soft);font-size:13.5px;margin:4px 0 18px;max-width:940px;line-height:1.5}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:13px;margin-bottom:18px}
.kpi{background:var(--cx-surface);border:1px solid var(--cx-border);border-radius:15px;padding:15px 17px;position:relative;overflow:hidden}
.kpi::after{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--cx-border)}
.kpi.v::after{background:var(--cx-success)}.kpi.p::after{background:var(--cx-primary)}.kpi.x::after{background:var(--cx-danger)}.kpi.w::after{background:var(--cx-warn)}
.kpi .n{font-size:26px;font-weight:800;letter-spacing:-.03em;line-height:1.05}
.kpi .l{font-size:11px;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:.05em;font-weight:700;margin-top:3px}
.kpi .d{font-size:11.5px;color:var(--cx-text-soft);margin-top:4px}
.bar{display:flex;gap:9px;flex-wrap:wrap;align-items:center;margin-bottom:14px}
.bar input.q{flex:1;min-width:230px;max-width:420px}
.fchip{border:1px solid var(--cx-border);background:var(--cx-surface);color:var(--cx-text-soft);border-radius:22px;padding:7px 15px;font-size:12.5px;font-weight:700;cursor:pointer}
.fchip.on{background:var(--cx-primary-grad);color:#fff;border-color:transparent}
.panel{background:var(--cx-surface);border:1px solid var(--cx-border);border-radius:16px;overflow:auto}
table{width:100%;border-collapse:collapse;font-size:13px}
th{background:var(--cx-bg-alt);text-align:left;padding:11px 13px;font-size:10.5px;text-transform:uppercase;letter-spacing:.05em;color:var(--cx-text-mute);font-weight:800;white-space:nowrap;position:sticky;top:0;z-index:2}
td{padding:10px 13px;border-top:1px solid var(--cx-border);vertical-align:middle}
tbody tr:hover{background:var(--cx-bg-alt)}
.cod{font-family:ui-monospace,monospace;font-weight:800;color:var(--cx-primary-text)}
.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.chip{display:inline-block;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:800;white-space:nowrap}
.c-ok{background:var(--cx-success-pale);color:var(--cx-success-text)}
.c-warn{background:var(--cx-warn-pale);color:var(--cx-warn-text)}
.c-out{background:var(--cx-danger-pale);color:var(--cx-danger-text)}
tr.fuera td{opacity:.62}
.empty{padding:38px;text-align:center;color:var(--cx-text-mute);font-size:13.5px}
.imp{background:var(--cx-primary-pale);border:1px solid var(--cx-primary-soft);border-radius:14px;padding:14px 17px;margin-bottom:16px}
.imp h3{margin:0 0 4px;font-size:14px;font-weight:800;color:var(--cx-primary-text)}
.imp p{margin:0 0 10px;font-size:12.5px;color:var(--cx-text-soft);line-height:1.5}
#imp-out{font-size:12.5px;color:var(--cx-text-soft);margin-top:10px;line-height:1.55}
@media(max-width:820px){.hero .who{display:none}}
</style>
</head>
<body>
<div class="wrap">
  <div class="hero">
    <div class="ic">&#127974;</div>
    <div>
      <h1>Libro de activos</h1>
      <div class="sub" style="margin:2px 0 0">Gerencia &middot; Tesorer&iacute;a</div>
    </div>
    <div class="who"><a href="/financiero" class="cx-btn cx-btn-ghost cx-btn-sm">&#8592; Financiero</a></div>
  </div>
  <div class="sub">Qu&eacute; tiene la empresa, d&oacute;nde est&aacute;, qui&eacute;n responde por ello y cu&aacute;nto vale.
  <b>El valor en libros se calcula</b>: un activo dado de baja, hurtado o fuera de uso deja de sumar, y la fila se
  conserva con su motivo. Materias primas y envases no est&aacute;n ac&aacute;: var&iacute;an con el uso y viven en el kardex.</div>

  <div class="imp">
    <h3>&#128228; Cargar el Excel maestro</h3>
    <p>Da de alta y actualiza. <b>Nunca borra</b>: si un activo del sistema no viene en el archivo, queda listado
    para que vos decidas. Primero muestra el plan; s&oacute;lo escribe cuando lo confirm&aacute;s.</p>
    <input type="file" id="imp-file" accept=".xlsx" class="cx-input" style="max-width:420px">
    <button class="cx-btn cx-btn-sm" onclick="actImportar(true)">Ver qu&eacute; pasar&iacute;a</button>
    <button class="cx-btn cx-btn-sm" id="imp-apply" style="background:var(--cx-primary);color:#fff;display:none" onclick="actImportar(false)">Aplicar</button>
    <div id="imp-out"></div>
  </div>

  <div class="kpis" id="kpis"></div>

  <div class="bar">
    <input class="cx-input q" id="q" placeholder="Buscar por c&oacute;digo, nombre, responsable o ubicaci&oacute;n..." oninput="actPintar()">
    <button class="fchip on" data-f="todos" onclick="actFiltrar(this)">Todos</button>
    <button class="fchip" data-f="libros" onclick="actFiltrar(this)">En libros</button>
    <button class="fchip" data-f="fuera" onclick="actFiltrar(this)">Fuera de libros</button>
    <button class="fchip" data-f="danado" onclick="actFiltrar(this)">Da&ntilde;ados</button>
    <button class="fchip" data-f="sinrot" onclick="actFiltrar(this)">Sin rotular</button>
    <button class="cx-btn cx-btn-ghost cx-btn-sm" style="margin-left:auto" onclick="actCargar()">Actualizar</button>
  </div>

  <div class="panel">
    <table>
      <thead><tr>
        <th>C&oacute;digo</th><th>Activo</th><th>Empresa</th><th>Ubicaci&oacute;n</th><th>Responsable</th>
        <th>Estado</th><th class="num">Costo</th><th class="num">En libros</th><th></th>
      </tr></thead>
      <tbody id="tb"><tr><td colspan="9" class="empty">Cargando...</td></tr></tbody>
    </table>
  </div>
</div>

<script>
var DATA = [], FILTRO = 'todos', FUERA = [];
function esc(s){ var d=document.createElement('div'); d.textContent=(s===null||s===undefined)?'':String(s); return d.innerHTML; }
function cop(n){ return '$' + Number(n||0).toLocaleString('es-CO', {maximumFractionDigits:0}); }
function _csrf(){ var m=document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/); return m?decodeURIComponent(m[1]):''; }

async function actCargar(){
  try{
    var r = await fetch('/api/activos', {credentials:'same-origin'});
    var d = await r.json();
    if(!r.ok || !d.ok){ document.getElementById('tb').innerHTML='<tr><td colspan="9" class="empty">'+esc(d.error||'Error')+'</td></tr>'; return; }
    DATA = d.items || []; FUERA = d.estados_fuera_de_libros || [];
    var k = '';
    k += '<div class="kpi v"><div class="n">'+cop(d.valor_en_libros_total)+'</div><div class="l">Valor en libros</div><div class="d">'+(d.total||0)+' activos registrados</div></div>';
    Object.keys(d.por_empresa||{}).sort().forEach(function(emp){
      var e = d.por_empresa[emp];
      k += '<div class="kpi p"><div class="n">'+cop(e.valor)+'</div><div class="l">'+esc(emp)+'</div>'+
           '<div class="d">'+e.activos+' activos'+(e.fuera? ' &middot; '+e.fuera+' fuera de libros':'')+'</div></div>';
    });
    var sinRot = DATA.filter(function(x){ return !x.rotulado; }).length;
    if(sinRot) k += '<div class="kpi w"><div class="n">'+sinRot+'</div><div class="l">Sin rotular</div><div class="d">no tienen la placa pegada</div></div>';
    var fuera = DATA.filter(function(x){ return !x.en_libros; }).length;
    if(fuera) k += '<div class="kpi x"><div class="n">'+fuera+'</div><div class="l">Fuera de libros</div><div class="d">de baja, hurto o fuera de uso</div></div>';
    document.getElementById('kpis').innerHTML = k;
    actPintar();
  }catch(e){ document.getElementById('tb').innerHTML='<tr><td colspan="9" class="empty">Error de red</td></tr>'; }
}

function actFiltrar(btn){
  FILTRO = btn.getAttribute('data-f');
  document.querySelectorAll('.fchip').forEach(function(b){ b.classList.toggle('on', b===btn); });
  actPintar();
}

function actPintar(){
  var q = (document.getElementById('q').value||'').toLowerCase().trim();
  var filas = DATA.filter(function(x){
    if(FILTRO==='libros' && !x.en_libros) return false;
    if(FILTRO==='fuera' && x.en_libros) return false;
    if(FILTRO==='danado' && String(x.estado||'').toLowerCase().indexOf('da')!==0) return false;
    if(FILTRO==='sinrot' && x.rotulado) return false;
    if(!q) return true;
    return [x.codigo,x.nombre,x.responsable,x.ubicacion,x.empresa,x.serial].join(' ').toLowerCase().indexOf(q)>=0;
  });
  if(!filas.length){ document.getElementById('tb').innerHTML='<tr><td colspan="9" class="empty">Nada que mostrar con ese filtro.</td></tr>'; return; }
  document.getElementById('tb').innerHTML = filas.map(function(x){
    var cls = x.en_libros ? (String(x.estado||'').toLowerCase().indexOf('da')===0 ? 'c-warn' : 'c-ok') : 'c-out';
    var acc = x.en_libros
      ? '<button class="cx-btn cx-btn-ghost cx-btn-sm" data-cod="'+esc(x.codigo)+'" onclick="actBaja(this)">Dar de baja</button>'
      : '<button class="cx-btn cx-btn-ghost cx-btn-sm" data-cod="'+esc(x.codigo)+'" onclick="actRevertir(this)">Revertir</button>';
    return '<tr class="'+(x.en_libros?'':'fuera')+'">'
      +'<td class="cod">'+esc(x.codigo)+'</td>'
      +'<td><b>'+esc(x.nombre)+'</b>'+(x.tipo_bien?'<div style="font-size:11px;color:var(--cx-text-mute)">'+esc(x.tipo_bien)+'</div>':'')+'</td>'
      +'<td>'+esc(x.empresa)+'</td>'
      +'<td>'+esc(x.ubicacion||'-')+'</td>'
      +'<td>'+esc(x.responsable||'-')+'</td>'
      +'<td><span class="chip '+cls+'">'+esc(x.estado)+'</span>'
        +(x.baja_motivo?'<div style="font-size:11px;color:var(--cx-text-mute);margin-top:3px">'+esc(x.baja_motivo)+'</div>':'')+'</td>'
      +'<td class="num">'+cop(x.costo_cop)+'</td>'
      +'<td class="num"><b>'+(x.en_libros?cop(x.valor_en_libros):'&mdash;')+'</b></td>'
      +'<td>'+acc+'</td></tr>';
  }).join('');
}

async function actBaja(btn){
  var cod = btn.getAttribute('data-cod')||'';
  var estado = prompt('Estado de la baja de '+cod+':\n\nDe baja / Hurto / Fuera de uso', 'De baja');
  if(!estado) return;
  var motivo = prompt('Motivo (queda en el libro y en la auditoria):');
  if(!motivo || !motivo.trim()){ alert('Sin motivo no se puede: es plata que sale del valor en libros.'); return; }
  try{
    var r = await fetch('/api/activos/'+encodeURIComponent(cod)+'/baja', {method:'POST', credentials:'same-origin',
      headers:{'Content-Type':'application/json','X-CSRF-Token':_csrf()},
      body: JSON.stringify({estado: estado.trim(), motivo: motivo.trim()})});
    var d = await r.json();
    if(!r.ok || !d.ok){ alert('No se pudo: '+((d&&d.error)||r.status)); return; }
    alert('Listo. Salen '+cop(d.valor_que_sale)+' del valor en libros.');
    actCargar();
  }catch(e){ alert('Error de red.'); }
}

async function actRevertir(btn){
  var cod = btn.getAttribute('data-cod')||'';
  if(!confirm('Revertir la baja de '+cod+'? Vuelve a sumar al valor en libros.')) return;
  try{
    var r = await fetch('/api/activos/'+encodeURIComponent(cod)+'/baja', {method:'POST', credentials:'same-origin',
      headers:{'Content-Type':'application/json','X-CSRF-Token':_csrf()},
      body: JSON.stringify({revertir:true, estado:'En uso', motivo:'Reversion desde el libro'})});
    var d = await r.json();
    if(!r.ok || !d.ok){ alert('No se pudo: '+((d&&d.error)||r.status)); return; }
    actCargar();
  }catch(e){ alert('Error de red.'); }
}

async function actImportar(dry){
  var f = document.getElementById('imp-file').files[0];
  var out = document.getElementById('imp-out');
  if(!f){ out.textContent = 'Elegi primero el archivo .xlsx'; return; }
  out.textContent = dry ? 'Leyendo el archivo...' : 'Aplicando...';
  var fd = new FormData(); fd.append('archivo', f);
  try{
    var r = await fetch('/api/activos/importar?dry_run='+(dry?'1':'0'), {method:'POST', credentials:'same-origin',
      headers:{'X-CSRF-Token':_csrf()}, body: fd});
    var d = await r.json();
    if(!r.ok || !d.ok){ out.innerHTML = '<span style="color:var(--cx-danger-text)">'+esc((d&&d.error)||('HTTP '+r.status))+'</span>'; return; }
    var h = '<b>'+d.en_archivo+'</b> activos en el archivo &middot; <b>'+d.nuevos+'</b> nuevos &middot; <b>'+d.actualizan+'</b> se actualizan';
    if(d.no_vienen_en_el_archivo) h += ' &middot; <b>'+d.no_vienen_en_el_archivo+'</b> ya estaban en EOS y no vienen en el archivo';
    if(d.aviso) h += '<br><span style="color:var(--cx-warn-text)">'+esc(d.aviso)+'</span>';
    if(dry){
      h += '<br><b>Nada se escribio todavia.</b> Si esto es lo esperado, dale Aplicar.';
      document.getElementById('imp-apply').style.display='';
    }else{
      h += '<br><b style="color:var(--cx-success-text)">Aplicado.</b>';
      document.getElementById('imp-apply').style.display='none';
      actCargar();
    }
    out.innerHTML = h;
  }catch(e){ out.innerHTML = '<span style="color:var(--cx-danger-text)">Error de red</span>'; }
}

actCargar();
</script>
</body>
</html>
'''
