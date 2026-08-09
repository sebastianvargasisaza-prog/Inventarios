# -*- coding: utf-8 -*-
"""Pantalla para NORMALIZAR el empaque: una fila por presentacion, una columna por componente.

Sebastian (8-ago): *"ese modulo asi no me sirve, quiero que sea producto, envase, tapa, etiqueta
etc, que arrastre todo por nombre, me deje vacio lo que no es, y me deje poner NO USA, porque no
he sido capaz, asi me tengas que abrir en otra ventana"*.

Lo anterior era una lista de PENDIENTES; esto es una tabla donde se CARGA. La diferencia no es
cosmetica: una lista dice que falta, una tabla deja avanzar.

⚠ Va en archivo propio y no dentro de `dashboard_html.py` a proposito: ese archivo tiene dos
millones de caracteres y un error de sintaxis ahi rompe el bundle entero y deja pantallas en
blanco (paso dos veces el mismo dia). Una pantalla nueva que puede vivir sola, vive sola.
"""

NORMALIZAR_ENVASES_HTML = r"""<!DOCTYPE html><html lang="es"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Normalizar empaque</title><link rel="stylesheet" href="/static/cortex.css">
<style>
 body{background:var(--cx-bg);color:var(--cx-text);font-family:Inter,system-ui,sans-serif;margin:0}
 .wrap{max-width:98vw;margin:0 auto;padding:18px}
 .hero{background:var(--cx-primary-grad);color:#fff;border-radius:14px;padding:16px 20px;
       display:flex;justify-content:space-between;align-items:center;gap:14px;flex-wrap:wrap}
 .hero h1{margin:0;font-size:18px;font-weight:800}
 .hero p{margin:4px 0 0;font-size:12.5px;opacity:.92;max-width:760px;line-height:1.5}
 .kpis{display:flex;gap:18px;flex-wrap:wrap;margin:14px 0}
 .kpi{background:var(--cx-card);border:1px solid var(--cx-border);border-radius:11px;
      padding:9px 15px;min-width:118px}
 .kpi b{display:block;font-size:19px;font-variant-numeric:tabular-nums}
 .kpi span{font-size:11px;color:var(--cx-text-soft);text-transform:uppercase;letter-spacing:.4px}
 .barra{display:flex;gap:9px;align-items:center;flex-wrap:wrap;margin-bottom:12px}
 input[type=text]{padding:8px 12px;border:1px solid var(--cx-border);border-radius:8px;
   background:var(--cx-bg-soft);color:var(--cx-text);font-size:13px;flex:1 1 240px}
 .btn{border:none;border-radius:8px;padding:8px 14px;font-size:12.5px;font-weight:700;cursor:pointer}
 .btn-p{background:var(--cx-primary-grad);color:#fff}
 .btn-s{background:var(--cx-bg-alt);color:var(--cx-text);border:1px solid var(--cx-border)}
 .tabla{background:var(--cx-card);border:1px solid var(--cx-border);border-radius:12px;
        overflow-x:auto}
 table{width:100%;border-collapse:collapse;font-size:12.5px}
 th{position:sticky;top:0;background:var(--cx-card);text-align:left;padding:9px 8px;
    color:var(--cx-text-soft);font-weight:700;border-bottom:1px solid var(--cx-border);z-index:1}
 td{padding:6px 8px;border-top:1px solid var(--cx-border-soft);vertical-align:middle}
 select{width:100%;min-width:150px;padding:5px 7px;border:1px solid var(--cx-border);
   border-radius:7px;background:var(--cx-bg-soft);color:var(--cx-text);font-size:11.5px}
 select.sug{border-color:var(--cx-primary);background:var(--cx-primary-soft)}
 select.nousa{color:var(--cx-text-faint);font-style:italic}
 select.vacio{border-color:var(--cx-warn)}
 .apag{opacity:.5}
 .pieop{font-size:10.5px;color:var(--cx-text-soft);margin-top:2px;line-height:1.25;word-break:break-word}
 .chip{display:inline-block;padding:1px 7px;border-radius:999px;font-size:10.5px;font-weight:700}
 .amb{background:var(--cx-warn-pale);color:var(--cx-warn-text)}
 .fan{background:var(--cx-danger-pale);color:var(--cx-danger-text)}
 .sos{background:var(--cx-danger-pale);color:var(--cx-danger-text);border:1px solid var(--cx-danger-text)}
 .prod{font-weight:600}
 .ml{font-variant-numeric:tabular-nums;color:var(--cx-text-soft)}
 .pie{position:sticky;bottom:0;background:var(--cx-card);border-top:1px solid var(--cx-border);
      padding:11px 14px;display:flex;gap:12px;align-items:center;flex-wrap:wrap;
      border-radius:0 0 12px 12px}
</style></head><body><div class="wrap">
<div class="hero">
  <div>
    <h1>&#128230; Normalizar el empaque</h1>
    <p>Una fila por presentaci&oacute;n y una columna por componente. Lo que se pudo deducir del
       NOMBRE viene propuesto y resaltado; lo que no tiene una respuesta clara queda <b>vac&iacute;o</b>
       a prop&oacute;sito. Si algo no lleva ese componente, eleg&iacute; <b>no usa</b> y deja de contar
       como pendiente.</p>
  </div>
  <a href="/inventarios" class="btn btn-s" style="text-decoration:none">&larr; Planta</a>
</div>
<div class="kpis" id="kpis"></div>
<div class="barra">
  <input type="text" id="q" placeholder="Buscar producto&hellip;" oninput="pintar()">
  <label style="font-size:12.5px;color:var(--cx-text-soft);display:flex;gap:6px;align-items:center;cursor:pointer">
    <input type="checkbox" id="solo" checked onchange="pintar()" style="width:15px;height:15px">
    Solo las incompletas
  </label>
  <label style="font-size:12.5px;color:var(--cx-text-soft);display:flex;gap:6px;align-items:center;cursor:pointer">
    <input type="checkbox" id="verapag" onchange="pintar()" style="width:15px;height:15px">
    Ver tambi&eacute;n las apagadas
  </label>
  <button class="btn btn-s" onclick="aceptarSugeridas()">Aceptar todas las sugeridas</button>
</div>
<div class="tabla">
  <div id="cuerpo" style="padding:26px;text-align:center;color:var(--cx-text-faint)">Cargando&hellip;</div>
  <div class="pie">
    <button class="btn btn-p" onclick="guardar()" id="btn-guardar">Guardar los cambios</button>
    <span id="estado" style="font-size:12.5px;color:var(--cx-text-soft)"></span>
  </div>
</div>
</div>
<script>
var D=null, CAMBIOS={};
function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){
  return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}

async function cargar(){
  try{
    var r=await fetch('/api/mee/normalizar-tabla',{credentials:'same-origin'});
    D=await r.json();
    if(!D.ok) throw new Error(D.error||'error');
  }catch(e){
    document.getElementById('cuerpo').innerHTML='<div style="color:var(--cx-danger-text);padding:20px">No pude cargar la tabla: '+esc(e)+'</div>';
    return;
  }
  pintar();
}

function valorDe(f, col){
  // Lo que la celda muestra: primero lo que el usuario cambio en esta sesion, despues lo
  // guardado, despues la sugerencia. Nunca se muestra una sugerencia encima de un dato real.
  var k=f.id+'|'+col;
  if(CAMBIOS[k]!==undefined) return CAMBIOS[k];
  if(f.no_usa[col]) return '__NO_USA__';
  if(f.actual[col]) return f.actual[col];
  if(f.sugerido[col]) return f.sugerido[col];
  return '';
}
function esSugerida(f, col){
  var k=f.id+'|'+col;
  return CAMBIOS[k]===undefined && !f.actual[col] && !f.no_usa[col] && !!f.sugerido[col];
}
function incompleta(f){
  var cols=D.columnas, i;
  for(i=0;i<cols.length;i++){
    var v=valorDe(f, cols[i]);
    if(!v) return true;
  }
  if(Object.keys(f.sospechoso||{}).length) return true;   // una guardada que hay que revisar
  if((f.de_baja||[]).length) return true;                 // apunta a un codigo dado de baja
  return (f.fantasma||[]).length>0;
}

function textoDe(col, sel){
  if(!sel) return '';
  if(sel==='__NO_USA__') return 'no usa';
  var lista=(D.catalogo[col]||[]), i, u=String(sel).toUpperCase();
  for(i=0;i<lista.length;i++){
    if(String(lista[i].codigo||'').toUpperCase()===u){
      return lista[i].codigo + (lista[i].desc?' · '+lista[i].desc:'')
           + (lista[i].medida?' · '+lista[i].medida:'')
           + (lista[i].activo===false?' · (de baja)':'');
    }
  }
  return sel;
}

function opciones(col, sel){
  var lista=(D.catalogo[col]||[]), h='<option value="">&mdash; sin definir &mdash;</option>';
  // 'No usa' solo donde tiene sentido: sin frasco no hay nada que envasar, asi que el envase no
  // puede declararse ausente.
  if(col!=='envase') h+='<option value="__NO_USA__"'+(sel==='__NO_USA__'?' selected':'')+'>no usa</option>';
  var vistos={}, i, corte=false;
  for(i=0;i<lista.length;i++){
    var c=lista[i].codigo, u=String(c||'').toUpperCase();
    vistos[u]=1;
    // Los dados de baja van al final y DICHOS. No se esconden -- si el que hace falta esta de
    // baja, esconderlo deja la columna vacia sin explicacion -- pero tampoco se mezclan con los
    // que se reponen: elegir uno de baja es apuntarle la compra a algo que nadie repone.
    if(lista[i].activo===false && !corte){
      corte=true;
      h+='<option disabled>&mdash;&mdash; dados de baja (no se reponen) &mdash;&mdash;</option>';
    }
    // La MEDIDA es lo que distingue a los que se llaman igual: los seis goteros dicen todos
    // "GOTERO" y lo unico que los separa es 89mm / 72mm / 65mm / 55mm.
    h+='<option value="'+esc(c)+'"'+(String(sel).toUpperCase()===u?' selected':'')+'>'
      + esc(c)+(lista[i].desc?' &middot; '+esc(lista[i].desc):'')
      + (lista[i].medida?' &middot; '+esc(lista[i].medida):'')
      + (lista[i].activo===false?' &middot; (de baja)':'')+'</option>';
  }
  // Un codigo cargado que ya no esta en el catalogo NO se borra de la vista: se muestra marcado.
  // Si desapareciera, el guardado lo pisaria con vacio sin que nadie lo haya decidido (M115).
  if(sel && sel!=='__NO_USA__' && !vistos[String(sel).toUpperCase()]){
    h+='<option value="'+esc(sel)+'" selected>'+esc(sel)+' (no esta en el maestro)</option>';
  }
  return h;
}

function pintar(){
  if(!D) return;
  var q=(document.getElementById('q').value||'').trim().toUpperCase();
  var solo=document.getElementById('solo').checked;
  var verApag=document.getElementById('verapag').checked;
  var filas=D.filas.filter(function(f){
    if(!verApag && !f.activo) return false;
    if(q && f.producto.toUpperCase().indexOf(q)<0) return false;
    if(solo && !incompleta(f)) return false;
    return true;
  });
  var listas=D.filas.filter(function(f){ return f.activo && !incompleta(f); }).length;
  var act=D.filas.filter(function(f){ return f.activo; }).length;
  document.getElementById('kpis').innerHTML=
      '<div class="kpi"><b>'+listas+' / '+act+'</b><span>completas</span></div>'
    + '<div class="kpi"><b>'+(D.resumen.se_arrastran||0)+'</b><span>se arrastran</span></div>'
    + '<div class="kpi"><b>'+(D.resumen.ambiguas||0)+'</b><span>ambiguas (vac&iacute;as)</span></div>'
    + '<div class="kpi"><b>'+Object.keys(CAMBIOS).length+'</b><span>sin guardar</span></div>';

  var h='<table><thead><tr><th>Producto</th><th>ml</th>';
  D.columnas.forEach(function(c){ h+='<th>'+esc(c)+'</th>'; });
  h+='</tr></thead><tbody>';
  filas.forEach(function(f){
    h+='<tr class="'+(f.activo?'':'apag')+'"><td class="prod">'+esc(f.producto)
      + (f.activo?'':' <span class="chip amb">apagada</span>')+'</td>'
      + '<td class="ml">'+(f.volumen_ml||'')+'</td>';
    D.columnas.forEach(function(col){
      var v=valorDe(f,col), cls=[];
      if(esSugerida(f,col)) cls.push('sug');
      if(v==='__NO_USA__') cls.push('nousa');
      if(!v) cls.push('vacio');
      // El nombre completo: el select cerrado lo recorta, asi que se pone tambien en `title`
      // (se ve al pasar el mouse) y la celda se deja crecer. Sebastian: *"tambien deben traer
      // aqui todo el nombre"* -- si no se lee entero, elegir es adivinar.
      var _txt = textoDe(col, v);
      h+='<td><select class="'+cls.join(' ')+'" title="'+esc(_txt)+'" '
        + 'onchange="cambio('+f.id+',&quot;'+esc(col)+'&quot;,this.value)">'
        + opciones(col, v)+'</select>'
        + (_txt?'<div class="pieop" title="'+esc(_txt)+'">'+esc(_txt)+'</div>':'');
      if((f.ambiguo||{})[col]) h+='<div class="chip amb" style="margin-top:3px">empatan: '+esc(f.ambiguo[col].join(' / '))+'</div>';
      if((f.fantasma||[]).indexOf(col)>=0) h+='<div class="chip fan" style="margin-top:3px">no esta en el maestro</div>';
      // Lo que YA esta guardado y nombra a OTRO producto. Hasta el 9-ago el emparejador proponia
      // por palabra de familia, asi que un "aceptar todas" pudo dejar la etiqueta del
      // retinaldehido en la cafeina: esa fila se ve RESUELTA, que es la peor forma de estar mal.
      if((f.de_baja||[]).indexOf(col)>=0)
        h+='<div class="chip fan" style="margin-top:3px">&#9888; ese codigo esta dado de baja</div>';
      if(((f.sospechoso||{})[col]||[]).length)
        h+='<div class="chip sos" style="margin-top:3px">&#9888; revisar: nombra a otro producto ('
          + esc(((f.sospechoso||{})[col]||[]).join(', ')) + ')</div>';
      h+='</td>';
    });
    h+='</tr>';
  });
  h+='</tbody></table>';
  if(!filas.length) h='<div style="padding:26px;text-align:center;color:var(--cx-success-text);font-weight:600">&#10004; No queda ninguna incompleta con ese filtro.</div>';
  document.getElementById('cuerpo').innerHTML=h;
}

function porId(id){ var i; for(i=0;i<(D.filas||[]).length;i++){ if(D.filas[i].id===id) return D.filas[i]; } return null; }

async function crearEmpaque(id, col){
  // Sebastian (9-ago): *"el usa etiqueta, quizas en este momento no hay, pero como hacemos? la
  // creamos y que aparezca en cero?"*. En cero es como corresponde: el motor compra
  // `necesidad - stock`, asi que una etiqueta que existe en cero pide TODA la necesidad, y una
  // que no existe no pide nada y el faltante queda invisible.
  var f=porId(id), sugerida=(f? (f.producto+' '+(f.etiqueta_txt||'')) : '');
  var desc=prompt('Descripcion del/la '+col+' que falta (con que producto es):', sugerida);
  if(desc===null || String(desc).trim().length<3){ pintar(); return; }
  try{
    var t=await (await fetch('/api/csrf-token',{credentials:'same-origin'})).json();
    var r=await fetch('/api/mee/normalizar-crear',{method:'POST',credentials:'same-origin',
      headers:{'Content-Type':'application/json','X-CSRF-Token':(t&&t.csrf_token)||''},
      body:JSON.stringify({columna:col, descripcion:String(desc).trim()})});
    var j=await r.json();
    if(!r.ok || !j.ok){
      alert(j.mensaje||j.error||'No se pudo crear');
      if(j.codigo){ CAMBIOS[id+'|'+col]=j.codigo; }   // ya existia: se usa ese, no se duplica
      await cargar();
      return;
    }
    D.catalogo[col].push({codigo:j.codigo, desc:j.descripcion});
    CAMBIOS[id+'|'+col]=j.codigo;
    pintar();
  }catch(e){ alert('No se pudo crear: '+e); await cargar(); }
}

function cambio(id, col, v){
  if(v==='__CREAR__'){ crearEmpaque(id, col); return; }
  CAMBIOS[id+'|'+col]=v; pintar();
}

function aceptarSugeridas(){
  // Acepta lo que se dedujo del nombre, en bloque. Se puede revisar antes de guardar: lo que se
  // escribe es lo que quede en pantalla, no lo que se propuso.
  var n=0;
  D.filas.forEach(function(f){
    if(!f.activo) return;
    D.columnas.forEach(function(col){
      if(esSugerida(f,col)){ CAMBIOS[f.id+'|'+col]=f.sugerido[col]; n++; }
    });
  });
  pintar();
  document.getElementById('estado').textContent = n+' sugerencia(s) aceptadas. Revisa y guarda.';
}

async function guardar(){
  var ks=Object.keys(CAMBIOS);
  if(!ks.length){ document.getElementById('estado').textContent='No hay cambios que guardar.'; return; }
  var porFila={};
  ks.forEach(function(k){
    var p=k.split('|'); var id=parseInt(p[0],10);
    porFila[id]=porFila[id]||{id:id};
    porFila[id][p[1]]=CAMBIOS[k];
  });
  var filas=Object.keys(porFila).map(function(id){ return porFila[id]; });
  var b=document.getElementById('btn-guardar');
  b.disabled=true; b.style.opacity='.6';
  document.getElementById('estado').textContent='Guardando '+filas.length+' fila(s)...';
  try{
    var t=await (await fetch('/api/csrf-token',{credentials:'same-origin'})).json();
    var r=await fetch('/api/mee/normalizar-guardar',{method:'POST',credentials:'same-origin',
      headers:{'Content-Type':'application/json','X-CSRF-Token':t.csrf_token||t.token||''},
      body:JSON.stringify({filas:filas})});
    var j=await r.json();
    if(!r.ok){ document.getElementById('estado').textContent='No se pudo guardar: '+(j.error||r.status); return; }
    CAMBIOS={};
    var msg=j.guardadas+' fila(s) guardadas.';
    if((j.errores||[]).length){
      // Lo que no se pudo guardar se DICE, con el motivo: un "listo" que dejo cosas afuera es
      // peor que un error, porque nadie vuelve a mirarlas.
      msg+=' '+j.errores.length+' rechazada(s): '+j.errores.slice(0,3).map(function(e){
        return (e.campo||'')+' '+(e.codigo||'')+' ('+(e.motivo||'')+')';}).join('; ');
    }
    document.getElementById('estado').textContent=msg;
    await cargar();
  }catch(e){
    document.getElementById('estado').textContent='No se pudo guardar: '+e;
  }finally{
    b.disabled=false; b.style.opacity='1';
  }
}

cargar();
</script></body></html>"""
