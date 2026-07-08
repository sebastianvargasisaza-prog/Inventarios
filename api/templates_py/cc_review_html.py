# -*- coding: utf-8 -*-
"""Modal de Revisión CC (COC-PRO-001) · componente PREMIUM compartido · Sebastián 8-jul-2026.

Se inyecta en el módulo Calidad (Laura/Yuliel) para que su liberación de MP se vea y funcione IGUAL que la del
CEO en Planta: checklist documental + solubilidad + AQL + muestra de retención + firma electrónica 21 CFR Part 11.
Autocontenido (no depende de globals del host salvo un helper de fetch estándar). Usa /api/lotes/cc-review.

⚠ Es RAW string (r-triple-comilla) para que los `\n` de los prompts JS queden literales (regla M65 · un \n
crudo dentro de un bloque script embebido rompe el script)."""

# ── Markup del modal (estilos inline · premium · no depende del CSS del host) ──
CC_REVIEW_MODAL_HTML = r'''
<div id="ccr-modal" style="display:none;position:fixed;inset:0;background:rgba(24,24,27,.55);z-index:99999;align-items:center;justify-content:center;padding:16px;font-family:'Inter',system-ui,Arial,sans-serif;">
  <div style="background:#fff;border-radius:16px;max-width:640px;width:100%;max-height:92vh;overflow:hidden;box-shadow:0 24px 70px rgba(24,24,27,.35);display:flex;flex-direction:column;">
    <div style="height:5px;background:linear-gradient(90deg,#a78bfa,#6d28d9);flex:none;"></div>
    <div style="display:flex;justify-content:space-between;align-items:center;padding:16px 22px 8px;">
      <div style="display:flex;align-items:center;gap:10px;min-width:0;">
        <div style="width:38px;height:38px;border-radius:11px;background:linear-gradient(135deg,#a78bfa,#6d28d9);display:flex;align-items:center;justify-content:center;font-size:18px;flex:none;">&#128203;</div>
        <div style="min-width:0;"><div style="font-size:16px;font-weight:800;color:#18181b;line-height:1.15;">Revisión CC &middot; Liberación de MP</div><div id="ccr-sub" style="font-size:12px;color:#71717a;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;"></div></div>
      </div>
      <button onclick="cerrarCCReview()" style="background:none;border:none;font-size:22px;cursor:pointer;color:#a1a1aa;line-height:1;flex:none;">&times;</button>
    </div>
    <div style="overflow-y:auto;padding:4px 22px 8px;">
      <div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;padding:10px 14px;margin-bottom:14px;font-size:12.5px;color:#1e40af;">
        <b>COC-PRO-001 &middot; modo migración</b> &mdash; por ahora los análisis son <b>opcionales</b>. Completá la <b>documental</b> y la <b>ubicación final</b>, y firmá para liberar. (Cuando se active INVIMA estricto, los campos pasan a obligatorios.)
      </div>
      <div id="ccr-info" style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px 14px;background:#f5f3ff;border:1px solid #ede9fe;border-radius:10px;padding:12px 14px;margin-bottom:16px;font-size:12.5px;"></div>

      <div class="ccr-sec">Revisión documental</div>
      <label class="ccr-chk"><input type="checkbox" id="ccr-coa-ok"><span>COA del proveedor presente y correspondiente al lote recibido</span></label>
      <label class="ccr-chk"><input type="checkbox" id="ccr-lote-coincide"><span>N° de lote del COA coincide exactamente con el lote del empaque</span></label>
      <label class="ccr-chk"><input type="checkbox" id="ccr-coa-vigente"><span>COA vigente &mdash; no vencido según política de re-análisis</span></label>
      <label class="ccr-chk"><input type="checkbox" id="ccr-ficha-ok"><span>Ficha técnica del proveedor disponible en archivo CC</span></label>

      <div class="ccr-sec">Prueba de solubilidad / compatibilidad</div>
      <div class="ccr-seg">
        <label><input type="radio" name="ccr-solub" value="ACEPTACION"><span style="color:#15803d;">&#10003; Aceptación</span></label>
        <label><input type="radio" name="ccr-solub" value="RECHAZO"><span style="color:#dc2626;">&#10007; Rechazo</span></label>
      </div>

      <div class="ccr-sec">Resultado AQL / inspección organoléptica</div>
      <div class="ccr-seg">
        <label><input type="radio" name="ccr-aql" value="CONFORME"><span style="color:#15803d;">Conforme</span></label>
        <label><input type="radio" name="ccr-aql" value="NO_CONFORME"><span style="color:#dc2626;">No conforme</span></label>
        <label><input type="radio" name="ccr-aql" value="CUARENTENA_EXTENDIDA"><span style="color:#c2410c;">Cuarentena ext.</span></label>
      </div>
      <input id="ccr-aql-obs" placeholder="Observaciones AQL (obligatorio si No conforme o Cuarentena extendida)" style="width:100%;padding:9px 12px;border:1px solid #e4e4e7;border-radius:9px;font-size:13px;margin-top:8px;box-sizing:border-box;">

      <div class="ccr-sec">Muestra de retención</div>
      <label class="ccr-chk"><input type="checkbox" id="ccr-muestra"><span>Se tomó muestra de retención y quedó identificada en laboratorio CC</span></label>

      <div class="ccr-sec">Ubicación final (al aprobar)</div>
      <div style="display:flex;gap:8px;">
        <input id="ccr-est" placeholder="Estantería" style="flex:1;padding:9px 12px;border:1px solid #e4e4e7;border-radius:9px;font-size:13px;box-sizing:border-box;">
        <input id="ccr-pos" placeholder="Posición" style="flex:1;padding:9px 12px;border:1px solid #e4e4e7;border-radius:9px;font-size:13px;box-sizing:border-box;">
      </div>
      <textarea id="ccr-obs" placeholder="Observaciones adicionales · condiciones especiales, hallazgos, acciones tomadas..." style="width:100%;padding:9px 12px;border:1px solid #e4e4e7;border-radius:9px;font-size:13px;margin-top:12px;min-height:56px;box-sizing:border-box;resize:vertical;"></textarea>
      <div id="ccr-msg" style="margin-top:12px;font-size:13px;min-height:18px;"></div>
    </div>
    <div style="display:flex;gap:10px;justify-content:space-between;align-items:center;padding:12px 22px 18px;border-top:1px solid #f1f1f4;flex:none;flex-wrap:wrap;">
      <button onclick="imprimirRotuloCC()" style="padding:10px 16px;border:1px solid #c4b5fd;background:#f5f3ff;color:#6d28d9;border-radius:10px;font-weight:700;cursor:pointer;font-size:14px;">&#128424; Imprimir rótulo</button>
      <div style="display:flex;gap:10px;">
        <button onclick="cerrarCCReview()" style="padding:10px 18px;border:1px solid #e4e4e7;background:#fff;color:#3f3f46;border-radius:10px;font-weight:600;cursor:pointer;font-size:14px;">Cancelar</button>
        <button id="ccr-submit" onclick="enviarCCReview()" style="padding:10px 22px;border:none;background:linear-gradient(135deg,#7c3aed,#6d28d9);color:#fff;border-radius:10px;font-weight:700;cursor:pointer;font-size:14px;box-shadow:0 4px 14px rgba(109,40,217,.25);">&#9998; Firmar y registrar</button>
      </div>
    </div>
  </div>
</div>
<style>
  #ccr-info b{color:#4c1d95;font-weight:700;}
  .ccr-sec{font-size:11px;font-weight:800;color:#71717a;text-transform:uppercase;letter-spacing:.5px;margin:16px 0 8px;}
  .ccr-chk{display:flex;align-items:flex-start;gap:10px;cursor:pointer;font-size:13px;color:#27272a;padding:6px 0;line-height:1.35;}
  .ccr-chk input{width:17px;height:17px;margin-top:1px;flex:none;accent-color:#6d28d9;cursor:pointer;}
  .ccr-seg{display:flex;gap:8px;flex-wrap:wrap;}
  .ccr-seg label{display:flex;align-items:center;gap:7px;cursor:pointer;padding:9px 14px;border:1.5px solid #e4e4e7;border-radius:10px;font-size:13px;font-weight:700;flex:1;justify-content:center;min-width:120px;}
  .ccr-seg input{accent-color:#6d28d9;cursor:pointer;}
  .ccr-seg label:has(input:checked){border-color:#6d28d9;background:#f5f3ff;}
</style>
'''

