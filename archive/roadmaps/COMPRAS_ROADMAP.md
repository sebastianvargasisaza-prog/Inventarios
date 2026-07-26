# Compras Module — Roadmap de Implementación
*Preparado: 2026-04-16 | Para implementación: fin de semana*

---

## ESTADO ACTUAL — DIAGNÓSTICO

### Bugs activos
| # | Descripción | Archivo | Función |
|---|-------------|---------|---------|
| B1 | `cantidad_solicitada` no existe en schema → OC auto vacía | index.py | `generar_oc_automatica()` |
| B2 | Form OC manual no tiene campo `nombre_mp` → items sin descripción | index.py | `addItemOC()` / `crearOC()` |

### Qué existe y funciona
- Login (ya arreglado hoy)
- Dashboard KPIs básicos
- Alertas MPs bajo mínimo
- OCs: crear, cambio de estado, recibir (→ ingreso inventario)
- Solicitudes: ver, aprobar, rechazar, aprobar+crear OC (copia items ✓)
- Proveedores: crear, listar
- `GET /api/solicitudes-compra/<numero>` devuelve area, empresa, categoria, tipo correctamente

---

## FASE 1 — Bugs + Visibilidad básica (~1h)
> **Objetivo:** Módulo confiable y operable el lunes

### F1-1: Fix `generar_oc_automatica` (B1)
**Archivo:** `api/index.py` ~línea 3160

```python
# ANTES (roto):
c.execute("INSERT INTO ordenes_compra_items (numero_oc, codigo_mp, nombre_mp, cantidad_solicitada, unidad) VALUES (?,?,?,?,?)",
          (numero_oc, item['codigo_mp'], item['nombre_mp'], item['cantidad_pedir'], 'g'))

# DESPUÉS (correcto):
c.execute("INSERT INTO ordenes_compra_items (numero_oc, codigo_mp, nombre_mp, cantidad_g) VALUES (?,?,?,?)",
          (numero_oc, item['codigo_mp'], item['nombre_mp'], item['cantidad_pedir']))
```

### F1-2: Fix form OC manual — agregar nombre_mp (B2)
**Archivo:** `api/index.py` — función `addItemOC()` y `crearOC()` en COMPRAS_HTML

La tabla de ítems en el form necesita una columna más para descripción.
También agregar botón de eliminar fila.

```html
<!-- Header de columnas (ANTES): -->
<div class="grid3 oc-item-row" ...>
  <span>Codigo MP</span><span>Cantidad (g)</span><span>Precio unit.</span>
</div>

<!-- Header de columnas (DESPUÉS): 5 columnas -->
<div style="display:grid;grid-template-columns:15% 1fr 13% 13% 5%;gap:6px;...">
  <span>Codigo</span><span>Descripcion *</span><span>Cantidad</span><span>Precio unit.</span><span></span>
</div>
```

```javascript
// addItemOC() DESPUÉS:
function addItemOC(){
  var n = document.getElementById('oc-items-list').children.length;
  var div = document.createElement('div');
  div.className = 'oc-item-row';
  div.style.cssText = 'display:grid;grid-template-columns:15% 1fr 13% 13% 5%;gap:6px;margin-bottom:6px;';
  div.innerHTML =
    '<input type="text" class="oc-cod" placeholder="Cod. MP" style="font-family:monospace;">' +
    '<input type="text" class="oc-nom" placeholder="Descripcion del item">' +
    '<input type="number" class="oc-cant" placeholder="0" step="0.01" min="0">' +
    '<input type="number" class="oc-precio" placeholder="0" step="100" min="0">' +
    '<button class="btn-del" onclick="this.parentElement.remove()" style="padding:4px;">✕</button>';
  document.getElementById('oc-items-list').appendChild(div);
}

// crearOC() — leer nombre también:
async function crearOC(){
  var items = [];
  document.querySelectorAll('.oc-item-row').forEach(function(row){
    var cod   = row.querySelector('.oc-cod').value.trim();
    var nom   = row.querySelector('.oc-nom').value.trim();
    var cant  = parseFloat(row.querySelector('.oc-cant').value) || 0;
    var precio= parseFloat(row.querySelector('.oc-precio').value) || 0;
    if((cod || nom) && cant > 0)
      items.push({codigo_mp: cod, nombre_mp: nom, cantidad_g: cant, precio_unitario: precio});
  });
  if(!items.length){ alert('Agrega al menos un item'); return; }
  var data = {
    proveedor: document.getElementById('oc-prov').value,
    fecha_entrega_est: document.getElementById('oc-fecha-ent').value,
    observaciones: document.getElementById('oc-obs').value,
    items: items, creado_por: USUARIO
  };
  try{
    var r = await fetch('/api/ordenes-compra', {
      method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)
    });
    var res = await r.json();
    if(r.ok){
      document.getElementById('oc-msg').innerHTML = '<div class="msg-ok">' + res.message + '</div>';
      document.getElementById('form-oc').style.display = 'none';
      loadOCs();
    } else {
      document.getElementById('oc-msg').innerHTML = '<div class="msg-err">' + (res.error||'Error') + '</div>';
    }
  }catch(e){ document.getElementById('oc-msg').innerHTML = '<div class="msg-err">Error de conexion</div>'; }
}
```

### F1-3: Modal detalle de OC

**Nuevo modal HTML** (antes del cierre `</body>`):
```html
<div id="modal-oc-det" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:2000;align-items:flex-start;justify-content:center;padding-top:60px;">
  <div style="background:#fff;border-radius:14px;padding:28px 32px;max-width:700px;width:94%;max-height:80vh;overflow-y:auto;position:relative;box-shadow:0 20px 60px rgba(0,0,0,.2);">
    <button onclick="closeModal('modal-oc-det')" style="position:absolute;top:14px;right:16px;background:none;border:none;font-size:22px;cursor:pointer;color:#bbb;">&#x2715;</button>
    <div id="modal-oc-det-content">Cargando...</div>
  </div>
</div>
```

