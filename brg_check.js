
var _B=[];
function esc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
async function cargar(){
  try{
    var r=await fetch('/api/programacion/mp-bridge',{credentials:'same-origin'});
    _B=(await r.json())||[]; pinta();
  }catch(e){document.getElementById('msg').innerHTML='<span style="color:#dc2626">Error de red</span>';}
}
function pinta(){
  var q=(document.getElementById('q').value||'').trim().toUpperCase();
  var act=_B.filter(function(b){return b.activo==1||b.activo===true;});
  if(q)act=act.filter(function(b){return (JSON.stringify(b)||'').toUpperCase().indexOf(q)>=0;});
  var h='<table><thead><tr><th>Código fórmula</th><th>Nombre</th><th>&rarr; usa stock de</th><th>Nombre bodega</th><th>Acción</th></tr></thead><tbody>';
  act.forEach(function(b){
    h+='<tr><td style="font-family:monospace;font-weight:700">'+esc(b.formula_material_id)+'</td><td>'+esc((b.formula_material_nombre||'').slice(0,28))+'</td><td style="font-family:monospace;font-weight:700;color:#7c3aed">'+esc(b.bodega_material_id)+'</td><td>'+esc((b.bodega_material_nombre||b.bodega_inci||'').slice(0,28))+'</td><td style="white-space:nowrap"><button class="bd" onclick="desactivar('+b.id+',&quot;'+esc(b.formula_material_id)+'&rarr;'+esc(b.bodega_material_id)+'&quot;)">Desactivar</button> <input id="rp'+b.id+'" placeholder="nuevo cód" style="width:88px;border:1px solid #e4e4e7;border-radius:6px;padding:4px 6px;font-family:monospace;font-size:12px"> <button class="rp" onclick="reapuntar(&quot;'+esc(b.formula_material_id)+'&quot;,&quot;'+esc((b.formula_material_nombre||'').replace(/"/g,\'\'))+'&quot;,'+b.id+')">Re-apuntar</button></td></tr>';
  });
  h+='</tbody></table>';
  document.getElementById('out').innerHTML= act.length? h : '<div style="color:#888;margin-top:10px">Sin puentes activos'+(q?' para "'+esc(q)+'"':'')+'.</div>';
}
async function desactivar(id,txt){
  if(!confirm('Desactivar el puente '+txt+'? A partir de ahora ese código de fórmula descuenta su PROPIO stock (no el del otro). Reversible.'))return;
  try{
    var t=await (await fetch('/api/csrf-token',{credentials:'same-origin'})).json();
    var r=await fetch('/api/programacion/mp-bridge/'+id,{method:'DELETE',credentials:'same-origin',headers:{'X-CSRF-Token':t.csrf_token||''}});
    var d=await r.json();
    if(!r.ok||!d.ok){document.getElementById('msg').innerHTML='<span style="color:#dc2626">Error: '+esc(d.error||r.status)+'</span>';return;}
    document.getElementById('msg').innerHTML='<span style="color:#16a34a;font-weight:700">&#10003; Puente desactivado</span>';
    cargar();
  }catch(e){document.getElementById('msg').innerHTML='<span style="color:#dc2626">Error de red</span>';}
}
async function reapuntar(fid,fnom,id){
  var nb=((document.getElementById('rp'+id)||{}).value||'').trim().toUpperCase();
  if(!nb){alert('Escribí el código de bodega al que debe apuntar (ej. MP00110)');return;}
  if(!confirm('Re-apuntar '+fid+' → '+nb+'? (desactiva el puente actual y crea uno nuevo a '+nb+' · reversible)'))return;
  try{
    var t=await (await fetch('/api/csrf-token',{credentials:'same-origin'})).json();
    var r=await fetch('/api/admin/mp-bridge-reapuntar',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':t.csrf_token||''},body:JSON.stringify({formula_material_id:fid,formula_nombre:fnom,nuevo_bodega:nb})});
    var d=await r.json();
    if(!r.ok||!d.ok){document.getElementById('msg').innerHTML='<span style="color:#dc2626">Error: '+esc(d.error||r.status)+'</span>';return;}
    document.getElementById('msg').innerHTML='<span style="color:#16a34a;font-weight:700">&#10003; '+esc(fid)+' ahora apunta a '+esc(nb)+'</span>';
    cargar();
  }catch(e){document.getElementById('msg').innerHTML='<span style="color:#dc2626">Error de red</span>';}
}
cargar();

;

var _C='';
function esc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function num(n){return Number(n||0).toLocaleString('es-CO');}
async function diag(){
  var cod=(document.getElementById('cod').value||'').trim().toUpperCase();
  if(!cod){alert('Poné un código');return;}
  document.getElementById('out').innerHTML='<div style="color:#7c3aed">Cargando…</div>';
  try{
    var r=await fetch('/api/admin/mp-diag?codigo='+encodeURIComponent(cod),{credentials:'same-origin'});
    var d=await r.json();
    if(!r.ok||!d.ok){document.getElementById('out').innerHTML='<div style="color:#dc2626">'+esc(d.error||r.status)+'</div>';return;}
    _C=d.codigo;
    if(!d.existe){document.getElementById('out').innerHTML='<div style="background:#fef2f2;border:1px solid #fecaca;border-radius:10px;padding:14px;color:#7f1d1d"><b>'+esc(d.codigo)+'</b> no existe en el maestro de MP.</div>';return;}
    var rows='';(d.lotes||[]).forEach(function(l){rows+='<tr><td style="font-family:monospace">'+esc(l.lote||'(sin lote)')+'</td><td>'+esc(l.estado)+'</td><td style="text-align:right;color:#166534">'+num(l.entrada_g)+'</td><td style="text-align:right;color:#b91c1c">'+num(l.salida_g)+'</td><td style="text-align:right;font-weight:700">'+num(l.neto_g)+' g</td><td>'+(l.usable?'<span style="color:#16a34a">usable</span>':'<span style="color:#b45309">retenido</span>')+'</td></tr>';});
    if(!rows)rows='<tr><td colspan="6" style="color:#888">Sin lotes con stock.</td></tr>';
    var badgeAct=d.activo?'<span style="background:#dcfce7;color:#166534;border-radius:8px;padding:2px 9px;font-weight:700;font-size:12px">ACTIVA</span>':'<span style="background:#fee2e2;color:#991b1b;border-radius:8px;padding:2px 9px;font-weight:700;font-size:12px">INACTIVA</span>';
    var h='<div style="background:#fff;border:1px solid #ede9fe;border-radius:12px;padding:16px">'
      +'<div style="font-size:16px"><b>'+esc(d.codigo)+'</b> &middot; '+esc(d.nombre_inci||d.nombre_comercial||'(sin nombre)')+' '+badgeAct+'</div>'
      +'<div style="color:#555;font-size:13px;margin-top:4px">tipo_material: <b>'+esc(d.tipo_material)+'</b> &middot; stock usable: <b>'+num(d.stock_usable_g)+' g</b> &middot; retenido: <b>'+num(d.stock_retenido_g)+' g</b></div>'
      +'<div style="color:#555;font-size:13px;margin-top:2px">movimientos en kardex: <b>'+num(d.mov_total)+'</b> &middot; neto crudo (todos los estados): <b>'+num(d.mov_neto_raw_g)+' g</b></div>'
      +'<div style="margin-top:10px;padding:11px 13px;background:'+(d.aparece_en_bodega_default?'#f0fdf4;border:1px solid #bbf7d0;color:#166534':'#fffbeb;border:1px solid #fde68a;color:#92400e')+';border-radius:9px;font-size:13.5px"><b>'+esc(d.razon)+'</b></div>';
    if((d.historial||[]).length){
      h+='<div style="margin-top:12px;font-size:12px;color:#6d28d9;font-weight:700;text-transform:uppercase;letter-spacing:.4px">Historial de normalización</div>';
      (d.historial||[]).forEach(function(x){
        var st=(x.despues&&(x.despues.stock_g!=null))?(' &middot; stock registrado: <b>'+num(x.despues.stock_g)+' g</b>'):'';
        var de=(x.antes&&x.antes.codigo_mp)?(esc(x.antes.codigo_mp)+' &rarr; '+esc(d.codigo)):'';
        h+='<div style="font-size:12.5px;color:#444;margin-top:3px">&bull; '+esc(x.fecha).slice(0,16)+' &middot; <b>'+esc(x.accion)+'</b> '+de+st+'</div>';
      });
    }
    h+='<table><thead><tr><th>Lote</th><th>Estado</th><th style="text-align:right">Entró</th><th style="text-align:right">Salió</th><th style="text-align:right">Queda</th><th>Uso</th></tr></thead><tbody>'+rows+'</tbody></table>';
    if(!d.activo)h+='<button class="cx-btn cx-btn-success" style="margin-top:12px" onclick="reactivar()">&#9851;&#65039; Reactivar '+esc(d.codigo)+' (activo=1)</button>';
    h+='</div>';
    document.getElementById('out').innerHTML=h;
  }catch(e){document.getElementById('out').innerHTML='<div style="color:#dc2626">Error de red</div>';}
}
async function reactivar(){
  if(!_C)return;
  if(!confirm('Reactivar '+_C+' (activo=1)? Solo cambia el estado · NO toca fórmulas ni stock · reversible.'))return;
  try{
    var t=await (await fetch('/api/csrf-token',{credentials:'same-origin'})).json();
    var r=await fetch('/api/admin/mp-reactivar',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':t.csrf_token||''},body:JSON.stringify({codigo:_C})});
    var d=await r.json();
    if(!r.ok||!d.ok){alert('Error: '+(d.error||r.status));return;}
    diag();
  }catch(e){alert('Error de red');}
}
