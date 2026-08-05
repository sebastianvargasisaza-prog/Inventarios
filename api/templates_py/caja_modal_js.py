# -*- coding: utf-8 -*-
"""El JS del modal de caja menor · una definición para las dos pantallas.

Vive aparte del HTML por una razón práctica: el prefijo de ids (`cp` en Compras, `ep` en
Espagiria) se sustituye con el marcador `@P@`, no concatenando comillas. Escribir
`'''' + p + '''` deja cuatro comillas pegadas y Python las parsea mal — me pasó al escribirlo.
Con marcador, el texto de abajo se lee exactamente como el JS que se emite, que es lo que hay
que poder revisar.

⚠ Ni un `\\n` real dentro de un string de JS: esto termina incrustado en un string de Python y
un salto de línea rompería TODO el bloque `<script>`, no sólo esta función (M65).
"""


def js_caja(pref):
    """El JS del modal con el prefijo de ids ya sustituido."""
    return _JS_CAJA.replace('@P@', pref)


def cajaComoPagar_js():
    """Sólo el pintor de "cómo se le paga", sin el modal.

    Lo necesita la bandeja de quien paga (Daniela en Ánimus), que muestra los datos pero no
    tiene el formulario para pedirlos. Si esa pantalla se armara su propio pintor, el día que
    se agregue un medio de pago quedaría mostrando el anterior (M45)."""
    i = _JS_CAJA.find('function cajaComoPagar(')
    assert i > 0, 'no encontré cajaComoPagar en el JS compartido'
    return _JS_CAJA[i:]