**Función `verOC(numero)` JS:**
```javascript
async function verOC(numero){
  openModal('modal-oc-det');
  document.getElementById('modal-oc-det-content').innerHTML = '<div style="padding:20px;text-align:center;color:#999;">Cargando...</div>';
  try{
    var d = await fetch('/api/ordenes-compra/' + numero).then(function(r){ return r.json(); });
    var oc = d.oc || {}; var items = d.items || [];
    // oc es un array (SELECT *) — mapear por posición según schema
    // ordenes_compra: id(0) numero_oc(1) fecha(2) estado(3) proveedor(4) valor_total(5) observaciones(6) creado_por(7) fecha_entrega_est(8)
    var ocObj = {
      numero_oc: oc[1], fecha: oc[2], estado: oc[3], proveedor: oc[4],
      valor_total: oc[5], observaciones: oc[6], creado_por: oc[7], fecha_entrega_est: oc[8]
    };
    var h = '<h3 style="font-size:18px;font-weight:700;margin-bottom:4px;font-family:monospace;">' + ocObj.numero_oc + '</h3>';
    h += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:16px;font-size:13px;">';
    h += '<div><strong>Proveedor:</strong><br>' + (ocObj.proveedor||'—') + '</div>';
    h += '<div>' + badgeEstado(ocObj.estado) + '</div>';
    h += '<div><strong>Fecha:</strong><br>' + (ocObj.fecha||'').substring(0,10) + '</div>';
    h += '<div><strong>Entrega est.:</strong><br>' + (ocObj.fecha_entrega_est||'—') + '</div>';
    if(ocObj.creado_por) h += '<div><strong>Creado por:</strong><br>' + ocObj.creado_por + '</div>';
    h += '</div>';
    if(ocObj.observaciones) h += '<div style="background:#f8f8f8;border-radius:8px;padding:10px 12px;font-size:13px;margin-bottom:16px;">' + ocObj.observaciones + '</div>';
    // Tabla de ítems
    // ordenes_compra_items: id(0) numero_oc(1) codigo_mp(2) nombre_mp(3) cantidad_g(4) precio_unitario(5) subtotal(6)
    var total = 0;
    h += '<table style="width:100%;border-collapse:collapse;font-size:13px;">';
    h += '<thead><tr><th style="text-align:left;padding:6px 8px;background:#f5f5f5;font-size:11px;color:#888;">Cod.</th><th style="text-align:left;padding:6px 8px;background:#f5f5f5;font-size:11px;color:#888;">Descripcion</th><th style="text-align:right;padding:6px 8px;background:#f5f5f5;font-size:11px;color:#888;">Cantidad</th><th style="text-align:right;padding:6px 8px;background:#f5f5f5;font-size:11px;color:#888;">P. Unit.</th><th style="text-align:right;padding:6px 8px;background:#f5f5f5;font-size:11px;color:#888;">Subtotal</th></tr></thead><tbody>';
    items.forEach(function(it){
      var sub = (it[4]||0) * (it[5]||0);
      total += sub;
      h += '<tr><td style="padding:6px 8px;font-family:monospace;font-size:12px;color:#888;">' + (it[2]||'—') + '</td>';
      h += '<td style="padding:6px 8px;">' + (it[3]||'—') + '</td>';
      h += '<td style="padding:6px 8px;text-align:right;">' + (it[4]||0) + ' g</td>';
      h += '<td style="padding:6px 8px;text-align:right;">' + (it[5]?'$'+it[5].toLocaleString():'—') + '</td>';
      h += '<td style="padding:6px 8px;text-align:right;">' + (sub?'$'+sub.toLocaleString():'—') + '</td></tr>';
    });
    if(!items.length) h += '<tr><td colspan="5" style="padding:12px;text-align:center;color:#aaa;">Sin ítems registrados</td></tr>';
    h += '</tbody>';
    if(total > 0) h += '<tfoot><tr><td colspan="4" style="padding:8px;text-align:right;font-weight:700;border-top:2px solid #eee;">TOTAL ESTIMADO</td><td style="padding:8px;text-align:right;font-weight:700;font-size:15px;color:#2B7A78;border-top:2px solid #eee;">$' + total.toLocaleString() + '</td></tr></tfoot>';
    h += '</table>';
    document.getElementById('modal-oc-det-content').innerHTML = h;
  }catch(e){
    document.getElementById('modal-oc-det-content').innerHTML = '<div style="color:#dc2626;padding:16px;">Error al cargar</div>';
  }
}
```

**Agregar botón "Ver" en `loadOCs()`:**
```javascript
// ANTES:
'<button class="btn btn-ghost btn-sm" onclick="cambiarEstadoOC(&quot;'+o.numero_oc+'&quot;)" >Estado</button>'

// DESPUÉS (agregar Ver antes de Estado):
'<button class="btn btn-ghost btn-sm" onclick="verOC(&quot;'+o.numero_oc+'&quot;)" >Ver</button> ' +
'<button class="btn btn-ghost btn-sm" onclick="cambiarEstadoOC(&quot;'+o.numero_oc+'&quot;)" >Estado</button>'
```

### F1-4: Categoría y valor total en tabla Solicitudes

**Backend** — modificar `GET /api/solicitudes-compra` para incluir valor total por solicitud:
```python
# En handle_solicitudes_compra() GET, cambiar el SQL a:
sql = """
  SELECT s.numero, s.fecha, s.estado, s.solicitante, s.urgencia,
         s.observaciones, s.empresa, s.categoria, s.tipo, s.area,
         COALESCE(SUM(si.valor_estimado),0) as valor_total
  FROM solicitudes_compra s
  LEFT JOIN solicitudes_compra_items si ON s.numero=si.numero
  WHERE 1=1 {filtros}
  GROUP BY s.numero
  ORDER BY s.fecha DESC
  LIMIT 200
"""
cols_sol = ['numero','fecha','estado','solicitante','urgencia','observaciones',
            'empresa','categoria','tipo','area','valor_total']
```

**Frontend** — en `loadSolicitudes()`, agregar categoría y valor en la fila:
```javascript
// En el .map() de solicitudes, reemplazar el return:
var cat = s.categoria ? '<span style="font-size:11px;color:#666;">'+s.categoria+'</span>' : '';
var val = s.valor_total > 0 ? '<span style="font-size:11px;font-weight:600;color:#2B7A78;">$'+s.valor_total.toLocaleString()+'</span>' : '';
return '<tr>' +
  '<td style="font-family:monospace;font-weight:600;">' + s.numero + '</td>' +
  '<td>' + s.solicitante + '<br><span style="font-size:11px;color:#999;">' + (s.area||'') + '</span></td>' +
  '<td>' + s.fecha.substring(0,10) + '</td>' +
  '<td>' + cat + (val?'<br>'+val:'') + '</td>' +
  '<td>' + badgeEstado(s.urgencia) + '</td>' +
  '<td>' + badgeEstado(s.estado) + '</td>' +
  '<td>' + eBadge + acc + '</td></tr>';
```
*(Y agregar `<th>Categoria / Valor</th>` al header de la tabla — actualmente tiene 6 columnas)*

---

## FASE 2 — Flujo completo (~3h)
> **Objetivo:** El módulo se puede usar en producción real

### F2-1: Búsqueda/autocomplete de MP en form OC

Cuando el usuario escribe en `.oc-cod` o `.oc-nom`, hacer búsqueda a `/api/maestro-mps?q=<texto>` y mostrar sugerencias.

```javascript
// Agregar input event listener al crear cada fila de OC:
// Al escribir en .oc-nom → buscar en maestro, al seleccionar llenar .oc-cod
function addItemOC(){
  // ... (mismo código F1-2) ...
  var nomInput = div.querySelector('.oc-nom');
  var codInput = div.querySelector('.oc-cod');
  var cantInput = div.querySelector('.oc-cant');
  var suggest = document.createElement('div');
  suggest.className = 'mp-suggest';
  suggest.style.cssText = 'position:absolute;background:#fff;border:1px solid #ddd;border-radius:6px;z-index:100;max-height:160px;overflow-y:auto;min-width:260px;box-shadow:0 4px 12px rgba(0,0,0,.1);display:none;';
  div.style.position = 'relative';
  div.appendChild(suggest);

  var timer;
  nomInput.addEventListener('input', function(){
    clearTimeout(timer);
    var q = nomInput.value.trim();
    if(q.length < 2){ suggest.style.display='none'; return; }
    timer = setTimeout(async function(){
      var d = await fetch('/api/maestro-mps?q='+encodeURIComponent(q)+'&limit=8').then(function(r){return r.json();});
      var mps = d.materiales || [];
      if(!mps.length){ suggest.style.display='none'; return; }
      suggest.innerHTML = mps.map(function(m){
        var stk = m.stock_actual != null ? ' <span style="color:' + (m.stock_actual < m.stock_minimo ? '#dc2626':'#16a34a') + ';font-size:11px;">(' + m.stock_actual + 'g)</span>' : '';
        return '<div class="mp-opt" data-cod="'+(m.codigo_mp||'')+'" data-nom="'+(m.nombre_comercial||m.nombre_inci||'')+'" style="padding:7px 12px;cursor:pointer;font-size:13px;border-bottom:1px solid #f0f0f0;">' +
          '<span style="font-family:monospace;font-size:11px;color:#888;">' + (m.codigo_mp||'') + '</span> ' +
          (m.nombre_comercial||m.nombre_inci||'') + stk + '</div>';
      }).join('');
      suggest.style.display = 'block';
      suggest.querySelectorAll('.mp-opt').forEach(function(opt){
        opt.addEventListener('click', function(){
          codInput.value = opt.dataset.cod;
          nomInput.value = opt.dataset.nom;
          cantInput.focus();
          suggest.style.display = 'none';
        });
        opt.addEventListener('mouseover', function(){ opt.style.background='#f0f9f8'; });
        opt.addEventListener('mouseout',  function(){ opt.style.background=''; });
      });
    }, 280);
  });
  document.addEventListener('click', function(){ suggest.style.display='none'; });
}
```

