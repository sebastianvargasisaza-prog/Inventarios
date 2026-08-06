# -*- coding: utf-8 -*-
"""El modal "Solicitar pago con caja menor" · UNA sola definición para las dos pantallas.

Sebastián (5-ago): *"esto debe ser así tanto en Compras como en Espagiria, y reflejarse a
Daniela en Ánimus cuando le llega la solicitud"*.

Antes había dos copias del modal, una en `compras_html.py` y otra en `espagiria_html.py`, con
los mismos campos escritos dos veces. Eso no es un problema estético: dos copias divergen, y la
que queda vieja es siempre la de la pantalla que se toca menos (M116/M45). Acá se genera una
vez, con el prefijo de ids como parámetro (`cp` en Compras, `ep` en Espagiria), y las dos se
inyectan con `assert` — si el reemplazo no matchea, el botón quedaría llamando a un modal que
no existe.

Lo que el modal agrega y era el motivo del pedido: **COMO se le paga**. Hasta hoy la solicitud
decía cuánto y a quién, nunca cómo, así que Daniela recibía una orden de pago que no se puede
ejecutar — si es transferencia falta la cuenta, si es Nequi el celular — y eso terminaba
resolviéndose por WhatsApp, fuera del sistema y sin rastro.
"""


def modal_caja(pref, empresa_default='ANIMUS'):
    """HTML del modal. `pref` es el prefijo de los ids ('cp' o 'ep')."""
    p = pref
    otra = 'ESPAGIRIA' if empresa_default == 'ANIMUS' else 'ANIMUS'
    _op = ('<option value="%s">%s</option><option value="%s">%s</option>'
           % (empresa_default, 'ANIMUS' if empresa_default == 'ANIMUS' else 'Espagiria',
              otra, 'Espagiria' if otra == 'ESPAGIRIA' else 'ANIMUS'))

    return '''
<div id="modal-''' + p + '''" class="cajam-back" onclick="if(event.target===this)''' + p + '''Cerrar()">
  <div class="cajam-box">
    <div class="cajam-head">
      <div>
        <div class="cajam-title">&#128184; Solicitar pago con caja menor</div>
        <div class="cajam-sub">Lo autoriza gerencia y lo paga quien maneja la caja</div>
      </div>
      <button onclick="''' + p + '''Cerrar()" class="cajam-x" title="Cerrar">&times;</button>
    </div>

    <div class="cajam-body">

      <!-- (1) QUE SE PAGA -->
      <div class="cajam-sec">&#9312; Qu&eacute; se paga</div>
      <div class="cajam-card">
        <label class="cajam-lbl">Concepto *</label>
        <input id="''' + p + '''-concepto" class="cajam-in" placeholder="Ej: transporte de la mercanc&iacute;a, bolsas ziploc, servicio de limpieza">
        <div class="cajam-row2" style="margin-top:11px">
          <div>
            <label class="cajam-lbl">Monto *</label>
            <div class="cajam-money">
              <span class="cajam-cur">$</span>
              <input id="''' + p + '''-monto" type="number" min="0" step="1" class="cajam-in cajam-in-money" placeholder="0" oninput="''' + p + '''AvisarTope()">
            </div>
          </div>
          <div>
            <label class="cajam-lbl">Empresa</label>
            <select id="''' + p + '''-empresa" class="cajam-in">''' + _op + '''</select>
          </div>
        </div>
        <div id="''' + p + '''-tope-aviso" class="cajam-aviso"></div>
      </div>

      <!-- (2) A QUIEN -->
      <div class="cajam-sec">&#9313; A qui&eacute;n se le paga</div>
      <div class="cajam-card">
        <div class="cajam-seg" id="''' + p + '''-bt-seg">
          <button type="button" class="cajam-segb on" data-bt="proveedor" onclick="''' + p + '''BenTipo('proveedor')">&#127978; Un proveedor</button>
          <button type="button" class="cajam-segb" data-bt="persona" onclick="''' + p + '''BenTipo('persona')">&#128100; Una persona</button>
          <button type="button" class="cajam-segb" data-bt="concepto" onclick="''' + p + '''BenTipo('concepto')">&#128221; Solo el concepto</button>
        </div>

        <div id="''' + p + '''-ben-prov">
          <label class="cajam-lbl">Proveedor</label>
          <input id="''' + p + '''-prov-buscar" class="cajam-in" list="''' + p + '''-prov-dl"
                 placeholder="Escrib&iacute; para buscar en el maestro&hellip;" autocomplete="off"
                 onchange="''' + p + '''ProvElegido()" oninput="''' + p + '''ProvElegido()">
          <datalist id="''' + p + '''-prov-dl"></datalist>
          <div id="''' + p + '''-prov-estado" class="cajam-hint">Eleg&iacute; uno y traigo sus datos de pago &middot; si no est&aacute; en la lista, us&aacute; &quot;Una persona&quot;.</div>
        </div>

        <div id="''' + p + '''-ben-persona" style="display:none">
          <label class="cajam-lbl">Nombre de quien cobra</label>
          <input id="''' + p + '''-benef" class="cajam-in" placeholder="Ej: Juli&aacute;n Andr&eacute;s Quiceno Valencia">
          <div class="cajam-hint">Va a quedar en la lista para la pr&oacute;xima vez que le paguen.</div>
        </div>

        <div id="''' + p + '''-ben-concepto" style="display:none">
          <div class="cajam-hint" style="margin-top:2px">Un gasto sin destinatario nominal (un peaje, un domicilio). Se registra con el concepto de arriba.</div>
        </div>
      </div>

      <!-- (3) COMO SE LE PAGA -->
      <div class="cajam-sec">&#9314; C&oacute;mo se le paga</div>
      <div class="cajam-card">
        <div class="cajam-seg" id="''' + p + '''-medio-seg">
          <button type="button" class="cajam-segb on" data-medio="efectivo" onclick="''' + p + '''Medio('efectivo')">&#128181; Efectivo</button>
          <button type="button" class="cajam-segb" data-medio="nequi" onclick="''' + p + '''Medio('nequi')">&#128241; Nequi</button>
          <button type="button" class="cajam-segb" data-medio="transferencia" onclick="''' + p + '''Medio('transferencia')">&#127974; Transferencia</button>
        </div>

        <div id="''' + p + '''-m-efectivo" class="cajam-hint" style="margin-top:2px">
          Se le entrega la plata en la mano &middot; no hace falta ning&uacute;n dato m&aacute;s.
        </div>

        <div id="''' + p + '''-m-nequi" style="display:none">
          <label class="cajam-lbl">N&uacute;mero de Nequi (celular) *</label>
          <input id="''' + p + '''-nequi" class="cajam-in" inputmode="numeric" placeholder="3001234567">
          <div class="cajam-row2" style="margin-top:11px">
            <div>
              <label class="cajam-lbl">A nombre de</label>
              <input id="''' + p + '''-titular-n" class="cajam-in" placeholder="Titular de la cuenta">
            </div>
            <div>
              <label class="cajam-lbl">C&eacute;dula / NIT</label>
              <input id="''' + p + '''-doc-n" class="cajam-in" placeholder="Opcional">
            </div>
          </div>
        </div>

        <div id="''' + p + '''-m-transf" style="display:none">
          <div class="cajam-row2">
            <div>
              <label class="cajam-lbl">Banco *</label>
              <input id="''' + p + '''-banco" class="cajam-in" list="''' + p + '''-bancos-dl" placeholder="Ej: Bancolombia">
              <datalist id="''' + p + '''-bancos-dl">
                <option value="Bancolombia"><option value="Davivienda"><option value="BBVA">
                <option value="Banco de Bogot&aacute;"><option value="Nu"><option value="Lulo Bank">
                <option value="Banco de Occidente"><option value="Scotiabank Colpatria">
                <option value="Banco Agrario"><option value="Banco Caja Social"><option value="Itau">
              </datalist>
            </div>
            <div>
              <label class="cajam-lbl">Tipo de cuenta</label>
              <select id="''' + p + '''-tipocta" class="cajam-in">
                <option value="ahorros">Ahorros</option>
                <option value="corriente">Corriente</option>
              </select>
            </div>
          </div>
          <label class="cajam-lbl" style="margin-top:11px">N&uacute;mero de cuenta *</label>
          <input id="''' + p + '''-numcta" class="cajam-in" inputmode="numeric" placeholder="Solo n&uacute;meros">
          <div class="cajam-row2" style="margin-top:11px">
            <div>
              <label class="cajam-lbl">A nombre de</label>
              <input id="''' + p + '''-titular-t" class="cajam-in" placeholder="Titular de la cuenta">
            </div>
            <div>
              <label class="cajam-lbl">C&eacute;dula / NIT</label>
              <input id="''' + p + '''-doc-t" class="cajam-in" placeholder="Opcional">
            </div>
          </div>
        </div>
      </div>

      <!-- (4) RESPALDO -->
      <div class="cajam-sec">&#9315; Con qu&eacute; se justifica</div>
      <div class="cajam-card">
        <label class="cajam-lbl">Factura o cotizaci&oacute;n (foto)</label>
        <input id="''' + p + '''-foto" type="file" accept="image/*,.pdf" capture="environment"
               onchange="''' + p + '''SubirFoto()" class="cajam-file">
        <div id="''' + p + '''-foto-estado" class="cajam-hint">
          Sacale una foto a la factura o eleg&iacute;la del celular &middot; justifica el monto ANTES de autorizar
        </div>
        <label class="cajam-lbl" style="margin-top:12px">Enlace de la cotizaci&oacute;n</label>
        <input id="''' + p + '''-cotiz" class="cajam-in" placeholder="Opcional &middot; se llena solo si sub&iacute;s la foto">
        <label class="cajam-lbl" style="margin-top:12px">Observaciones</label>
        <textarea id="''' + p + '''-obs" class="cajam-in cajam-ta" placeholder="Lo que quien paga necesita saber"></textarea>
      </div>

      <div id="''' + p + '''-err" class="cajam-err"></div>
    </div>

    <div class="cajam-foot">
      <button class="cajam-btn cajam-btn-sec" onclick="''' + p + '''Cerrar()">Cancelar</button>
      <button class="cajam-btn cajam-btn-pri" id="''' + p + '''-enviar" onclick="''' + p + '''Guardar()">Enviar solicitud</button>
    </div>
  </div>
</div>
'''