_JS_CAJA = r"""
// ── Modal de pago con caja menor · generado por caja_modal.py (una definicion, dos pantallas)
var _@P@BenTipo = 'proveedor', _@P@Medio = 'efectivo', _@P@Provs = [];

function @P@Cerrar(){ var m = document.getElementById('modal-@P@'); if(m) m.style.display = 'none'; }

function @P@BenTipo(t){
  _@P@BenTipo = t;
  var seg = document.getElementById('@P@-bt-seg');
  if(seg) Array.prototype.forEach.call(seg.querySelectorAll('.cajam-segb'), function(b){
    b.classList.toggle('on', b.getAttribute('data-bt') === t);
  });
  var map = {proveedor:'@P@-ben-prov', persona:'@P@-ben-persona', concepto:'@P@-ben-concepto'};
  for(var k in map){ var el = document.getElementById(map[k]); if(el) el.style.display = (k === t ? '' : 'none'); }
}

function @P@Medio(m){
  _@P@Medio = m;
  var seg = document.getElementById('@P@-medio-seg');
  if(seg) Array.prototype.forEach.call(seg.querySelectorAll('.cajam-segb'), function(b){
    b.classList.toggle('on', b.getAttribute('data-medio') === m);
  });
  var map = {efectivo:'@P@-m-efectivo', nequi:'@P@-m-nequi', transferencia:'@P@-m-transf'};
  for(var k in map){ var el = document.getElementById(map[k]); if(el) el.style.display = (k === m ? '' : 'none'); }
}

// La lista NO trae cuentas: solo nombres. La cuenta se pide de a una al elegir (Ley 1581).
async function @P@CargarBenef(){
  try{
    var r = await fetch('/api/caja/beneficiarios', {credentials:'same-origin'});
    var d = await r.json();
    _@P@Provs = (d && d.beneficiarios) || [];
    var dl = document.getElementById('@P@-prov-dl');
    if(dl) dl.innerHTML = _@P@Provs.map(function(b){
      return '<option value="' + String(b.nombre).replace(/"/g, '&quot;') + '">';
    }).join('');
    // Si el maestro no se pudo leer se DICE: un buscador vacio se lee como "no hay proveedores",
    // que es lo contrario de lo que pasa.
    if(d && d.ok === false){
      var est = document.getElementById('@P@-prov-estado');
      if(est) est.innerHTML = '<span style="color:var(--cx-danger-text)">No pude leer el maestro de proveedores &middot; escribi el nombre en "Una persona"</span>';
    }
  }catch(e){}
}

async function @P@ProvElegido(){
  var inp = document.getElementById('@P@-prov-buscar');
  var est = document.getElementById('@P@-prov-estado');
  if(!inp || !est) return;
  var nom = (inp.value || '').trim().toLowerCase();
  var hit = null;
  for(var i = 0; i < _@P@Provs.length; i++){
    if(String(_@P@Provs[i].nombre || '').trim().toLowerCase() === nom){ hit = _@P@Provs[i]; break; }
  }
  inp.setAttribute('data-pid', (hit && hit.id) ? hit.id : '');
  if(!hit){ est.textContent = 'Elegi uno de la lista y traigo sus datos de pago.'; return; }
  if(!hit.id){ est.textContent = 'Ya cobro antes · escribi abajo como se le paga.'; return; }
  est.textContent = 'Buscando sus datos de pago...';
  try{
    var r = await fetch('/api/caja/beneficiario-datos?proveedor_id=' + hit.id, {credentials:'same-origin'});
    var d = await r.json();
    if(!d.ok){ est.textContent = d.error || 'No pude traer los datos'; return; }
    if(d.tiene_datos){
      @P@Medio('transferencia');
      var b = document.getElementById('@P@-banco'); if(b) b.value = d.banco || '';
      var t = document.getElementById('@P@-tipocta');
      if(t && d.tipo_cuenta) t.value = (String(d.tipo_cuenta).toLowerCase().indexOf('corr') >= 0) ? 'corriente' : 'ahorros';
      var n = document.getElementById('@P@-numcta'); if(n) n.value = d.num_cuenta || '';
      var ti = document.getElementById('@P@-titular-t'); if(ti && !ti.value) ti.value = d.nombre || '';
      var dc = document.getElementById('@P@-doc-t'); if(dc && !dc.value) dc.value = d.documento || '';
      est.innerHTML = '<span style="color:var(--cx-success-text)">&#10003; Traje su cuenta del maestro</span> &middot; podes cambiarla para este pago.';
    } else {
      est.innerHTML = '<span style="color:var(--cx-warn-text)">' + (d.aviso || 'Sin cuenta en el maestro') + '</span>';
    }
  }catch(e){ est.textContent = 'No pude traer los datos · escribilos abajo.'; }
}

function @P@Abrir(){
  ['-concepto','-monto','-benef','-obs','-cotiz','-prov-buscar','-nequi','-banco','-numcta',
   '-titular-n','-titular-t','-doc-n','-doc-t'].forEach(function(sfx){
    var el = document.getElementById('@P@' + sfx); if(el) el.value = '';
  });
  var pb = document.getElementById('@P@-prov-buscar'); if(pb) pb.setAttribute('data-pid', '');
  ['-tope-aviso','-err'].forEach(function(sfx){
    var el = document.getElementById('@P@' + sfx); if(el) el.innerHTML = '';
  });
  var fe = document.getElementById('@P@-foto-estado');
  if(fe) fe.innerHTML = 'Sacale una foto a la factura o elegila del celular &middot; justifica el monto ANTES de autorizar';
  @P@BenTipo('proveedor'); @P@Medio('efectivo'); @P@CargarBenef();
  var m = document.getElementById('modal-@P@'); if(m) m.style.display = 'flex';
}

// Arma el cuerpo con COMO se le paga. La validacion dura vive en el backend: dos pantallas
// mandan aca, y si cada una validara por su cuenta una de las dos quedaria floja.
function @P@Cuerpo(){
  var g = function(id){ var e = document.getElementById('@P@' + id); return e ? String(e.value || '').trim() : ''; };
  var pb = document.getElementById('@P@-prov-buscar');
  var pid = pb ? (pb.getAttribute('data-pid') || '') : '';
  var benef = (_@P@BenTipo === 'proveedor') ? g('-prov-buscar')
            : (_@P@BenTipo === 'persona')   ? g('-benef') : '';
  var b = {
    concepto: g('-concepto'),
    monto: parseFloat(g('-monto') || '0'),
    empresa: g('-empresa'),
    beneficiario: benef,
    beneficiario_tipo: _@P@BenTipo,
    proveedor_id: (_@P@BenTipo === 'proveedor') ? pid : '',
    observaciones: g('-obs'),
    cotizacion_url: g('-cotiz'),
    pago_medio: _@P@Medio
  };
  if(_@P@Medio === 'nequi'){
    b.pago_nequi = g('-nequi'); b.pago_titular = g('-titular-n'); b.pago_documento = g('-doc-n');
  } else if(_@P@Medio === 'transferencia'){
    b.pago_banco = g('-banco'); b.pago_tipo_cuenta = g('-tipocta');
    b.pago_num_cuenta = g('-numcta'); b.pago_titular = g('-titular-t'); b.pago_documento = g('-doc-t');
  }
  return b;
}

// Muestra COMO hay que pagarle · lo usa la bandeja de quien paga (Daniela) y el listado de
// Compras/Espagiria. Una orden de pago que no dice a donde se paga no se puede ejecutar, y
// eso terminaba resolviendose por WhatsApp: fuera del sistema y sin rastro.
function cajaComoPagar(s, esc){
  var e = esc || function(x){ return String(x == null ? '' : x); };
  var medio = (s.pago_medio || 'efectivo');
  if(medio === 'efectivo') return '<span class="cajam-chip cajam-chip-efe">&#128181; Efectivo</span>';
  var det = '', chip = '';
  if(medio === 'nequi'){
    chip = '<span class="cajam-chip cajam-chip-nq">&#128241; Nequi</span>';
    det = '<b>' + e(s.pago_nequi || '') + '</b>';
  } else {
    chip = '<span class="cajam-chip cajam-chip-tr">&#127974; Transferencia</span>';
    det = e(s.pago_banco || '') + (s.pago_tipo_cuenta ? ' &middot; ' + e(s.pago_tipo_cuenta) : '')
        + '<br><b>' + e(s.pago_num_cuenta || '') + '</b>';
  }
  var tit = s.pago_titular ? '<div class="cajam-tit">a nombre de ' + e(s.pago_titular)
            + (s.pago_documento ? ' &middot; ' + e(s.pago_documento) : '') + '</div>' : '';
  return chip + '<div class="cajam-det">' + det + '</div>' + tit;
}
"""