**Backend — revisar `/api/maestro-mps`** ya devuelve `codigo_mp`, `nombre_comercial`, `nombre_inci` ✓
Necesita agregar `stock_actual` al response (join con movimientos o tabla stock).
```python
# En handle_maestro() GET, agregar LEFT JOIN para stock:
sql = """
  SELECT m.codigo_mp, m.nombre_inci, m.nombre_comercial, m.tipo, m.proveedor,
         m.stock_minimo, COALESCE(s.stock_actual, 0) as stock_actual
  FROM maestro_mps m
  LEFT JOIN (
    SELECT material_id,
           SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END) as stock_actual
    FROM movimientos GROUP BY material_id
  ) s ON m.codigo_mp = s.material_id
  WHERE m.activo=1 {filtros}
  ORDER BY m.nombre_comercial
  LIMIT {limit}
"""
```

### F2-2: Vista imprimible / PDF de OC

No requiere librería externa. Generar una ruta HTML optimizada para impresión.

**Nueva ruta backend:**
```python
@app.route('/compras/oc/<numero_oc>/print')
def print_oc(numero_oc):
    if 'compras_user' not in session:
        return redirect('/login')
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT * FROM ordenes_compra WHERE numero_oc=?", (numero_oc,))
    oc = c.fetchone()
    c.execute("""
        SELECT codigo_mp, nombre_mp, cantidad_g, precio_unitario, subtotal
        FROM ordenes_compra_items WHERE numero_oc=?
    """, (numero_oc,))
    items = c.fetchall()
    conn.close()
    if not oc:
        return "OC no encontrada", 404
    # oc tuple: id(0) numero_oc(1) fecha(2) estado(3) proveedor(4) valor_total(5) obs(6) creado_por(7) fecha_ent(8)
    total = sum((it[4] or (it[2]*(it[3] or 0))) for it in items)
    items_rows = ''.join(
        f'<tr><td style="font-family:monospace;color:#555;">{it[0] or "—"}</td>'
        f'<td>{it[1] or "—"}</td>'
        f'<td style="text-align:right;">{it[2] or 0:,.0f} g</td>'
        f'<td style="text-align:right;">{("$"+f"{it[3]:,.0f}") if it[3] else "—"}</td>'
        f'<td style="text-align:right;">{("$"+f"{(it[4] or it[2]*(it[3] or 0)):,.0f}") if (it[3] or it[4]) else "—"}</td></tr>'
        for it in items
    )
    fecha_fmt = (oc[2] or '')[:10]
    fecha_ent = (oc[8] or '—')
    html = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
    <title>OC {oc[1]}</title>
    <style>
      body{{font-family:Arial,sans-serif;margin:0;padding:32px;color:#111;}}
      .header{{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:24px;padding-bottom:16px;border-bottom:3px solid #2B7A78;}}
      .brand{{font-size:22px;font-weight:800;color:#2B7A78;}}
      .brand small{{display:block;font-size:12px;color:#888;font-weight:400;}}
      .oc-title{{text-align:right;}}
      .oc-num{{font-size:28px;font-weight:900;color:#1a1a2e;font-family:monospace;}}
      .oc-estado{{display:inline-block;padding:3px 10px;border-radius:12px;font-size:12px;background:#dcfce7;color:#166534;margin-top:4px;}}
      .info-grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:24px;font-size:13px;}}
      .info-box{{background:#f8fafc;border-radius:8px;padding:12px 16px;}}
      .info-box label{{font-size:10px;text-transform:uppercase;color:#888;letter-spacing:.5px;}}
      .info-box p{{margin:4px 0 0;font-weight:600;font-size:15px;}}
      table{{width:100%;border-collapse:collapse;margin-bottom:16px;}}
      th{{background:#1a1a2e;color:#fff;padding:9px 12px;text-align:left;font-size:12px;}}
      td{{padding:8px 12px;border-bottom:1px solid #f0f0f0;font-size:13px;}}
      tr:nth-child(even){{background:#fafafa;}}
      .total-row{{background:#f0f9f8 !important;font-weight:700;font-size:15px;}}
      .footer{{margin-top:32px;padding-top:16px;border-top:1px solid #ddd;font-size:11px;color:#aaa;text-align:center;}}
      .obs-box{{background:#fff8e1;border-left:3px solid #f59e0b;padding:10px 14px;border-radius:4px;font-size:13px;margin-bottom:20px;}}
      @media print{{body{{padding:0 !important;}} .no-print{{display:none;}}}}
    </style></head><body>
    <div class="no-print" style="background:#e0f2fe;padding:10px 16px;border-radius:8px;margin-bottom:20px;font-size:13px;display:flex;align-items:center;gap:12px;">
      <span>Vista de impresion.</span>
      <button onclick="window.print()" style="background:#2B7A78;color:#fff;border:none;padding:6px 16px;border-radius:6px;cursor:pointer;font-weight:600;">Imprimir / Guardar PDF</button>
      <button onclick="window.close()" style="background:#eee;border:none;padding:6px 12px;border-radius:6px;cursor:pointer;">Cerrar</button>
    </div>
    <div class="header">
      <div class="brand">Espagiria Laboratorios<small>Sistema de Compras</small></div>
      <div class="oc-title">
        <div class="oc-num">{oc[1]}</div>
        <div class="oc-estado">{oc[3]}</div>
        <div style="font-size:12px;color:#888;margin-top:4px;">Fecha: {fecha_fmt}</div>
      </div>
    </div>
    <div class="info-grid">
      <div class="info-box"><label>Proveedor</label><p>{oc[4] or '—'}</p></div>
      <div class="info-box"><label>Fecha entrega estimada</label><p>{fecha_ent}</p></div>
      <div class="info-box"><label>Creado por</label><p>{oc[7] or '—'}</p></div>
      <div class="info-box"><label>Estado</label><p>{oc[3]}</p></div>
    </div>
    {"<div class='obs-box'><strong>Observaciones:</strong> " + oc[6] + "</div>" if oc[6] else ""}
    <table>
      <thead><tr><th>Codigo</th><th>Descripcion</th><th style="text-align:right;">Cantidad</th><th style="text-align:right;">Precio Unit.</th><th style="text-align:right;">Subtotal</th></tr></thead>
      <tbody>{items_rows}</tbody>
      {"<tfoot><tr class='total-row'><td colspan='4' style='text-align:right;'>TOTAL ESTIMADO</td><td style='text-align:right;color:#2B7A78;'>$"+f'{total:,.0f}'+"</td></tr></tfoot>" if total > 0 else ""}
    </table>
    <div class="footer">
      Documento generado por Sistema de Inventarios Espagiria · {fecha_fmt}<br>
      Este documento es de uso interno. Para uso externo, verificar con el equipo de compras.
    </div>
    </body></html>"""
    return Response(html, mimetype='text/html')
```

**Botón en modal de OC (en `verOC()`):**
```javascript
// Al final del contenido del modal agregar:
h += '<div style="margin-top:20px;text-align:right;">' +
     '<button class="btn btn-ghost" onclick="window.open(\'/compras/oc/'+numero+'/print\',\'_blank\')">🖨 Imprimir / PDF</button>' +
     '</div>';
```