# El CSS va aparte para inyectarlo una sola vez por página aunque el modal se use más de una vez.
# Todo en tokens `var(--cx-*)`: es la regla 0 del proyecto y además es lo que hace que el tema
# oscuro funcione — un hex fijo en el fondo con el texto en token da contraste 1.0 (M114).
CAJA_MODAL_CSS = '''
<style>
.cajam-back{display:none;position:fixed;inset:0;background:rgba(15,15,20,.62);
  backdrop-filter:blur(3px);z-index:1000;align-items:flex-start;justify-content:center;
  padding:24px 16px;overflow-y:auto}
.cajam-box{background:var(--cx-card);border:1px solid var(--cx-border);border-radius:18px;
  width:660px;max-width:96vw;box-shadow:0 24px 60px -20px rgba(24,24,27,.45),0 2px 6px rgba(24,24,27,.06);
  overflow:hidden;margin:auto}
.cajam-head{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;
  padding:20px 24px 16px;border-bottom:1px solid var(--cx-hairline, var(--cx-border));
  background:linear-gradient(180deg,var(--cx-primary-pale, #faf7ff),transparent)}
.cajam-title{font-size:17px;font-weight:800;color:var(--cx-text);letter-spacing:-.01em}
.cajam-sub{font-size:12px;color:var(--cx-text-mute);margin-top:3px}
.cajam-x{background:none;border:none;color:var(--cx-text-mute);font-size:24px;cursor:pointer;
  line-height:1;padding:0 4px;border-radius:8px}
.cajam-x:hover{background:var(--cx-bg-alt);color:var(--cx-text)}
.cajam-body{padding:18px 24px 6px;max-height:calc(100vh - 230px);overflow-y:auto}
.cajam-sec{font-size:10.5px;font-weight:800;letter-spacing:.09em;text-transform:uppercase;
  color:var(--cx-primary-text);margin:16px 0 7px;display:flex;align-items:center;gap:7px}
.cajam-sec:first-child{margin-top:2px}
.cajam-card{background:var(--cx-bg-alt);border:1px solid var(--cx-border);border-radius:13px;padding:15px 16px}
.cajam-lbl{display:block;font-size:11px;color:var(--cx-text-soft);font-weight:700;margin-bottom:5px}
.cajam-in{width:100%;background:var(--cx-card);border:1.5px solid var(--cx-border);
  color:var(--cx-text);padding:9px 12px;border-radius:9px;font-size:13.5px;font-family:inherit;
  transition:border-color .12s,box-shadow .12s;box-sizing:border-box}
.cajam-in:focus{outline:none;border-color:var(--cx-primary);
  box-shadow:0 0 0 3px var(--cx-primary-pale, rgba(124,58,237,.12))}
.cajam-ta{min-height:62px;resize:vertical;line-height:1.5}
.cajam-row2{display:grid;grid-template-columns:1fr 1fr;gap:11px}
.cajam-money{position:relative;display:flex;align-items:center}
.cajam-cur{position:absolute;left:12px;font-size:14px;font-weight:800;color:var(--cx-text-mute);pointer-events:none}
.cajam-in-money{padding-left:26px;font-size:17px;font-weight:800;letter-spacing:-.01em}
.cajam-seg{display:flex;gap:6px;margin-bottom:12px;flex-wrap:wrap}
.cajam-segb{flex:1;min-width:120px;background:var(--cx-card);border:1.5px solid var(--cx-border);
  color:var(--cx-text-soft);border-radius:10px;padding:9px 10px;font-size:12.5px;font-weight:700;
  cursor:pointer;font-family:inherit;transition:all .12s}
.cajam-segb:hover{border-color:var(--cx-primary-light, var(--cx-primary))}
.cajam-segb.on{background:var(--cx-primary-pale, #f5f3ff);border-color:var(--cx-primary);
  color:var(--cx-primary-text);box-shadow:0 1px 3px rgba(124,58,237,.14)}
.cajam-hint{font-size:11.5px;color:var(--cx-text-mute);margin-top:6px;line-height:1.5}
.cajam-file{width:100%;background:var(--cx-card);border:1.5px dashed var(--cx-border);
  color:var(--cx-text);border-radius:10px;padding:10px 12px;font-size:12.5px;box-sizing:border-box}
.cajam-aviso{font-size:12px;margin-top:9px;line-height:1.5}
.cajam-err{font-size:12.5px;color:var(--cx-danger-text);margin:10px 0 2px;font-weight:600}
.cajam-foot{display:flex;gap:9px;justify-content:flex-end;padding:14px 24px 18px;
  border-top:1px solid var(--cx-hairline, var(--cx-border));background:var(--cx-bg-alt)}
.cajam-btn{border:none;border-radius:10px;padding:10px 20px;font-size:13.5px;font-weight:700;
  cursor:pointer;font-family:inherit}
.cajam-btn-sec{background:var(--cx-card);border:1.5px solid var(--cx-border);color:var(--cx-text-soft)}
.cajam-btn-sec:hover{background:var(--cx-bg-alt)}
.cajam-btn-pri{background:var(--cx-primary-grad, linear-gradient(90deg,#7c3aed,#5b21b6));color:#fff;
  box-shadow:0 2px 8px -2px rgba(124,58,237,.5)}
.cajam-btn-pri:disabled{opacity:.55;cursor:default;box-shadow:none}
@media (max-width:620px){.cajam-row2{grid-template-columns:1fr}.cajam-body{padding:14px 16px 4px}
  .cajam-head,.cajam-foot{padding-left:16px;padding-right:16px}}

/* Chips de "cómo se le paga" · se usan en las TRES pantallas (Compras, Espagiria y la bandeja
   de quien paga), así que su estilo viaja con el resto en vez de repetirse en cada una. */
.cajam-chip{display:inline-block;font-size:10.5px;font-weight:800;padding:3px 9px;
  border-radius:999px;letter-spacing:.02em;white-space:nowrap}
.cajam-chip-efe{background:var(--cx-success-pale);color:var(--cx-success-text)}
.cajam-chip-nq{background:var(--cx-primary-pale);color:var(--cx-primary-text)}
.cajam-chip-tr{background:var(--cx-info-pale);color:var(--cx-info-text)}
.cajam-det{font-size:11.5px;color:var(--cx-text);margin-top:4px;line-height:1.45;
  font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.cajam-tit{font-size:11px;color:var(--cx-text-mute);margin-top:3px}
/* El NUMERO DE CUENTA es lo unico que hay que transcribir exacto, y es donde un error cuesta
   plata: va grande, monoespaciado y con aire entre digitos. Un dato critico en 11px es una
   invitacion a equivocarse (Sebastian: "se ven super pequenos... que despues no tengamos
   errores"). */
.cajam-cuenta{display:flex;align-items:center;gap:8px;margin-top:3px;flex-wrap:wrap}
.cajam-cuenta b{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:16px;
  font-weight:800;letter-spacing:.06em;color:var(--cx-text);line-height:1.2}
.cajam-copy{border:1px solid var(--cx-border);background:var(--cx-card);color:var(--cx-text-soft);
  border-radius:7px;padding:3px 9px;font-size:10.5px;font-weight:700;cursor:pointer;
  font-family:inherit;white-space:nowrap}
.cajam-copy:hover{background:var(--cx-bg-soft)}
.cajam-copy.ok{background:var(--cx-success-pale);border-color:var(--cx-success);
  color:var(--cx-success-text)}
.cajam-banco{font-size:12px;color:var(--cx-text-soft);font-weight:700;margin-top:3px}
</style>
'''


# El JS vive en `caja_modal_js.py` y se re-exporta desde acá, para que quien use el modal importe
# de un solo lugar. La separación no es capricho: allá el prefijo de ids se sustituye con un
# marcador en vez de concatenar comillas — pegar cuatro comillas seguidas es ambiguo en Python y
# me costó dos intentos descubrirlo.
from templates_py.caja_modal_js import js_caja, cajaComoPagar_js  # noqa: E402,F401


