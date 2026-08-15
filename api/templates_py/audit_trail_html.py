"""Audit trail en lenguaje humano (15-ago-2026).

El Audit Trail de MyBatch muestra el JSON crudo de Django. Es trazabilidad de verdad,
pero un auditor no lee eso. EOS ya guarda el antes y el despues completos, asi que puede
mostrar la misma evidencia en palabras -quien, que cambio, de que a que- conservando el
JSON crudo debajo de cada renglon, que es la prueba.
"""

AUDIT_TRAIL_HTML = r"""<!DOCTYPE html><html lang="es" translate="no"><head><meta charset="UTF-8">
<meta name="google" content="notranslate">
<meta name="viewport" content="width=device-width,initial-scale=1.0,viewport-fit=cover"><title>Audit trail &middot; Aseguramiento &middot; EOS</title>
<link rel="stylesheet" href="/static/cortex.css?v=eos15">
<script>(function(){try{var t=localStorage.getItem("cx-theme");if(t==="dark")document.documentElement.setAttribute("data-theme","dark");}catch(e){}})();</script>
<style>
body{background:var(--cx-bg);color:var(--cx-text);margin:0;font-family:'Inter',system-ui,-apple-system,sans-serif;}
*{box-sizing:border-box}
.at-wrap{width:96vw;max-width:1560px;margin:0 auto;padding:22px 18px 72px;}
.card{background:var(--cx-card);border:1px solid var(--cx-hairline);border-radius:18px;box-shadow:0 1px 3px rgba(15,23,42,.04),0 10px 30px rgba(15,23,42,.05);padding:20px 22px;margin-bottom:16px;}
.at-intro{color:var(--cx-text-mute);font-size:13.5px;line-height:1.55;max-width:920px;margin:0 0 16px;}
.filtros{display:flex;gap:10px;flex-wrap:wrap;align-items:center;}
.doms{display:flex;gap:7px;flex-wrap:wrap;margin-top:14px;}
.dom{font-size:12px;font-weight:700;padding:6px 13px;border-radius:999px;border:1px solid var(--cx-hairline);background:var(--cx-card);color:var(--cx-text-soft);cursor:pointer;}
.dom:hover{border-color:var(--cx-primary-light);color:var(--cx-primary-text);}
.dom.on{background:var(--cx-primary-grad, var(--cx-primary));color:#fff;border-color:transparent;}
.dom .c{opacity:.75;font-weight:600;margin-left:4px;}
.ev{border-left:3px solid var(--cx-hairline);padding:12px 0 12px 16px;margin-bottom:2px;}
.ev:hover{background:var(--cx-bg-alt);}
.ev.materiales{border-left-color:#0284c7;} .ev.manufactura{border-left-color:var(--cx-primary-text);}
.ev.envasado{border-left-color:#0d9488;} .ev.acondicionamiento{border-left-color:#7c3aed;}
.ev.calidad{border-left-color:var(--cx-success-text, #15803d);} .ev.procedimientos{border-left-color:var(--cx-warn-text, #b45309);}
.ev.compras{border-left-color:#c2410c;} .ev.dinero{border-left-color:var(--cx-danger-text, #b91c1c);}
.ev .t{font-size:14px;font-weight:700;color:var(--cx-text);line-height:1.4;}
.ev .m{font-size:11.5px;color:var(--cx-text-mute);margin-top:3px;font-variant-numeric:tabular-nums;}
.ev .nota{font-size:12.5px;color:var(--cx-text-soft);margin-top:5px;line-height:1.5;}
.cambios{margin-top:8px;display:flex;flex-direction:column;gap:3px;}
.cb{font-size:12.5px;color:var(--cx-text-soft);line-height:1.5;}
.cb b{color:var(--cx-text);font-weight:700;}
.cb .de{color:var(--cx-danger-text, #b91c1c);text-decoration:line-through;opacity:.85;}
.cb .a{color:var(--cx-success-text, #15803d);font-weight:700;}
.crudo{margin-top:8px;}
.crudo summary{font-size:11.5px;color:var(--cx-text-faint);cursor:pointer;font-weight:600;}
.crudo pre{font-size:11px;font-family:ui-monospace,monospace;background:var(--cx-bg-alt);border:1px solid var(--cx-hairline);border-radius:8px;padding:10px 12px;overflow-x:auto;margin:7px 0 0;color:var(--cx-text-soft);white-space:pre-wrap;word-break:break-word;}
.sinlee{display:inline-block;font-size:10px;font-weight:800;border-radius:6px;padding:2px 7px;background:rgba(180,83,9,.14);color:var(--cx-warn-text, #b45309);margin-left:6px;}
.nota-pie{font-size:11.5px;color:var(--cx-text-faint);line-height:1.6;margin-top:14px;}
.empty{color:var(--cx-text-mute);font-size:14px;padding:42px 0;text-align:center;}
</style></head><body>
<header class="cx-mod-header cx-fade-in">
  <span class="cx-mod-header__logo" style="display:inline-flex;align-items:center;color:var(--cx-primary-text);"><svg viewBox="0 0 24 24" width="34" height="34" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8v5l3 2"/><circle cx="12" cy="12" r="9"/></svg></span>
  <div>
    <div class="cx-mod-header__title">Audit trail</div>
    <div class="cx-mod-header__sub"><strong>Aseguramiento</strong> &middot; qui&eacute;n cambi&oacute; qu&eacute;, de qu&eacute; a qu&eacute; &middot; 21 CFR Part 11</div>
  </div>
  <div class="cx-mod-header__nav">
    <a href="/aseguramiento" class="cx-btn cx-btn-ghost cx-btn-sm">&larr; Aseguramiento</a>
    <a href="/calidad/maestro-lotes" class="cx-btn cx-btn-ghost cx-btn-sm">&#128202; Maestro de lotes</a>
    <a href="/modulos" class="cx-btn cx-btn-ghost cx-btn-sm">M&oacute;dulos</a>
    <button class="cx-theme-toggle" onclick="cxToggleTheme()" title="Modo claro/oscuro"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4 12H2M22 12h-2M5.6 5.6 4.2 4.2M19.8 19.8l-1.4-1.4M5.6 18.4l-1.4 1.4M19.8 4.2l-1.4 1.4"/></svg></button>
  </div>
</header>
<script>function cxToggleTheme(){var h=document.documentElement;var n=h.getAttribute('data-theme')==='dark'?'light':'dark';if(n==='dark')h.setAttribute('data-theme','dark');else h.removeAttribute('data-theme');try{localStorage.setItem('cx-theme',n);}catch(e){}}</script>
<div class="at-wrap">
<div class="card">
<div class="at-intro">Cada cambio del sistema, en palabras: <b>qui&eacute;n</b> lo hizo, <b>qu&eacute;</b> toc&oacute; y <b>de qu&eacute; a qu&eacute;</b>. Debajo de cada rengl&oacute;n queda el registro crudo, que es la prueba. Filtr&aacute; por &aacute;rea del proceso para responder una auditor&iacute;a sin leer todo.</div>
<div class="filtros">
  <input id="desde" type="date" class="cx-input" style="max-width:170px" title="Desde">
  <input id="hasta" type="date" class="cx-input" style="max-width:170px" title="Hasta">
  <input id="usuario" class="cx-input" style="max-width:190px" placeholder="Usuario" autocomplete="off">
  <input id="q" class="cx-input" style="min-width:220px;flex:1" placeholder="Buscar acción, tabla o registro…" autocomplete="off">
  <button class="cx-btn cx-btn-grad" onclick="atCargar()">Buscar</button>
  <span id="msg" style="font-size:12.5px;font-weight:700"></span>
</div>
<div id="doms" class="doms"></div>
</div>
<div class="card">
  <div id="res"></div>
  <div id="pie" class="nota-pie"></div>
</div>
</div>
<script>
var AT = {dominio:''};
function esc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function atCargar(){
  var p=new URLSearchParams();
  ['desde','hasta','usuario','q'].forEach(function(k){var v=document.getElementById(k).value.trim(); if(v)p.set(k,v);});
  if(AT.dominio)p.set('dominio',AT.dominio);
  document.getElementById('msg').textContent='Cargando...';
  fetch('/api/aseguramiento/audit-trail-legible?'+p.toString(),{credentials:'same-origin'})
   .then(function(r){return r.json().then(function(j){return {s:r.status,j:j};});})
   .then(function(x){
     if(x.s===403){document.getElementById('msg').textContent='Este registro lo ve Calidad, Aseguramiento o la Dirección Técnica.';return;}
     var j=x.j;
     if(!j||!j.ok){document.getElementById('msg').textContent='No se pudo cargar';return;}
     document.getElementById('msg').textContent='';
     atDominios(j);
     atPintar(j);
   }).catch(function(e){document.getElementById('msg').textContent='Error: '+e;});
}
function atDominios(j){
  var nombres={materiales:'Materiales',manufactura:'Manufactura',envasado:'Envasado',
    acondicionamiento:'Acondicionamiento',calidad:'Calidad',procedimientos:'Procedimientos',
    compras:'Compras',dinero:'Dinero',clientes:'Clientes',personas:'Personas',otros:'Otros'};
  var h='<span class="dom'+(AT.dominio?'':' on')+'" onclick="atDom(\'\')">Todo</span>';
  (j.dominios||[]).forEach(function(d){
    var n=(j.por_dominio||{})[d]||0;
    h+='<span class="dom'+(AT.dominio===d?' on':'')+'" onclick="atDom(\''+d+'\')">'+esc(nombres[d]||d)+(n?'<span class="c">'+n+'</span>':'')+'</span>';
  });
  document.getElementById('doms').innerHTML=h;
}
function atDom(d){AT.dominio=d; atCargar();}
function atPintar(j){
  var L=j.items||[];
  if(!L.length){document.getElementById('res').innerHTML='<div class="empty">No hay cambios registrados con esos filtros.</div>';
    document.getElementById('pie').textContent='';return;}
  document.getElementById('res').innerHTML=L.map(function(e){
    var h='<div class="ev '+esc(e.dominio)+'">';
    h+='<div class="t">'+esc(e.titulo)+(e.traducido?'':'<span class="sinlee" title="EOS no supo traducir esta acción: se muestra el registro crudo, que es la prueba">sin traducir</span>')+'</div>';
    h+='<div class="m">'+esc((e.fecha||'').replace('T',' ').slice(0,19))+' &middot; '+esc(e.accion||'')+' &middot; '+esc(e.tabla||'')+'</div>';
    if(e.nota) h+='<div class="nota">'+esc(e.nota)+'</div>';
    if(e.cambios && e.cambios.length){
      h+='<div class="cambios">';
      e.cambios.forEach(function(c){
        h+='<div class="cb"><b>'+esc(c.campo)+'</b>: ';
        if(c.de!=null) h+='<span class="de">'+esc(c.de)+'</span> &rarr; ';
        h+='<span class="a">'+esc(c.a==null?'quitado':c.a)+'</span></div>';
      });
      h+='</div>';
    }
    if(e.antes||e.despues){
      h+='<details class="crudo"><summary>Ver el registro crudo (la prueba)</summary>';
      if(e.antes) h+='<pre>ANTES: '+esc(e.antes)+'</pre>';
      if(e.despues) h+='<pre>DESPUÉS: '+esc(e.despues)+'</pre>';
      h+='</details>';
    }
    return h+'</div>';
  }).join('');
  var pie='Mostrando '+j.mostrados+' de '+j.total+' cambios en el rango.';
  if(j.recortado>0) pie+=' Quedan '+j.recortado+' fuera de esta página: acotá el rango de fechas, el usuario o el área.';
  if(j.sin_traducir>0) pie+=' '+j.sin_traducir+' renglón(es) no se pudieron traducir a lenguaje humano y se muestran crudos: EOS lo declara en vez de dejarlos a medias.';
  document.getElementById('pie').textContent=pie;
}
['q','usuario'].forEach(function(k){
  document.getElementById(k).addEventListener('keydown',function(e){if(e.key==='Enter')atCargar();});
});
atCargar();
</script>
</body></html>"""