### F2-3: Audit trail de OC

**Nueva tabla en `init_db()`:**
```python
c.execute("""CREATE TABLE IF NOT EXISTS ordenes_compra_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_oc TEXT NOT NULL,
    accion TEXT NOT NULL,
    estado_anterior TEXT,
    estado_nuevo TEXT,
    usuario TEXT,
    fecha TEXT,
    notas TEXT
)""")
```

**Función helper Python:**
```python
def log_oc(cur, numero_oc, accion, estado_ant=None, estado_nuevo=None, usuario='', notas=''):
    cur.execute(
        "INSERT INTO ordenes_compra_log (numero_oc,accion,estado_anterior,estado_nuevo,usuario,fecha,notas) VALUES (?,?,?,?,?,?,?)",
        (numero_oc, accion, estado_ant, estado_nuevo, usuario, datetime.now().isoformat(), notas)
    )
```

**Llamarla en:**
- `handle_oc_detalle()` PUT → `log_oc(cur, numero_oc, 'cambio_estado', viejo_estado, nuevo_estado, usuario)`
- `recibir_oc()` → `log_oc(cur, numero_oc, 'recepcion', 'En transito', 'Recibida', usuario)`
- `actualizar_estado_solicitud()` → `log_oc(cur, oc_num, 'creada_desde_solicitud', None, 'Borrador', usuario, numero)`

**Mostrar historial en `verOC()`:**
```javascript
// Agregar al final del modal, después de la tabla de items:
var logs = await fetch('/api/ordenes-compra/' + numero + '/log').then(r=>r.json());
if(logs.log && logs.log.length){
  h += '<div style="margin-top:20px;"><div style="font-size:12px;font-weight:700;color:#888;margin-bottom:8px;text-transform:uppercase;">Historial</div>';
  h += '<div style="font-size:12px;">';
  logs.log.forEach(function(l){
    h += '<div style="display:flex;gap:10px;padding:5px 0;border-bottom:1px solid #f5f5f5;">';
    h += '<span style="color:#aaa;min-width:80px;">'+(l.fecha||'').substring(0,10)+'</span>';
    h += '<span style="color:#2B7A78;font-weight:600;">'+(l.usuario||'sistema')+'</span>';
    h += '<span>'+l.accion+(l.estado_nuevo?' → <strong>'+l.estado_nuevo+'</strong>':'')+'</span>';
    h += '</div>';
  });
  h += '</div></div>';
}
```

**Nuevo endpoint:**
```python
@app.route('/api/ordenes-compra/<numero_oc>/log')
def get_oc_log(numero_oc):
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT accion,estado_anterior,estado_nuevo,usuario,fecha,notas FROM ordenes_compra_log WHERE numero_oc=? ORDER BY fecha DESC", (numero_oc,))
    cols = ['accion','estado_anterior','estado_nuevo','usuario','fecha','notas']
    rows = [dict(zip(cols, r)) for r in c.fetchall()]
    conn.close()
    return jsonify({'log': rows})
```

### F2-4: Valor total en OC

**Calcular y actualizar `valor_total` en la OC al crearla o modificarla:**
```python
# En handle_ordenes_compra() POST, después de insertar items:
total = sum(it.get('cantidad_g',0) * it.get('precio_unitario',0) for it in (d.get('items') or []))
c.execute("UPDATE ordenes_compra SET valor_total=? WHERE numero_oc=?", (round(total,2), numero_oc))

# En recibir_oc(), cuando se recibe, marcar valor_total si no estaba
# (items podrían tener precio ya ingresado)
```

**Mostrar en `loadOCs()`:**
```javascript
// Agregar columna Valor a la tabla de OCs:
// En el header: <th>Valor est.</th>
// En la fila:
var val = o.valor_total > 0 ? '$' + o.valor_total.toLocaleString('es-CO') : '—';
// ...dentro del return:
'<td style="text-align:right;font-size:13px;color:#2B7A78;font-weight:600;">' + val + '</td>'
```

### F2-5: Recepción parcial de OC

Cuando una OC llega incompleta (caso muy frecuente), poder registrar cantidades reales vs pedidas.

**Nuevo modal `modal-oc-recibir`:**
```html
<div id="modal-oc-recibir" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:2000;align-items:flex-start;justify-content:center;padding-top:60px;">
  <div style="background:#fff;border-radius:14px;padding:28px 32px;max-width:640px;width:94%;max-height:80vh;overflow-y:auto;position:relative;">
    <button onclick="closeModal('modal-oc-recibir')" style="position:absolute;top:14px;right:16px;background:none;border:none;font-size:22px;cursor:pointer;color:#bbb;">&#x2715;</button>
    <h3 style="font-size:17px;font-weight:700;margin-bottom:4px;">Registrar Recepcion</h3>
    <p id="recibir-oc-num" style="font-family:monospace;color:#2B7A78;font-weight:700;margin-bottom:16px;"></p>
    <div id="recibir-items-list"></div>
    <div style="display:flex;gap:10px;margin-top:18px;">
      <button class="btn" onclick="confirmarRecepcion()">Confirmar recepcion</button>
      <button class="btn btn-ghost" onclick="closeModal('modal-oc-recibir')">Cancelar</button>
    </div>
    <div id="recibir-msg"></div>
  </div>
</div>
```

**Funciones JS:**
```javascript
var _recibirOCNum = '';

async function abrirRecepcionOC(numero){
  _recibirOCNum = numero;
  document.getElementById('recibir-oc-num').textContent = numero;
  var d = await fetch('/api/ordenes-compra/' + numero).then(r=>r.json());
  var items = d.items || [];
  // items: id(0) oc(1) codigo(2) nombre(3) cantidad_g(4) precio(5) subtotal(6)
  var html = '<table style="width:100%;border-collapse:collapse;font-size:13px;">';
  html += '<thead><tr><th style="padding:6px;background:#f5f5f5;text-align:left;">Codigo</th><th style="padding:6px;background:#f5f5f5;">Descripcion</th><th style="padding:6px;background:#f5f5f5;text-align:right;">Pedido</th><th style="padding:6px;background:#f5f5f5;text-align:right;">Recibido</th></tr></thead><tbody>';
  items.forEach(function(it, i){
    html += '<tr><td style="padding:5px;font-family:monospace;font-size:11px;color:#888;">' + (it[2]||'—') + '</td>';
    html += '<td style="padding:5px;">' + (it[3]||'—') + '</td>';
    html += '<td style="padding:5px;text-align:right;">' + (it[4]||0) + ' g</td>';
    html += '<td style="padding:5px;"><input type="number" id="recv-'+i+'" data-cod="'+(it[2]||'')+'" data-nom="'+(it[3]||'')+'" value="'+(it[4]||0)+'" min="0" step="0.01" style="width:80px;text-align:right;"></td></tr>';
  });
  html += '</tbody></table>';
  html += '<div style="margin-top:10px;font-size:12px;color:#888;">Modifica las cantidades si la recepcion fue parcial.</div>';
  document.getElementById('recibir-items-list').innerHTML = html;
  document.getElementById('recibir-msg').innerHTML = '';
  openModal('modal-oc-recibir');
}

async function confirmarRecepcion(){
  var items = [];
  document.querySelectorAll('[id^="recv-"]').forEach(function(inp){
    var cant = parseFloat(inp.value) || 0;
    if(cant > 0) items.push({codigo_mp: inp.dataset.cod, nombre_mp: inp.dataset.nom, cantidad_recibida: cant});
  });
  if(!items.length){ alert('Ingresa al menos una cantidad'); return; }
  var r = await fetch('/api/ordenes-compra/' + _recibirOCNum + '/recibir', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({items_recibidos: items})
  });
  var d = await r.json();
  if(d.ok){
    document.getElementById('recibir-msg').innerHTML = '<div class="msg-ok">Recepcion registrada. ' + d.ingresos + ' ingreso(s) en inventario.</div>';
    setTimeout(function(){ closeModal('modal-oc-recibir'); loadOCs(); loadDashboard(); }, 1500);
  } else {
    document.getElementById('recibir-msg').innerHTML = '<div class="msg-err">' + (d.error||'Error') + '</div>';
  }
}
```