# ── JS del modal (raw · autocontenido) · usa /api/lotes/cc-review + firma Part 11 ──
CC_REVIEW_JS = r'''
var _ccrLote=null;
function abrirCCReview(lote){
  _ccrLote = (typeof lote==='string') ? JSON.parse(lote) : lote;
  var l=_ccrLote||{};
  var nombre = l.material_nombre || l.nombre || l.codigo_mp || l.material_id || '';
  document.getElementById('ccr-sub').textContent = (l.lote||'sin lote') + '  ·  ' + nombre;
  document.getElementById('ccr-info').innerHTML =
    '<div><b>Código:</b> '+(l.material_id||l.codigo_mp||'—')+'</div>'+
    '<div><b>Lote:</b> '+(l.lote||'—')+'</div>'+
    '<div><b>Cantidad:</b> '+(l.cantidad!=null?l.cantidad+' g':'—')+'</div>'+
    '<div style="grid-column:1/-1"><b>Material:</b> '+nombre+'</div>'+
    '<div><b>Proveedor:</b> '+(l.proveedor||'—')+'</div>'+
    '<div><b>OC:</b> '+(l.numero_oc||'—')+'</div>';
  ['ccr-coa-ok','ccr-lote-coincide','ccr-coa-vigente','ccr-ficha-ok','ccr-muestra'].forEach(function(id){var e=document.getElementById(id);if(e)e.checked=false;});
  ['ccr-aql-obs','ccr-est','ccr-pos','ccr-obs'].forEach(function(id){var e=document.getElementById(id);if(e)e.value='';});
  var rs=document.querySelectorAll('input[name="ccr-solub"],input[name="ccr-aql"]');rs.forEach(function(r){r.checked=false;});
  document.getElementById('ccr-msg').innerHTML='';
  document.getElementById('ccr-modal').style.display='flex';
}
function cerrarCCReview(){var m=document.getElementById('ccr-modal');if(m)m.style.display='none';_ccrLote=null;}
function imprimirRotuloCC(){
  // Sebastián 9-jul: si el lote entró en cuarentena en recepción, Calidad imprime el rótulo acá al liberar
  // y lo pega en la ubicación. Reusa el rótulo de recepción de MP.
  if(!_ccrLote){return;}
  var cod=_ccrLote.material_id||_ccrLote.codigo_mp||'';
  var lote=_ccrLote.lote||'SL';
  var cant=parseFloat(_ccrLote.cantidad)||0;
  if(!cod){alert('No hay código de MP para el rótulo');return;}
  window.open('/rotulo-recepcion/'+encodeURIComponent(cod)+'/'+encodeURIComponent(lote)+'/'+cant.toFixed(1),'_blank');
}
async function _ccrFirmar(meaning, recordId){
  var pwd=prompt('FIRMA ELECTRÓNICA (21 CFR Part 11)\n\nIngresá tu contraseña para firmar la disposición del lote ('+meaning+'):');
  if(!pwd){return null;}
  var totp=prompt('Si tenés MFA activo, ingresá el código de 6 dígitos.\nSi no usás MFA, dejá vacío y presioná OK.')||'';
  try{
    var rc=await fetch('/api/sign/challenge',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({password:pwd,totp_token:totp})});
    var dc=await rc.json();
    if(!rc.ok){return {error:dc.error||'Credenciales inválidas'};}
    var rs=await fetch('/api/sign',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({record_table:'movimientos',record_id:String(recordId),meaning:meaning,challenge_token:dc.token})});
    var ds=await rs.json();
    if(!rs.ok){return {error:ds.error||'Error al firmar'};}
    return {signature_id:ds.signature_id};
  }catch(e){return {error:'Error de red al firmar: '+e.message};}
}
async function enviarCCReview(){
  if(!_ccrLote){return;}
  var msg=document.getElementById('ccr-msg');
  var solub=document.querySelector('input[name="ccr-solub"]:checked');
  var aql=document.querySelector('input[name="ccr-aql"]:checked');
  var aqlObs=(document.getElementById('ccr-aql-obs').value||'').trim();
  // Modo migración (warm · Sebastián 9-jul): los análisis son OPCIONALES. Si no se marca nada, el backend lo
  // trata como APROBADO. Solo exigimos la observación cuando SÍ se marca un rechazo explícito.
  if(aql && (aql.value==='NO_CONFORME'||aql.value==='CUARENTENA_EXTENDIDA') && !aqlObs){msg.innerHTML='<span style="color:#dc2626;font-weight:600">Si marcás No conforme / Cuarentena ext., poné la observación</span>';return;}
  var payload={
    mov_id:_ccrLote.id, lote:_ccrLote.lote||'', codigo_mp:_ccrLote.material_id||_ccrLote.codigo_mp||'',
    coa_ok:document.getElementById('ccr-coa-ok').checked, lote_coincide:document.getElementById('ccr-lote-coincide').checked,
    coa_vigente:document.getElementById('ccr-coa-vigente').checked, ficha_ok:document.getElementById('ccr-ficha-ok').checked,
    solubilidad:(solub?solub.value:''), resultado_aql:(aql?aql.value:''), observaciones_aql:aqlObs,
    muestra_retencion:document.getElementById('ccr-muestra').checked,
    observaciones:(document.getElementById('ccr-obs').value||'').trim(),
    estanteria_final:(document.getElementById('ccr-est').value||'').trim(),
    posicion_final:(document.getElementById('ccr-pos').value||'').trim()
  };
  var btn=document.getElementById('ccr-submit');
  try{
    btn.disabled=true; btn.textContent='Registrando...';
    var r=await fetch('/api/lotes/cc-review',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify(payload)});
    var res=await r.json();
    if(!r.ok && res.requiere_firma){
      var firma=await _ccrFirmar(res.sign_meaning, res.record_id);
      if(firma===null){msg.innerHTML='<span style="color:#dc2626">Firma cancelada · la disposición NO se registró</span>';return;}
      if(firma.error){msg.innerHTML='<span style="color:#dc2626">'+firma.error+'</span>';return;}
      payload.signature_id=firma.signature_id;
      r=await fetch('/api/lotes/cc-review',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify(payload)});
      res=await r.json();
    }
    if(r.ok){
      msg.innerHTML='<span style="color:#16a34a;font-weight:700">&#10003; '+((res.message||'Revisión registrada'))+' · '+((res.estado||''))+'</span>';
      setTimeout(function(){cerrarCCReview(); if(typeof loadCuarentena==='function'){loadCuarentena();} if(typeof cargarCuarentena==='function'){cargarCuarentena();}},1500);
    }else{
      msg.innerHTML='<span style="color:#dc2626">'+((res.error||'Error al registrar'))+'</span>';
    }
  }catch(e){
    msg.innerHTML='<span style="color:#dc2626">Error: '+e.message+'</span>';
  }finally{
    btn.disabled=false; btn.textContent='✎ Firmar y registrar';
  }
}
'''
