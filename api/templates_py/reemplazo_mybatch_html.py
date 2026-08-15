"""Que falta para que EOS reemplace a MyBatch · medido, no supuesto (15-ago-2026).

El clon del batch record puede estar completo y aun asi no reemplazar nada: el registro
de lote nace OCULTO y el modo de control nace apagado. Un sistema construido y apagado se
ve, desde afuera, igual que uno que no existe. Esta pantalla lo mide contra la base real
y dice DONDE se cambia cada cosa.
"""

REEMPLAZO_MYBATCH_HTML = r"""<!DOCTYPE html><html lang="es" translate="no"><head><meta charset="UTF-8">
<meta name="google" content="notranslate">
<meta name="viewport" content="width=device-width,initial-scale=1.0,viewport-fit=cover"><title>Reemplazo de MyBatch &middot; EOS</title>
<link rel="stylesheet" href="/static/cortex.css?v=eos15">
<script>(function(){try{var t=localStorage.getItem("cx-theme");if(t==="dark")document.documentElement.setAttribute("data-theme","dark");}catch(e){}})();</script>
<style>
body{background:var(--cx-bg);color:var(--cx-text);margin:0;font-family:'Inter',system-ui,-apple-system,sans-serif;}
*{box-sizing:border-box}
.rm-wrap{width:96vw;max-width:1200px;margin:0 auto;padding:22px 18px 72px;}
.card{background:var(--cx-card);border:1px solid var(--cx-hairline);border-radius:18px;box-shadow:0 1px 3px rgba(15,23,42,.04),0 10px 30px rgba(15,23,42,.05);padding:20px 22px;margin-bottom:16px;}
.rm-intro{color:var(--cx-text-mute);font-size:13.5px;line-height:1.55;max-width:900px;margin:0 0 4px;}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-bottom:16px;}
.kpi{background:var(--cx-card);border:1px solid var(--cx-hairline);border-radius:14px;padding:15px 17px;position:relative;overflow:hidden;}
.kpi:before{content:'';position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--cx-hairline);}
.kpi.ok:before{background:var(--cx-success-text, #15803d);} .kpi.parcial:before{background:var(--cx-warn-text, #b45309);}
.kpi.falta:before{background:var(--cx-danger-text, #b91c1c);}
.kpi .n{font-size:28px;font-weight:800;letter-spacing:-.02em;color:var(--cx-text);line-height:1.05;}
.kpi .t{font-size:11.5px;color:var(--cx-text-mute);margin-top:3px;font-weight:600;}
.pt{display:flex;gap:14px;align-items:flex-start;padding:15px 0;border-bottom:1px solid var(--cx-hairline);}
.pt:last-child{border-bottom:none;}
.pt .ic{font-size:17px;line-height:1.3;min-width:22px;text-align:center;padding-top:1px;}
.pt .cuerpo{flex:1;min-width:0;}
.pt .ti{font-size:14.5px;font-weight:700;color:var(--cx-text);}
.pt .va{font-size:13px;font-weight:700;margin-top:2px;}
.pt.ok .va{color:var(--cx-success-text, #15803d);}
.pt.parcial .va{color:var(--cx-warn-text, #b45309);}
.pt.falta .va{color:var(--cx-danger-text, #b91c1c);}
.pt .pq{font-size:12.5px;color:var(--cx-text-mute);margin-top:5px;line-height:1.55;}
.pt .det{font-size:12px;color:var(--cx-text-faint);margin-top:6px;line-height:1.5;}
.pt a.don{font-size:12px;font-weight:700;color:var(--cx-primary-text);text-decoration:none;white-space:nowrap;padding-top:2px;}
.pt a.don:hover{text-decoration:underline;}
.aviso{font-size:12px;color:var(--cx-text-faint);line-height:1.6;margin-top:16px;border-top:1px solid var(--cx-hairline);padding-top:14px;}
</style></head><body>
<header class="cx-mod-header cx-fade-in">
  <span class="cx-mod-header__logo" style="display:inline-flex;align-items:center;color:var(--cx-primary-text);"><svg viewBox="0 0 24 24" width="34" height="34" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16v5H4z"/><path d="M4 13h16v7H4z"/><path d="M8 9v4"/></svg></span>
  <div>
    <div class="cx-mod-header__title">Reemplazo de MyBatch</div>
    <div class="cx-mod-header__sub"><strong>Aseguramiento</strong> &middot; qu&eacute; falta para que el registro de lote viva en EOS</div>
  </div>
  <div class="cx-mod-header__nav">
    <a href="/aseguramiento" class="cx-btn cx-btn-ghost cx-btn-sm">&larr; Aseguramiento</a>
    <a href="/calidad/maestro-lotes" class="cx-btn cx-btn-ghost cx-btn-sm">&#128202; Maestro de lotes</a>
    <a href="/modulos" class="cx-btn cx-btn-ghost cx-btn-sm">M&oacute;dulos</a>
    <button class="cx-theme-toggle" onclick="cxToggleTheme()" title="Modo claro/oscuro"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4 12H2M22 12h-2M5.6 5.6 4.2 4.2M19.8 19.8l-1.4-1.4M5.6 18.4l-1.4 1.4M19.8 4.2l-1.4 1.4"/></svg></button>
  </div>
</header>
<script>function cxToggleTheme(){var h=document.documentElement;var n=h.getAttribute('data-theme')==='dark'?'light':'dark';if(n==='dark')h.setAttribute('data-theme','dark');else h.removeAttribute('data-theme');try{localStorage.setItem('cx-theme',n);}catch(e){}}</script>
<div class="rm-wrap">
<div class="card"><div class="rm-intro">El batch record de EOS puede estar completo y aun as&iacute; no reemplazar nada: nace <b>oculto</b> y con los controles <b>apagados</b>, a prop&oacute;sito. Ac&aacute; est&aacute; medido contra la base real qu&eacute; falta encender, con el enlace a d&oacute;nde se cambia cada cosa.</div></div>
<div id="kpis" class="kpis"></div>
<div class="card"><div id="puntos"></div><div id="aviso" class="aviso"></div></div>
</div>
<script>
function esc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function rmCargar(){
  fetch('/api/aseguramiento/estado-reemplazo-mybatch',{credentials:'same-origin'})
   .then(function(r){return r.json();}).then(function(j){
     if(!j||!j.ok){document.getElementById('puntos').textContent='No se pudo medir el estado.';return;}
     document.getElementById('kpis').innerHTML=
       '<div class="kpi ok"><div class="n">'+j.listos+'</div><div class="t">listos</div></div>'
      +'<div class="kpi parcial"><div class="n">'+j.parciales+'</div><div class="t">a medias</div></div>'
      +'<div class="kpi falta"><div class="n">'+j.pendientes+'</div><div class="t">faltan</div></div>'
      +'<div class="kpi"><div class="n">'+j.total+'</div><div class="t">puntos medidos</div></div>';
     document.getElementById('puntos').innerHTML=(j.puntos||[]).map(function(p){
       var ic=p.estado==='ok'?'&#10004;':(p.estado==='parcial'?'&#9679;':'&#10007;');
       var h='<div class="pt '+esc(p.estado)+'"><div class="ic">'+ic+'</div><div class="cuerpo">';
       h+='<div class="ti">'+esc(p.titulo)+'</div>';
       h+='<div class="va">'+esc(p.valor)+'</div>';
       h+='<div class="pq">'+esc(p.porque)+'</div>';
       if(p.detalle && p.detalle.length){
         h+='<div class="det">Sin instructivo aprobado: '+esc(p.detalle.slice(0,12).join(' &middot; '))
           +(p.detalle.length>12?' y '+(p.detalle.length-12)+' m&aacute;s':'')+'</div>';
       }
       h+='</div>';
       if(p.donde) h+='<a class="don" href="'+esc(p.donde)+'">Ir &rarr;</a>';
       return h+'</div>';
     }).join('');
     document.getElementById('aviso').textContent=j.aviso||'';
   }).catch(function(e){document.getElementById('puntos').textContent='Error: '+e;});
}
rmCargar();
</script>
</body></html>"""