**Modificar backend `recibir_oc()`:**
```python
@app.route('/api/ordenes-compra/<numero_oc>/recibir', methods=['POST'])
def recibir_oc(numero_oc):
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    d = request.get_json() or {}
    items_recibidos = d.get('items_recibidos')  # None = recibir todo
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute("SELECT estado, proveedor FROM ordenes_compra WHERE numero_oc=?", (numero_oc,))
    oc_row = cur.fetchone()
    if not oc_row:
        conn.close(); return jsonify({'error': 'OC no encontrada'}), 404
    prov_nombre = oc_row[1] or ''
    if items_recibidos is None:
        # Recibir todo (comportamiento original)
        cur.execute("SELECT codigo_mp, nombre_mp, cantidad_g FROM ordenes_compra_items WHERE numero_oc=?", (numero_oc,))
        items_to_recv = [{'codigo_mp':r[0],'nombre_mp':r[1],'cantidad_recibida':r[2]} for r in cur.fetchall()]
    else:
        items_to_recv = items_recibidos
    fecha = datetime.now().isoformat()
    for item in items_to_recv:
        if item.get('cantidad_recibida', 0) <= 0:
            continue
        cur.execute("""INSERT INTO movimientos
            (material_id, material_nombre, cantidad, tipo, fecha, observaciones, proveedor, operador)
            VALUES (?,?,?,?,?,?,?,?)""",
            (item.get('codigo_mp',''), item.get('nombre_mp',''), item['cantidad_recibida'],
             'ingreso', fecha, f'Recepcion OC {numero_oc}', prov_nombre,
             session.get('compras_user','')))
    # Determinar si fue recepción total o parcial
    total_pedido = sum(i.get('cantidad_recibida',0) for i in items_to_recv)
    nuevo_estado = 'Recibida'  # podría ser 'Recibida parcialmente' con lógica adicional
    cur.execute("UPDATE ordenes_compra SET estado=? WHERE numero_oc=?", (nuevo_estado, numero_oc,))
    conn.commit(); conn.close()
    return jsonify({'ok': True, 'numero_oc': numero_oc, 'ingresos': len(items_to_recv)})
```

**Cambiar botón "Recibir" en `loadOCs()`** para que llame `abrirRecepcionOC()` en lugar de `recibirOC()`:
```javascript
var bR = pR ? '<button class="btn btn-sm" style="margin-left:6px;background:#2B7A78;" onclick="abrirRecepcionOC(&quot;'+o.numero_oc+'&quot;)">Recibir</button>' : '';
```

---

## FASE 3 — Analytics de compras (~2h)
> **Objetivo:** Datos para tomar decisiones

### F3-1: Dashboard analytics mejorado

**Nuevos endpoints:**
```python
@app.route('/api/compras/analytics')
def compras_analytics():
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()

    # Gasto mensual por categoría (últimos 6 meses)
    c.execute("""
        SELECT strftime('%Y-%m', s.fecha) as mes,
               s.categoria,
               SUM(si.valor_estimado) as total
        FROM solicitudes_compra s
        JOIN solicitudes_compra_items si ON s.numero=si.numero
        WHERE s.estado IN ('Aprobada','Completada')
          AND s.fecha >= date('now','-6 months')
        GROUP BY mes, s.categoria
        ORDER BY mes DESC
    """)
    gasto_cat = [dict(zip(['mes','categoria','total'], r)) for r in c.fetchall()]

    # OCs por estado
    c.execute("SELECT estado, COUNT(*) FROM ordenes_compra GROUP BY estado")
    ocs_estado = [dict(zip(['estado','count'], r)) for r in c.fetchall()]

    # Top 5 proveedores por valor total de OCs
    c.execute("""
        SELECT proveedor, COUNT(*) as num_ocs,
               COALESCE(SUM(valor_total),0) as total_valor
        FROM ordenes_compra
        WHERE estado NOT IN ('Cancelada','Borrador')
        GROUP BY proveedor
        ORDER BY total_valor DESC
        LIMIT 5
    """)
    top_provs = [dict(zip(['proveedor','num_ocs','total_valor'], r)) for r in c.fetchall()]

    # Tiempo promedio entrega por proveedor (días entre fecha y recepción)
    c.execute("""
        SELECT proveedor,
               AVG(CAST((julianday(fecha_recepcion) - julianday(fecha)) AS REAL)) as dias_promedio,
               COUNT(*) as total_ocs
        FROM (
            SELECT oc.proveedor, oc.fecha,
                   MAX(CASE WHEN l.accion='recepcion' THEN l.fecha END) as fecha_recepcion
            FROM ordenes_compra oc
            LEFT JOIN ordenes_compra_log l ON oc.numero_oc=l.numero_oc
            GROUP BY oc.numero_oc
        )
        WHERE fecha_recepcion IS NOT NULL
        GROUP BY proveedor
        ORDER BY dias_promedio ASC
    """)
    entrega_provs = [dict(zip(['proveedor','dias_promedio','total_ocs'], r)) for r in c.fetchall()]

    # Solicitudes pendientes de este mes
    c.execute("""
        SELECT COUNT(*) FROM solicitudes_compra
        WHERE estado='Pendiente'
          AND strftime('%Y-%m', fecha) = strftime('%Y-%m', 'now')
    """)
    sol_pendientes_mes = c.fetchone()[0]

    conn.close()
    return jsonify({
        'gasto_cat': gasto_cat,
        'ocs_estado': ocs_estado,
        'top_provs': top_provs,
        'entrega_provs': entrega_provs,
        'sol_pendientes_mes': sol_pendientes_mes
    })
```

**Nueva sección "Analytics" en dashboard frontend:**
```javascript
async function loadDashboard(){
  // ... (código existente) ...
  // Agregar:
  var ra2 = await fetch('/api/compras/analytics').then(r=>r.json());
  renderAnalytics(ra2);
}

function renderAnalytics(data){
  // OCs por estado — donut simple con CSS
  var estados = data.ocs_estado || [];
  var estColors = {
    'Borrador':'#94a3b8','Pendiente':'#fbbf24','Aprobada':'#60a5fa',
    'Enviada':'#a78bfa','En transito':'#f97316','Recibida':'#34d399','Pagada':'#10b981','Cancelada':'#f87171'
  };
  var totalOCs = estados.reduce(function(a,b){ return a + b.count; }, 0);
  var donutHTML = estados.map(function(e){
    var pct = totalOCs > 0 ? Math.round(e.count/totalOCs*100) : 0;
    return '<div style="display:flex;align-items:center;gap:8px;margin-bottom:5px;">' +
      '<div style="width:12px;height:12px;border-radius:3px;background:'+(estColors[e.estado]||'#ddd')+'"></div>' +
      '<span style="font-size:12px;flex:1;">' + e.estado + '</span>' +
      '<span style="font-weight:700;font-size:13px;">' + e.count + '</span>' +
      '<span style="color:#aaa;font-size:11px;">'+pct+'%</span></div>';
  }).join('');

  // Top proveedores
  var provHTML = (data.top_provs||[]).map(function(p, i){
    var bar = data.top_provs[0].total_valor > 0
      ? Math.round(p.total_valor / data.top_provs[0].total_valor * 100)
      : 0;
    return '<div style="margin-bottom:8px;">' +
      '<div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:3px;">' +
      '<span>' + p.proveedor + '</span>' +
      '<span style="font-weight:600;">' + (p.total_valor>0?'$'+p.total_valor.toLocaleString('es-CO'):'—') + '</span></div>' +
      '<div style="height:6px;background:#f0f0f0;border-radius:3px;"><div style="height:6px;width:'+bar+'%;background:#2B7A78;border-radius:3px;"></div></div>' +
      '</div>';
  }).join('');

  // Tiempo entrega
  var entHTML = (data.entrega_provs||[]).slice(0,5).map(function(p){
    var dias = p.dias_promedio ? p.dias_promedio.toFixed(1) : '—';
    var color = p.dias_promedio <= 7 ? '#16a34a' : p.dias_promedio <= 14 ? '#d97706' : '#dc2626';
    return '<tr><td style="padding:5px;font-size:12px;">'+p.proveedor+'</td>' +
      '<td style="padding:5px;text-align:right;font-weight:700;font-size:13px;color:'+color+';">'+dias+'d</td>' +
      '<td style="padding:5px;text-align:right;font-size:11px;color:#aaa;">'+p.total_ocs+' OCs</td></tr>';
  }).join('');

  document.getElementById('analytics-panel').innerHTML =
    '<div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">' +
      '<div><div style="font-size:11px;text-transform:uppercase;color:#888;font-weight:700;letter-spacing:.5px;margin-bottom:10px;">OCs por Estado</div>' + donutHTML + '</div>' +
      '<div><div style="font-size:11px;text-transform:uppercase;color:#888;font-weight:700;letter-spacing:.5px;margin-bottom:10px;">Top Proveedores</div>' + provHTML + '</div>' +
    '</div>' +
    '<div style="margin-top:20px;"><div style="font-size:11px;text-transform:uppercase;color:#888;font-weight:700;letter-spacing:.5px;margin-bottom:10px;">Tiempo Promedio de Entrega</div>' +
    '<table style="width:100%;border-collapse:collapse;">' + (entHTML||'<tr><td colspan="3" style="color:#aaa;font-size:12px;padding:8px;">Sin datos aún</td></tr>') + '</table></div>';
}
```

**HTML — agregar panel en tab dashboard:**
```html
<!-- En #dashboard, después de la tabla de solicitudes -->
<div class="card" style="margin-top:20px;">
  <div style="font-size:14px;font-weight:700;margin-bottom:16px;">Analytics</div>
  <div id="analytics-panel"><div style="color:#aaa;font-size:13px;">Cargando...</div></div>
</div>
```

---

## FASE 4 — Inteligencia de precios (~2h)
> **Objetivo:** Negociar mejor, detectar aumentos

### F4-1: Tabla precios_historicos

**Nueva tabla en `init_db()`:**
```python
c.execute("""CREATE TABLE IF NOT EXISTS precios_historicos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo_mp TEXT,
    nombre_mp TEXT,
    proveedor TEXT,
    precio_unitario REAL,
    unidad TEXT DEFAULT 'g',
    fecha TEXT,
    numero_oc TEXT
)""")
```

**Poblar automáticamente en `recibir_oc()`:**
```python
# Después de registrar los movimientos de ingreso:
cur.execute("SELECT codigo_mp, nombre_mp, precio_unitario FROM ordenes_compra_items WHERE numero_oc=? AND precio_unitario > 0", (numero_oc,))
for it in cur.fetchall():
    cur.execute("INSERT INTO precios_historicos (codigo_mp,nombre_mp,proveedor,precio_unitario,unidad,fecha,numero_oc) VALUES (?,?,?,?,?,?,?)",
        (it[0], it[1], prov_nombre, it[2], 'g', fecha, numero_oc))
```

### F4-2: Vista de precios históricos por MP

**Nuevo endpoint:**
```python
@app.route('/api/precios-historicos')
def get_precios_historicos():
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    codigo_mp = request.args.get('codigo_mp', '')
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    sql = """SELECT codigo_mp, nombre_mp, proveedor, precio_unitario, unidad, fecha, numero_oc
             FROM precios_historicos WHERE 1=1"""
    params = []
    if codigo_mp:
        sql += " AND codigo_mp=?"; params.append(codigo_mp)
    sql += " ORDER BY fecha DESC LIMIT 100"
    c.execute(sql, params)
    cols = ['codigo_mp','nombre_mp','proveedor','precio_unitario','unidad','fecha','numero_oc']
    rows = [dict(zip(cols, r)) for r in c.fetchall()]
    conn.close()
    return jsonify({'precios': rows})
```

**Mostrar en modal de OC (en `verOC()`):**
```javascript
// Agregar sección "Historial de precios" en modal cuando hay items:
var codigos = items.map(function(it){ return it[2]; }).filter(Boolean);
if(codigos.length){
  var ph = await fetch('/api/precios-historicos?codigo_mp=' + codigos[0]).then(r=>r.json());
  if(ph.precios && ph.precios.length){
    h += '<div style="margin-top:16px;font-size:12px;color:#888;">Últimos precios registrados para ' + codigos[0] + ':</div>';
    h += '<table style="width:100%;font-size:12px;border-collapse:collapse;">';
    ph.precios.slice(0,5).forEach(function(p){
      h += '<tr><td style="padding:3px 6px;">' + (p.fecha||'').substring(0,10) + '</td>';
      h += '<td style="padding:3px 6px;color:#666;">' + p.proveedor + '</td>';
      h += '<td style="padding:3px 6px;text-align:right;font-weight:600;">$' + p.precio_unitario + '/g</td>';
      h += '<td style="padding:3px 6px;font-family:monospace;font-size:11px;color:#aaa;">' + p.numero_oc + '</td></tr>';
    });
    h += '</table>';
  }
}
```

---

## FASE 5 — Proveedores 360° (~2h)
> **Objetivo:** Gestión completa + calificación BPM

### F5-1: Nuevas tablas

```python
c.execute("""CREATE TABLE IF NOT EXISTS proveedores_contactos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    proveedor_nombre TEXT NOT NULL,
    nombre_contacto TEXT,
    rol TEXT,
    email TEXT,
    telefono TEXT,
    principal INTEGER DEFAULT 0,
    activo INTEGER DEFAULT 1
)""")

c.execute("""CREATE TABLE IF NOT EXISTS proveedores_evaluaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    proveedor_nombre TEXT NOT NULL,
    fecha TEXT,
    entregas_a_tiempo INTEGER,  -- 0-5
    pedidos_completos INTEGER,  -- 0-5
    calidad_producto INTEGER,   -- 0-5
    documentacion INTEGER,      -- 0-5 (COA, fichas)
    precio_competitivo INTEGER, -- 0-5
    calificador TEXT,
    observaciones TEXT,
    score_total REAL            -- calculado
)""")

# Agregar columnas a proveedores existente (migration):
try: c.execute("ALTER TABLE proveedores ADD COLUMN estado_calificacion TEXT DEFAULT 'En evaluacion'")
except: pass
try: c.execute("ALTER TABLE proveedores ADD COLUMN fecha_ultima_eval TEXT")
except: pass
try: c.execute("ALTER TABLE proveedores ADD COLUMN nit TEXT")
except: pass
try: c.execute("ALTER TABLE proveedores ADD COLUMN direccion TEXT")
except: pass
try: c.execute("ALTER TABLE proveedores ADD COLUMN ciudad TEXT")
except: pass
```

### F5-2: Vista de proveedor ampliada (modal con tabs)

```javascript
async function verProveedor(nombre){
  // Modal con tabs: Info | OCs | Evaluacion
  openModal('modal-prov-det');
  var d = await fetch('/api/proveedores-compras/' + encodeURIComponent(nombre)).then(r=>r.json());
  var prov = d.proveedor || {};
  var ocs = d.ocs || [];
  var evals = d.evaluaciones || [];

  var estadoColor = {
    'Calificado': '#dcfce7', 'En evaluacion': '#fef9c3', 'Suspendido': '#fee2e2'
  };
  var bg = estadoColor[prov.estado_calificacion] || '#f0f0f0';

  var h = '<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:20px;">';
  h += '<div><h3 style="font-size:18px;font-weight:800;margin:0;">'+prov.nombre+'</h3>';
  h += '<div style="font-size:12px;color:#888;margin-top:2px;">'+(prov.categoria||'')+(prov.ciudad?' · '+prov.ciudad:'')+'</div></div>';
  h += '<div style="background:'+bg+';padding:4px 12px;border-radius:12px;font-size:12px;font-weight:700;">'+(prov.estado_calificacion||'En evaluacion')+'</div></div>';

  // Score promedio
  if(evals.length){
    var avgScore = evals.reduce(function(a,e){ return a+e.score_total; },0) / evals.length;
    h += '<div style="background:#f8fafc;border-radius:8px;padding:12px 16px;margin-bottom:16px;display:flex;align-items:center;gap:20px;">';
    h += '<div style="font-size:32px;font-weight:900;color:#2B7A78;">' + avgScore.toFixed(1) + '</div>';
    h += '<div style="font-size:12px;color:#666;">Score promedio<br>(' + evals.length + ' evaluacion(es))</div>';
    h += '</div>';
  }

  // Historial de OCs
  h += '<div style="font-size:11px;font-weight:700;color:#888;text-transform:uppercase;margin-bottom:8px;">OCs recientes</div>';
  if(ocs.length){
    h += '<table style="width:100%;border-collapse:collapse;font-size:12px;margin-bottom:16px;">';
    ocs.slice(0,5).forEach(function(o){
      h += '<tr><td style="padding:4px 6px;font-family:monospace;color:#2B7A78;font-weight:700;">' + o.numero_oc + '</td>';
      h += '<td style="padding:4px 6px;">' + (o.fecha||'').substring(0,10) + '</td>';
      h += '<td style="padding:4px 6px;">' + badgeEstado(o.estado) + '</td>';
      h += '<td style="padding:4px 6px;text-align:right;">' + (o.valor_total>0?'$'+o.valor_total.toLocaleString('es-CO'):'—') + '</td></tr>';
    });
    h += '</table>';
  } else {
    h += '<p style="font-size:12px;color:#aaa;">Sin OCs registradas</p>';
  }

  document.getElementById('modal-prov-det-content').innerHTML = h;
}
```

**Nuevo endpoint:**
```python
@app.route('/api/proveedores-compras/<nombre_proveedor>')
def get_proveedor_detalle(nombre_proveedor):
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    nombre = nombre_proveedor  # ya viene URL-decoded por Flask
    c.execute("SELECT nombre,contacto,email,telefono,categoria,condiciones_pago,estado_calificacion,fecha_ultima_eval,nit,direccion,ciudad FROM proveedores WHERE nombre=?", (nombre,))
    row = c.fetchone()
    if not row:
        conn.close(); return jsonify({'error': 'No encontrado'}), 404
    cols = ['nombre','contacto','email','telefono','categoria','condiciones_pago','estado_calificacion','fecha_ultima_eval','nit','direccion','ciudad']
    prov = dict(zip(cols, row))

    # OCs del proveedor
    c.execute("SELECT numero_oc,fecha,estado,valor_total FROM ordenes_compra WHERE proveedor=? ORDER BY fecha DESC LIMIT 10", (nombre,))
    ocs = [dict(zip(['numero_oc','fecha','estado','valor_total'], r)) for r in c.fetchall()]

    # Evaluaciones
    c.execute("SELECT fecha,score_total,calificador,observaciones FROM proveedores_evaluaciones WHERE proveedor_nombre=? ORDER BY fecha DESC", (nombre,))
    evals = [dict(zip(['fecha','score_total','calificador','observaciones'], r)) for r in c.fetchall()]

    conn.close()
    return jsonify({'proveedor': prov, 'ocs': ocs, 'evaluaciones': evals})
```

### F5-3: Formulario de evaluación de proveedor

```javascript
function abrirEvalProveedor(nombre){
  var h = '<h3 style="font-size:16px;font-weight:700;margin-bottom:16px;">Evaluar: '+nombre+'</h3>';
  var criterios = [
    ['entregas_a_tiempo','Entregas a tiempo'],
    ['pedidos_completos','Pedidos completos'],
    ['calidad_producto','Calidad del producto'],
    ['documentacion','Documentacion (COA, fichas)'],
    ['precio_competitivo','Precio competitivo']
  ];
  criterios.forEach(function(cr){
    h += '<div style="margin-bottom:12px;">';
    h += '<label style="font-size:13px;font-weight:600;display:block;margin-bottom:5px;">'+cr[1]+'</label>';
    h += '<div style="display:flex;gap:6px;">';
    [1,2,3,4,5].forEach(function(n){
      h += '<button class="eval-btn" data-field="'+cr[0]+'" data-val="'+n+'" '+
        'onclick="selectEval(this)" '+
        'style="width:36px;height:36px;border:1px solid #ddd;border-radius:6px;cursor:pointer;font-weight:700;background:#fff;">'+n+'</button>';
    });
    h += '</div></div>';
  });
  h += '<div style="margin-bottom:12px;"><label style="font-size:13px;font-weight:600;">Observaciones</label>';
  h += '<textarea id="eval-obs" style="width:100%;margin-top:5px;border:1px solid #ddd;border-radius:6px;padding:8px;" rows="2"></textarea></div>';
  h += '<button class="btn" onclick="guardarEval(\''+nombre+'\')">Guardar evaluacion</button>';
  h += '<div id="eval-msg"></div>';
  document.getElementById('modal-prov-det-content').innerHTML = h;
}

function selectEval(btn){
  var field = btn.dataset.field;
  document.querySelectorAll('[data-field="'+field+'"]').forEach(function(b){
    b.style.background='#fff'; b.style.borderColor='#ddd'; b.style.color='#333';
  });
  btn.style.background = '#2B7A78'; btn.style.color = '#fff'; btn.style.borderColor = '#2B7A78';
}

async function guardarEval(nombre){
  var scores = {};
  ['entregas_a_tiempo','pedidos_completos','calidad_producto','documentacion','precio_competitivo'].forEach(function(f){
    var sel = document.querySelector('[data-field="'+f+'"][style*="#2B7A78"]');
    scores[f] = sel ? parseInt(sel.dataset.val) : null;
  });
  var total = Object.values(scores).filter(Boolean);
  var scoreTotal = total.length ? total.reduce(function(a,b){ return a+b; },0) / total.length : 0;
  var r = await fetch('/api/proveedores-compras/' + encodeURIComponent(nombre) + '/evaluar', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({...scores, score_total: scoreTotal.toFixed(2), observaciones: document.getElementById('eval-obs').value})
  });
  var d = await r.json();
  if(d.ok){
    document.getElementById('eval-msg').innerHTML = '<div class="msg-ok">Evaluacion guardada. Score: '+scoreTotal.toFixed(1)+'/5</div>';
    setTimeout(function(){ loadProveedores(); }, 1200);
  }
}
```

---

## FASE 6 — BPM / Regulatorio (~1h)
> **Objetivo:** Cumplimiento INVIMA / ISO

### F6-1: Estado de calificación en flujo de OC

**Advertencia al crear OC con proveedor no calificado:**
```python
# En handle_ordenes_compra() POST, verificar estado del proveedor:
prov_nombre = d['proveedor']
c.execute("SELECT estado_calificacion FROM proveedores WHERE nombre=?", (prov_nombre,))
prov_row = c.fetchone()
prov_advertencia = ''
if prov_row and prov_row[0] == 'Suspendido':
    conn.close()
    return jsonify({'error': f'Proveedor {prov_nombre} está SUSPENDIDO. No se puede crear OC.'}), 400
if not prov_row or prov_row[0] == 'En evaluacion':
    prov_advertencia = f'ADVERTENCIA: {prov_nombre} está en evaluación.'
# Devolver advertencia en el response:
return jsonify({'message': f'OC {numero_oc} creada', 'numero_oc': numero_oc, 'advertencia': prov_advertencia}), 201
```

**Frontend — mostrar advertencia:**
```javascript
// En crearOC(), si res.advertencia:
if(res.advertencia){
  document.getElementById('oc-msg').innerHTML =
    '<div class="msg-ok">' + res.message + '</div>' +
    '<div style="background:#fef9c3;border-left:3px solid #f59e0b;padding:8px 12px;border-radius:4px;font-size:12px;margin-top:6px;">' + res.advertencia + '</div>';
} else {
  document.getElementById('oc-msg').innerHTML = '<div class="msg-ok">' + res.message + '</div>';
}
```

### F6-2: Registros de recepción con lote y COA

**Nueva tabla:**
```python
c.execute("""CREATE TABLE IF NOT EXISTS recepciones_mp (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_oc TEXT,
    codigo_mp TEXT,
    nombre_mp TEXT,
    cantidad_recibida REAL,
    unidad TEXT DEFAULT 'g',
    numero_lote TEXT,
    fecha_vencimiento TEXT,
    coa_estado TEXT DEFAULT 'Pendiente',  -- 'Pendiente','Recibido','Aprobado','Rechazado'
    fecha_recepcion TEXT,
    operador TEXT,
    observaciones TEXT
)""")
```

**En el modal de recepción (F2-5), agregar campos de lote y COA por ítem:**
```javascript
// En abrirRecepcionOC(), agregar en cada fila:
'<input type="text" id="lote-'+i+'" placeholder="Lote" style="width:90px;">' +
'<input type="date" id="venc-'+i+'" style="width:110px;">' +
'<select id="coa-'+i+'"><option value="Pendiente">COA Pendiente</option><option value="Recibido">COA OK</option></select>'
```

**Y en `confirmarRecepcion()`, guardar esos datos:**
```javascript
items.push({
  codigo_mp: inp.dataset.cod,
  nombre_mp: inp.dataset.nom,
  cantidad_recibida: cant,
  numero_lote: document.getElementById('lote-'+i).value,
  fecha_vencimiento: document.getElementById('venc-'+i).value,
  coa_estado: document.getElementById('coa-'+i).value
});
```

**En backend, insertar en recepciones_mp y también crear lote en el sistema de inventario.**

### F6-3: Panel de COAs pendientes

**En el tab "Alertas", agregar sección:**
```python
# Nuevo endpoint:
@app.route('/api/compras/coas-pendientes')
def coas_pendientes():
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""
        SELECT r.codigo_mp, r.nombre_mp, r.numero_lote, r.fecha_recepcion, r.numero_oc
        FROM recepciones_mp r
        WHERE r.coa_estado='Pendiente'
        ORDER BY r.fecha_recepcion DESC
    """)
    cols = ['codigo_mp','nombre_mp','numero_lote','fecha_recepcion','numero_oc']
    rows = [dict(zip(cols, r)) for r in c.fetchall()]
    conn.close()
    return jsonify({'coas_pendientes': rows})
```

---

## MIGRACIÓN DE DB — SCRIPT CONSOLIDADO

Todas las nuevas tablas y columnas en orden (para pegar en `init_db()`):
```python
# Fase 2
c.execute("""CREATE TABLE IF NOT EXISTS ordenes_compra_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_oc TEXT NOT NULL,
    accion TEXT NOT NULL,
    estado_anterior TEXT,
    estado_nuevo TEXT,
    usuario TEXT,
    fecha TEXT,
    notas TEXT
)""")

# Fase 4
c.execute("""CREATE TABLE IF NOT EXISTS precios_historicos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo_mp TEXT,
    nombre_mp TEXT,
    proveedor TEXT,
    precio_unitario REAL,
    unidad TEXT DEFAULT 'g',
    fecha TEXT,
    numero_oc TEXT
)""")

# Fase 5
c.execute("""CREATE TABLE IF NOT EXISTS proveedores_contactos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    proveedor_nombre TEXT NOT NULL,
    nombre_contacto TEXT,
    rol TEXT,
    email TEXT,
    telefono TEXT,
    principal INTEGER DEFAULT 0,
    activo INTEGER DEFAULT 1
)""")

c.execute("""CREATE TABLE IF NOT EXISTS proveedores_evaluaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    proveedor_nombre TEXT NOT NULL,
    fecha TEXT,
    entregas_a_tiempo INTEGER,
    pedidos_completos INTEGER,
    calidad_producto INTEGER,
    documentacion INTEGER,
    precio_competitivo INTEGER,
    calificador TEXT,
    observaciones TEXT,
    score_total REAL
)""")

try: c.execute("ALTER TABLE proveedores ADD COLUMN estado_calificacion TEXT DEFAULT 'En evaluacion'")
except: pass
try: c.execute("ALTER TABLE proveedores ADD COLUMN fecha_ultima_eval TEXT")
except: pass
try: c.execute("ALTER TABLE proveedores ADD COLUMN nit TEXT")
except: pass
try: c.execute("ALTER TABLE proveedores ADD COLUMN direccion TEXT")
except: pass
try: c.execute("ALTER TABLE proveedores ADD COLUMN ciudad TEXT")
except: pass

# Fase 6
c.execute("""CREATE TABLE IF NOT EXISTS recepciones_mp (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_oc TEXT,
    codigo_mp TEXT,
    nombre_mp TEXT,
    cantidad_recibida REAL,
    unidad TEXT DEFAULT 'g',
    numero_lote TEXT,
    fecha_vencimiento TEXT,
    coa_estado TEXT DEFAULT 'Pendiente',
    fecha_recepcion TEXT,
    operador TEXT,
    observaciones TEXT
)""")
```

---

## ORDEN DE IMPLEMENTACIÓN (FIN DE SEMANA)

### Sábado mañana (~2-3h)
- [ ] F1-1: Fix cantidad_solicitada
- [ ] F1-2: Form OC con nombre_mp
- [ ] F1-3: Modal detalle OC
- [ ] F1-4: Tabla solicitudes con categoría y valor
- [ ] F2-3: Audit trail (fácil, alta visibilidad)
- [ ] F2-4: Valor total OC

### Sábado tarde (~3h)
- [ ] F2-1: Autocomplete MP en OC form
- [ ] F2-2: PDF de OC (ruta /compras/oc/<num>/print)
- [ ] F2-5: Recepción parcial
- [ ] F3-1: Analytics dashboard

### Domingo (~3h)
- [ ] F4-1/F4-2: Precios históricos
- [ ] F5-1/F5-2/F5-3: Proveedores 360° + evaluación
- [ ] F6-1/F6-2/F6-3: BPM — calificación + COAs

---

*Total estimado: 8-9h de implementación. Todo el código está listo arriba.*
*Cada fase es independiente — si algo se complica se puede saltar y volver.*
