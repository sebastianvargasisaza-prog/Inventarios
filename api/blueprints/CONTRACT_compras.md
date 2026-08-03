# CONTRACT · `compras.py`

> **Para agentes IA · LEER ANTES de modificar este blueprint.**

Última revisión: 2026-05-19

---

## Tablas que ESCRIBE

| Tabla | Operación | Cuándo |
|---|---|---|
| `solicitudes_compra` | INSERT/UPDATE/DELETE | Crear SOL, aprobar, limpiar planta |
| `solicitudes_compra_items` | INSERT/UPDATE/DELETE | Items de SOL |
| `ordenes_compra` | INSERT/UPDATE | Crear OC desde SOL, aprobar, recibir |
| `oc_items` | INSERT/UPDATE | Items de OC |
| `pagos_oc` | INSERT | Pago registrado |
| `comprobantes_pago` | INSERT | PDF generado |
| `maestro_mps` | UPDATE | Sync proveedor desde PATCH SOL |
| `mp_lead_time_config` | INSERT/UPDATE | Sync proveedor + crear si falta |
| `precio_historico_mp` | INSERT | Cambio de precio_unit_g en SOL |
| `audit_log` | INSERT | Cada operación |

---

## Invariantes CRÍTICAS · NO romper

### INV-1 · 3 fuentes de SOL no se mezclan
Filtros `?fuente=` en `/api/solicitudes-compra` y `/agrupadas-por-proveedor`:
- `planta`: `categoria IN ('Materia Prima','Empaque','Material de Empaque')`
- `usuarios`: `categoria NOT IN (planta + influencer)`
- `influencers`: `categoria IN ('Influencer/Marketing Digital','Cuenta de Cobro')`
- Sin param: legacy compatible (todas).

### INV-2 · PATCH item sincroniza GLOBAL
Cuando Catalina edita un item:
- `proveedor` cambió → UPDATE `maestro_mps.proveedor` + UPSERT
  `mp_lead_time_config.proveedor_principal`.
- `precio_unit_g` cambió → UPDATE `maestro_mps.precio_referencia` =
  `precio_unit_g * 1000` ($/kg).
- Audit: `SYNC_PROVEEDOR_GLOBAL`.
- **GOLDEN PATH 3** lo verifica.

### INV-3 · Solo admin puede modificar permisos / aprobar override
- `_require_admin` para reset password, hard delete SOL, override aprobación.
- `_require_compras_write` para CRUD SOL/OC normal (compras + admin).

### INV-4 · No revertir Pago en Pagada
- Una OC marcada como Pagada NO puede volver a Borrador.
- Si error, crear OC nueva o cancelar la actual con motivo (audit).

### INV-5 · Limpiar SOLs planta solo no-OC
- `/limpiar-solicitudes-planta` borra solo `estado='Pendiente'` AND
  `numero_oc=''`. NUNCA toca SOLs con OC vinculada.

### INV-6 · Recepción rotula el kardex por INCI, no por comercial (Sebastián 12-jun)
- En `recibir_oc` el `movimientos.material_nombre` se escribe con el **INCI**
  (`maestro_mps.nombre_inci`), no con el `nombre_mp` comercial de la OC. Cae al
  **código** si no hay INCI (nunca al comercial, nunca en blanco). Identidad
  sigue siendo el código (`material_id`). El comercial NO se borra: queda en
  `ordenes_compra_items.nombre_mp` y `maestro_mps.nombre_comercial`.
- Mismo criterio en el ingreso manual `inventario.py /api/recepcion` y en el
  panel `/api/recepcion/detalle` (devuelve `inci`; el front muestra `INCI (código)`).
- Motivo: el comercial varía por proveedor y era la mayor fuente de error en
  recepción. Tests: `tests/test_recepcion_ingreso_inci.py`.

### INV-10 · El PERÍODO de un egreso sale de la FECHA DEL PAGO, nunca del reloj (27-jul)
- Al espejar un pago de OC a `flujo_egresos`, `periodo = fecha_pago[:7]`. Antes
  salía de `datetime.now()`, y eso partía la fila en dos meses de dos maneras:
  (a) un pago registrado hoy con **fecha retroactiva** guardaba `fecha` del mes
  pasado y `periodo` del mes en curso; (b) `now()` es **UTC** en Render, así que
  después de las 19:00 en Colombia un pago de fin de mes ya contaba en el mes
  siguiente (M24).
- Corolario para todo el módulo: el "hoy" de compras se toma de
  `tz_colombia.hoy_colombia()`, nunca de `date.today()`. Aplica también al corte
  de "ya venció" al validar recepciones: con UTC, un lote que vence HOY se
  marcaba vencido desde las 19:00 de la víspera.
- Guardado por `tests/test_hoy_colombia_dinero.py` (barre los 6 módulos de dinero
  por el patrón y falla si vuelve a aparecer). Ver M106 en `.claude/CERO_ERROR.md`.

### INV-11 · La recepción ADMINISTRATIVA no exige datos que sólo Calidad puede tomar (27-jul)
- `recibir_oc` ya **no bloquea** por falta de `lote_proveedor`. Quien recibe (Catalina) cuenta
  lo que llegó; el lote real, el peso en balanza y el vencimiento los lee **Calidad** del envase
  físico en el F01. Exigirlos antes dejaba la recepción administrativa sin poder cerrarse.
- El control INVIMA **se movió, no se quitó** (M39): el material entra en CUARENTENA (el FEFO la
  excluye → no se puede consumir), si no hubo lote se asigna uno sintético `OC-<numero>-<n>` y se
  devuelve en `lotes_sinteticos`, y **`/api/lotes/liberar` rechaza APROBAR un lote sintético**
  (`LOTE_SINTETICO_SIN_LIBERAR`, 422). RECHAZAR sí se permite: trabar un rechazo dejaría material
  malo atascado en cuarentena.
- **`lote_proveedor` cae a `lote`**: la pantalla tiene UN campo de lote y mandaba `lote`, mientras
  el backend leía `lote_proveedor` → el lote tecleado se descartaba en silencio y la validación lo
  veía siempre vacío (422 aunque lo escribiera). Una llave que se arma en dos lados coincide en los
  dos (M2).
- Tests: `tests/test_recepcion_administrativa.py` (en el gate).

---

## Endpoints downstream que CONSUMEN sus datos

| Endpoint externo | Lee | Si rompo `compras.py`... |
|---|---|---|
| `programacion.py /faltantes-bulk` | `solicitudes_compra` schema | ...bulk crea SOLs malformadas |
| `auto_plan.py /aplicar-plan` | `mp_lead_time_config` (sync) | ...auto_plan no ve nuevo proveedor |
| `inventario.py /maestro-mps` | `maestro_mps` (sync) | ...stock display con proveedor viejo |
| Tab Planta en `/compras` | `/agrupadas?fuente=planta` | ...Catalina ve mezclado |
| Tab Influencers | `?fuente=influencers` | ...se solapa con Marketing |

---

## Endpoints que expone

### Solicitudes
- `GET  /api/solicitudes-compra?fuente=...&categoria=...`
- `POST /api/solicitudes-compra` · crear (cualquier user)
- `PATCH /api/solicitudes-compra/<num>/items` · sync GLOBAL
- `POST /api/compras/limpiar-solicitudes-planta` · cleanup

### Agrupadas
- `GET /api/compras/solicitudes-agrupadas-por-proveedor?fuente=...`
- `POST /api/compras/consolidar-auto-pendientes`
- `POST /api/compras/limpiar-y-regenerar-auto-plan`

### Órdenes de compra
- `GET  /api/ordenes-compra` · listado filtrado
- `POST /api/ordenes-compra` · crear desde SOL
- `PATCH /api/ordenes-compra/<num>` · approve/cancel
- `POST /api/ordenes-compra/<num>/items` · agregar item
- `PATCH /api/ordenes-compra/<num>/items/<id>` · editar item
- `DELETE /api/ordenes-compra/<num>/items/<id>` · borrar item

### Pagos
- `POST /api/ordenes-compra/<num>/pagar` · registrar pago
  - Sincroniza `solicitudes_compra.estado='Pagada'` por `numero_oc` Y, si el body
    trae `sol_numero` (lo manda el front influencers), también por `numero` directo
    + re-vincula `numero_oc` (bulletproof contra links rotos · 2-jun-2026).
- `GET  /api/comprobantes-pago/<oc>` · PDF

### Influencers
- `GET  /api/solicitudes-compra?categoria=Influencer/Marketing Digital`
- `POST /api/compras/influencer/limpiar-no-pagadas`

---

## Cambios recientes (post-mortems)

### 2026-05-06 · 3 fuentes mezcladas en tab Solicitudes
- **Bug**: Catalina veía planta + influencer mezclado en tab "Solicitudes".
- **Fix**: `?fuente=` filter + 3 tabs separados en UI.
- **Test que cazaría**: `test_golden_3_fuentes_solicitudes_no_se_mezclan`.

### 2026-05-06 · PATCH no propagaba al cron
- **Bug**: cambiar proveedor en SOL no se reflejaba en próximo
  auto_plan (que lee `mp_lead_time_config` con COALESCE).
- **Fix**: PATCH ahora UPSERT a `mp_lead_time_config`.
- **Test que cazaría**: `test_golden_patch_sol_sincroniza_global`.

### 2026-05-19 · RBAC inconsistente · 4 endpoints sin guarda (auditoría)
- **Bug**: `DELETE /api/ordenes-compra/<oc>`, `POST /api/generar-oc-automatica`
  y `PATCH /api/solicitudes-compra/<n>/estado` no verificaban permisos de
  Compras (solo sesión, o nada); `PUT /api/ordenes-compra/<oc>` permitía
  revertir una OC Pagada a cualquier estado → violaba INV-4.
- **Fix**: los tres primeros ahora exigen `_require_compras_write`; el PUT
  rechaza cambiar el estado de una OC Pagada. Las cuatro operaciones auditan.

### 2026-05-19 · Hallazgos MEDIO de la auditoría
- `actualizar_precios_items_oc`: exige `_require_compras_write` y rechaza
  editar precios de una OC Pagada/Cancelada/Rechazada.
- `recibir_oc`: ahora acepta recibir una OC ya Pagada (anticipo / pago
  antes de recepción) — registra el kardex y deja el estado en Pagada,
  no lo revierte a Recibida (INV-4).
- `handle_proveedor` + endpoints MEE: exigen permiso de Compras y auditan;
  el rename de proveedor propaga también a `solicitudes_compra_items`.
- `update_sol_observaciones`: rechaza un UPDATE vacío con 400 en vez de 500.

### 2026-05-21 · Sesión enterprise zero-error · 70+ bugs cerrados

**Nuevos endpoints:**
- ~~`POST /api/compras/asistente-ia`~~ · ELIMINADO 16-jul (muerto · burbuja quitada 13-jul)
- `POST /api/compras/ocr-factura` · Claude Vision extrae factura proveedor
- `GET /api/compras/dashboard-home` · dashboard CONSOLIDADO (reemplaza 4 dashes legacy)
- `GET /api/compras/cash-flow` · proyección 30/60/90 días
- `GET /api/compras/trazabilidad-oc/<num>` · OC → SOL → producción → cliente
- `GET /api/compras/roi-proveedores` · ROI 12m con cumplimiento
- `GET /api/compras/proveedor-scorecard/<nombre>` · 5 métricas + score 0-100
- `GET|POST /api/compras/ordenes-servicio` · Serigrafía/Tampografía OS (mig 150)
- `GET /api/compras/prediccion-demanda` · con dedup cola (audit 22-may)

**Nuevas tablas (mig 150-154):**
- `ordenes_servicio` + `ordenes_servicio_eventos` · ciclo Catalina→Proveedor→Planta
- `movimientos.coa_url/coa_filename/lote_proveedor/ficha_seguridad_url` (mig 151 · INVIMA)
- 15 indexes performance hot path (mig 152)
- `ebr_ejecuciones` aliases columnas (mig 153)
- `formula_items.incluye_merma` flag opt-in (mig 154)

**Helpers compartidos nuevos:**
- `_pendiente_en_compras_g(c, codigo_mp)` · anti-duplicación SOLs cross-canales
- `_evaluar_auto_aprobacion(c, prov, monto, items)` · reglas auto-aprob
- `_enviar_oc_a_proveedor(...)` · email HTML al proveedor · **NO se dispara al autorizar** (15-jul: autorizar = aprobación INTERNA · el envío queda gated por `app_settings.compras_auto_email_oc` default OFF · el aviso al proveedor se replanteará junto con facturación, idealmente al PAGAR)
- `_scorecard_proveedor_dict(c, nombre_prov)` · 5 métricas live

**Variables env nuevas:**
- `COMPRAS_AUTO_APROB_OFF=1` · desactiva auto-aprobación reglas
- `COMPRAS_AUTO_APROB_LIMITE_COP=500000` · monto límite
- `COMPRAS_AUTO_APROB_REQ_SCORE=70` · score mínimo (opcional)
- `COMPRAS_AUTO_EMAIL_PROV_OFF=1` · (legacy) freno de emergencia al email · el default YA es NO enviar al autorizar (ver `app_settings.compras_auto_email_oc`)
- `BRD_CUARENTENA_MIN_DIAS=N` · tiempo mínimo antes liberar EBR
- `RRHH_BANCOS_JSON='[[...]]'` · cédulas+cuentas (PII fuera de código)

**Crons nuevos:**
- `auto_reparar_huerfanas` 4 AM · auto-repara formula_items con material_id huérfano
- `mee_drift_sync` 3 AM · resincroniza maestro_mee.stock_actual vs SUM(movimientos_mee)
- `pqr_sla_vencido` 8:15 AM · notif Ley 1755/2015 CO

**Invariantes nuevas (zero-error):**
1. CONTADORA NUNCA autoriza OCs (segregation of duties) · `_require_authorize_oc` bloquea
2. Influencers · datos bancarios SOLO admin (Habeas Data Ley 1581)
3. SOL DELETE: solo creador / admin / compras_access (no cualquier user)
4. Auto-aprobación: si OC cumple reglas (monto<X + recurrente + precio en rango + score opcional) → `Borrador → Autorizada` automático con `autorizado_por='auto-aprob-reglas'`
5. recibir_oc: bloquea `CATEGORIAS_PAGO_DIRECTO` (servicios sin material físico)
6. OCR factura: valida magic bytes (PDF rechazado · solo JPG/PNG)
7. Pagar Revisada bloqueado (bypass autorización gerencial)
8. autorizar_oc: CAS atómico anti-race
9. Borrar OC: revierte SOLs vinculadas a Pendiente automático
10. Cancelar producción: libera SOLs Pre-Producción asociadas

### 2026-05-22 · Auditoría abastecimiento · 12 bugs cerrados

**Bugs críticos cerrados:**
- Lead time: column real `lead_time_dias` (3 sitios escribían `dias_lead_time_promedio` inexistente)
- `_get_mp_stock` excluye CUARENTENA/VENCIDO/RECHAZADO/AGOTADO
- Ajuste/Ajuste+ suman en TODOS los cálculos de stock (4 sitios)
- Auto-SC IA fallback `cantidad_g_por_lote` cuando porcentaje=0
- Predicción demanda dedup `_pendiente_en_compras_g`
- Pre-Prod checklist dedup cross-checklist
- alertas-reabastecimiento incluye `en_cola_g`
- Auto-SC MEE dedup
- Urgencia con lead_time real (lt+3/+14/+30) en vez de ratios estáticos
- Flag `formula_items.incluye_merma=1` evita doble merma

**Tests goldens nuevos:** test_golden_abastecimiento_zero_error · test_golden_pendientes_audit_total.

### 2026-05-27 PM · Sesión mobile + performance audit
- **PERF FIX `_evaluar_auto_aprobacion`** (compras.py:252): antes N+1 (1
  SELECT precios_mp_historico por item · OCs grandes con 20+ items hacían
  20+ queries). Ahora 1 sola query `GROUP BY codigo_mp` pre-cargada en
  dict + lookup O(1) en loop. Verificable con OC de 30+ items.
- **No invariantes nuevas · solo performance**. INV-1..INV-5 intactas.

### 2026-06-01 · Libro de facturas de proveedor + dedup + audit de salud
**Tablas nuevas:** `facturas_proveedor` (mig 206), `facturas_proveedor_pdf` (mig 207
· blob del PDF en 1:1 · la tabla padre NO guarda el blob), `pagos_oc.factura_proveedor_id`
(liga pago→factura).

**Endpoints nuevos:**
- `GET/POST /api/compras/facturas-proveedor` · libro de cuentas por pagar + crear.
  GET sin SELECT* ni N+1 (pagado/valor_oc/tiene_pdf por LEFT JOIN · filtro q en SQL).
- `GET /api/compras/facturas-proveedor/<id>` · detalle con pagos.
- `GET /api/compras/facturas-proveedor/<id>/pdf` · sirve el PDF desde la tabla 1:1.
- `PATCH /api/compras/facturas-proveedor/<id>` · editar / anular.
- `POST /api/compras/facturas-proveedor/<id>/pagar` · pago contra factura.
- `POST /api/admin/proveedores-dedup-nombre` · dedup por variante de mayúsculas
  (la fusión por nombre se bloquea si keeper.lower()==merge_from.lower()).
- `GET /api/compras/feed-necesidades` · MP + envases bajo mínimo (unificado).

**Invariantes nuevas:**
- **INV-6 · factura = padre de pagos.** Un pago vía factura va a `pagos_oc` con
  `factura_proveedor_id` set y `numero_factura_proveedor=''` (el índice UNIQUE parcial
  `idx_pagos_oc_factura_unique` ignora ''→permite pagos parciales). `fp_pagar` recalcula
  el estado de la factura (SUM pagos vs total) Y el de la OC ligada (mismo CAS que
  pagar_oc, Pagada/Parcial · no toca OCs no-pagables).
- **INV-7 · stock de MP en feeds excluye lotes no disponibles.** Cualquier cálculo de
  stock de MP para necesidades/compra DEBE excluir estado_lote en
  (CUARENTENA, CUARENTENA_EXTENDIDA, VENCIDO, RECHAZADO, AGOTADO) — igual que
  `_get_mp_stock`. (feed-necesidades violaba esto → falso negativo de compra · INVIMA.)
- **INV-8 · dedup propaga = fusión propaga.** `admin_proveedores_dedup_nombre` y
  `admin_proveedores_fusionar` comparten la MISMA lista `propagar` de tablas/columnas
  (incluye `pagos_influencers`). Si una agrega una tabla, la otra también.

**Perf (audit escalabilidad):** N+1 de Shopify en preparar/mínimos envases resuelto
con `_ventas_sku_180d(c)` memoizado por request (flask.g). Blobs PDF fuera de la tabla
transaccional (1:1). NO materializar stock con cache persistente (drift · prohibido).

**CSRF:** `PUT /api/maestro-mps/<cod>/proveedor` ahora manda X-CSRF-Token desde el front
(estaba roto en prod · /api/maestro-mps/ está en _admin_paths).

### 2026-07-25 · Auditoría CERO-ERROR · 4 fugas de plata + Habeas Data

- **INV-9 · El espejo a `flujo_egresos` se ancla por `referencia`, NO por `numero_oc`**
  (esa columna no existe en la tabla). `revertir_pago_oc` borraba con `WHERE numero_oc=?`
  → OperationalError tragado por el `except` → el egreso NUNCA se borraba: la plata seguía
  contada en P&L/cash-flow y al re-pagar quedaba duplicada. Ahora borra por
  `referencia + fuente='compras'` y UNA sola fila (la más reciente).
- **INV-10 · La recepción decide MP vs ENVASE por ÍTEM, no por la categoría de la OC.**
  El front creaba las OC de la bandeja de Planta con `categoria:'MP'` fijo, así que los
  envases entraban al kardex de MATERIA PRIMA: no sumaban en `SUM(movimientos_mee)` (se
  volvían a pedir) y se saltaban la CUARENTENA (mig 301). Criterio: si el código está en
  `maestro_mee` y NO en `maestro_mps`, es envase. Cubre las OC mixtas, que son legítimas.
- **INV-11 · Aplicar saldo a favor ES pagar**: bloquea los mismos estados que `pagar_oc`
  (Cancelada/Rechazada/Borrador/Revisada). Antes solo frenaba cancelada/anulada, así que con
  crédito se dejaba en 'Pagada' una OC en Borrador, eludiendo la autorización gerencial.
- **INV-12 · `maestro_mps.precio_referencia` está en $/kg**: todo writer que venga de una OC
  (donde `precio_unitario` es $/g) multiplica por 1000. `items-precios` lo omitía y dejaba el
  precio 1000× más barato para la siguiente OC. Igual `precios_mp_historico.precio_kg`.
- **Habeas Data (Ley 1581)**: `por-pagar` y `ocs-consolidado-excel` devolvían banco, tipo y
  número de cuenta y NIT en claro a cualquier usuario logueado (`compras_user` = "inició
  sesión", NO un rol). Enmascarados a `***` salvo admin + contadora, como los hermanos.

## 💵 El libro de facturas de proveedor exige rol de Compras (26-jul)

`pagar_oc` pide rol desde el 21-may (`_require_authorize_oc`, con SoD que bloquea a la contadora
para AUTORIZAR). Sus hermanos del libro de facturas —`fp_crear`, `fp_editar` y **`fp_pagar`**—
sólo exigían estar logueado: **cualquier usuario del sistema** (planta, marketing, calidad, RRHH)
podía crear una factura de proveedor o registrar un pago contra ella. Y `fp_pagar` recalcula el
estado de la OC, así que mueve el mismo dinero.

Es el patrón M45: cuando se endurece un guard de dinero, uno de los pagadores hermanos se queda
sin endurecer. (Ya había pasado con el over-payment race AR/AP el 16-jun.)

**Gate = `_require_compras_write()`** (COMPRAS_ACCESS | ADMIN → Catalina, Mayra, Alejandro,
Sebastián). La contadora **sí** entra: REGISTRAR un pago es su trabajo; lo que sigue vedado para
ella es AUTORIZAR una OC, que tiene su propio gate más estricto. Test:
`tests/test_facturas_proveedor_rol.py` (verifica las dos direcciones: quien no tiene rol recibe
403 y quien hace el trabajo sigue pudiendo).

---

### INV-12 · Una factura de proveedor con pagos NO se anula (28-jul)

`fp_editar` con `{anular:true}` leía el estado de la factura y **no lo usaba para nada**:
`SELECT estado` y a continuación `UPDATE ... SET estado='anulada' WHERE id=?`. Con eso se podía
anular una factura **ya pagada**, y las filas de `pagos_oc` quedaban apuntando a un registro
anulado: el libro de cuentas por pagar decía "anulada" mientras la plata ya había salido del
banco.

Es el patrón M45 otra vez, y en el mismo par de hermanos que INV-9: **`fp_pagar` sí rechaza pagar
una factura anulada desde el 31-may**. Cuando se endurece un guard de dinero, uno de los dos
hermanos queda sin endurecer, y la asimetría es la firma.

**Reglas:**
1. Anular exige que la factura **no tenga ningún pago registrado**
   (`SUM(pagos_oc.monto WHERE factura_proveedor_id=?) = 0`). Con pagos → **409
   `FACTURA_CON_PAGOS`**, con el monto en el mensaje. Para anularla hay que revertir el pago
   primero, que es el orden correcto: la plata se devuelve antes que el papel.
2. La anulación va con **CAS** (`WHERE id=? AND estado != 'anulada'` + `rowcount`): dos
   anulaciones concurrentes no pueden pasar las dos (409 `YA_ANULADA`).
3. El `audit_log` guarda **de qué estado venía** (`antes`), no sólo que se anuló.

Test: `tests/test_factura_proveedor_anular.py` (en el gate · incluye el caso legítimo —una
factura mal cargada SÍ se anula— para que el arreglo no mate la función).

### INV-13 · El `except` de la recepción no es una sonda de esquema (28-jul)

El `UPDATE` que cierra una recepción escribe estado, fecha, observaciones, **discrepancias**,
quién recibió y el flag de parcial. Estaba envuelto en un `except Exception` que reintentaba un
UPDATE mínimo, asumiendo que cualquier fallo era "faltan las columnas de la migración de mayo".

Eso es M69: con esa forma, un fallo **real** (constraint, trigger, transacción abortada en PG) se
disfraza de drift de esquema y la recepción se guarda **perdiendo las discrepancias y el
receptor** — justo los datos con los que se le reclama al proveedor.

**Regla:** el fallback al UPDATE mínimo aplica **sólo si el error es de columna**
(`'column' | 'no such' | 'no existe la columna'`), y queda un `log.warning`. Cualquier otro error
se **re-lanza**. Para saber si una columna existe se detecta una vez y se ramifica; el `except` de
una mutación nunca es el detector.

---

### INV-14 · La OC guarda la UNIDAD de cada ítem, no gramos por defecto (28-jul)

Catalina: *"le está colocando gramos a cosas que son cantidades"*. En la bandeja, un `Servicio
de Calibración por laboratorio acreditado` aparecía como **"1 g"** y la serigrafía de 810
envases como **"810 g"**.

La unidad **sí se capturaba**: `solicitudes_compra_items.unidad` existe desde el principio.
Pero `ordenes_compra_items` sólo tenía `cantidad_g`, así que **el dato se perdía en el INSERT
que crea la OC desde las solicitudes** — y la pantalla, sin nada que mostrar, concatenaba `' g'`
a toda cantidad.

**Reglas:**
1. `ordenes_compra_items.unidad` (mig 390) se llena **desde la solicitud** al crear la OC. Un
   INSERT que traspasa una fila de una tabla a otra copia todas las columnas que importan.
2. La vista usa la unidad real. **Cuando no se sabe, no se inventa ninguna**: se muestra el
   número solo. Un número con la unidad equivocada es peor que uno sin unidad, porque se lee
   como si fuera cierto (M5).
3. Sólo **materia prima y empaque** se miden en gramos. El backfill de la mig 390 deduce el
   resto por la `categoria` de la OC.
4. El déficit de MP (Centro de Programación) **sí** va en gramos: ahí la unidad es correcta y no
   se toca.

Test: `tests/test_oc_unidad_real.py` (en el gate · incluye el guard de que nadie vuelva a
concatenar `' g'` a la cantidad de la bandeja).


## 🔎 INV-12 · El rastro de una orden · "se me perdió" se contesta con hechos (31-jul)

Catalina: *"al hacer órdenes de compra se le perdió"*. Esa pregunta sólo se podía contestar con
una hipótesis: más de 30 acciones distintas tocan una OC, todas quedan en `audit_log`, y nadie
tenía cómo leerlo.

`GET /api/compras/rastro?q=OC-2026-0231` (lectura · cualquier autenticado) devuelve el veredicto
en una frase + la línea de tiempo completa:

- **existe** → estado, proveedor, cuántos ítems y cuánto vale;
- **se fusionó** → con cuál orden, cuándo y quién (y aclara que los ítems se movieron, no se
  perdieron);
- **la eliminaron** → quién y cuándo;
- **una orden que existe pero SIN ítems** se declara: guardar una edición con la lista vacía los
  borra todos y la orden queda en cero sin que nadie lo note.

**Las TRES formas legítimas en que una OC desaparece** (ninguna destruye datos, pero las tres se
viven como "se perdió"):
1. `cambiar-proveedor` **FUSIONA** si el nuevo proveedor ya tiene una OC editable de la misma
   categoría: mueve ítems + re-vincula SOLs y **borra esta OC** (decisión de Sebastián 14-jul,
   "siempre una orden por proveedor"). La UI lo avisa en un alert al final.
2. `editar_oc` con `items` en el body **borra e re-inserta**: una lista vacía deja la orden sin
   ítems.
3. `ELIMINAR_OC` borra la orden y **revierte sus SOLs a pendientes** (no se pierden).

Tests: `tests/test_rastro_oc.py` (en el gate). ⚠ `audit_log` es **append-only por trigger**
(Part 11 §11.10(e)): un test que intente limpiarlo falla — cada caso usa su propio número.


## 🛡️ INV-13 · Una orden no se vacía ni desaparece sin que alguien lo pida (31-jul)

Del caso de Catalina ("se me perdió la orden 0299") salieron dos guards. Ninguno cambia lo que el
sistema hace bien; los dos evitan que lo haga **sin que nadie lo haya pedido**:

- **`editar_oc` con `items: []` ya no borra los ítems que hay** → 409 `ITEMS_VACIOS`. El bloque
  borra-y-re-inserta, así que una lista vacía (error de JS, carga a medias, doble submit) dejaba
  la orden existiendo con cero ítems y en cero pesos, y nadie lo notaba. **Vaciar una orden nunca
  es el objetivo de "guardar cambios"**: si de verdad hay que dejarla sin ítems, se elimina.
- **`cambiar-proveedor` PREGUNTA antes de fusionar** → 409 `FUSION_CONFIRMAR` con el número de la
  orden destino y cuántos ítems se mueven; el front reenvía con `confirmar_fusion: true`. La
  fusión sigue siendo la regla (Sebastián 14-jul: una orden por proveedor), pero **quien pidió
  "cambiá el proveedor" no pidió "borrá esta orden"**: son dos actos y el segundo se confirma.
  Antes se enteraba después, en un alert que se cierra sin leer.

Tests: `tests/test_rastro_oc.py` (en el gate · incluye los dientes del otro lado: la edición
normal con ítems sigue funcionando y la fusión confirmada sí mueve todo).

## 📦 INV-14 · Recepción de OTROS ACTIVOS (31-jul)

*"Todo lo que llegue se debe recepcionar"*. Tenían puerta la MP, los envases, los consumibles y
los equipos; un computador, una silla o un archivador **no son equipos de planta** y sólo entraban
al libro por el Excel — o sea que el valor de la empresa quedaba viejo hasta la próxima carga.

`POST /api/recepcion/activos` (misma puerta que equipos: `COMPRAS_ACCESS ∪ {luz} ∪ ADMIN`) crea la
fila en `activos` con `origen='recepcion'`, código siguiendo la convención del Excel maestro
(`ANM-LT-003`, `ESP-SIL-012` · correlativo extraído en Python, nunca `CAST(SUBSTR)` · M45). **No
lleva calificación** (una silla no se califica) y suma al valor en libros desde que se registra.
Pestaña "Otros activos" dentro de `/recepcion` (M120).

## 💰 INV-12 · TODO lo AUTORIZADO entra a Por Pagar (3-ago)

Sebastián, corrigiendo la regla del negocio: *"es que nosotros pagamos para que llegue · todo
lo que se autorice debe aparecer allí en Por Pagar para ella hacerlo · algunas cosas llegan sin
pagar, otras sí"*.

En ÁNIMUS se paga **por anticipado** para que el proveedor despache. Así que el trabajo que
sigue a autorizar es **pagar**, no esperar. La premisa contraria -que la mercancía se paga
contra entrega- dejaba a la OC autorizada esperando en Recepción, donde todavía no hay nada que
hacer porque no ha llegado.

**Invariante de `GET /api/compras/por-pagar`:**

| Entra | Estado | Flag |
|---|---|---|
| Mercancía ya recibida | `Recibida` / `Parcial` | `pago_directo: false` |
| Todo lo autorizado | `Aprobada` / `Autorizada` | `pago_directo` según categoría |

- Antes exigía **además** categoría de `CATEGORIAS_PAGO_DIRECTO`, así que una OC de MERCANCÍA
  autorizada no aparecía en **ninguna** lista accionable (Por Pagar la excluía por categoría y
  la lista de OCs sólo mostraba Borrador/Revisada). Catalina: *"cuando da autorizar desaparecen
  y no salen en Por Pagar"*.
- **`Influencer/Marketing Digital` queda EXCLUIDO** en los dos lados: tiene su propio flujo en
  Marketing (se paga sin entrar a Compras) y son 82 OCs · incluirlas enterraría el trabajo real.
- El campo `tipo` distingue **"Pago directo (servicio)"** de **"Autorizada · pagar para que
  despachen"**: en la segunda todavía falta que la mercancía llegue.

**El badge cuenta EXACTAMENTE lo mismo que la lista deja trabajar (M5).** Antes el badge decía
**52** y la lista traía **16**, porque el badge ya contaba todas las autorizadas y la lista
exigía el filtro de categoría: el número prometía un trabajo que la pantalla no dejaba hacer.

⚠ Verificado antes de construirlo: `pagar_oc` **acepta** una OC `Autorizada` (sólo bloquea
`Borrador`/`Revisada`/`Cancelada`/`Rechazada`). Si el gate de pago la frenara, esta lista sería
una pantalla que no se puede usar (M121).

**Flujo completo:** autorizar → **Por Pagar** (se paga) → llega → **Recepción** (INV-21 de
`CONTRACT_inventario.md`: el desplegable de ingreso incluye `Autorizada` y `Pagada`).

Tests: `tests/test_oc_autorizada_visible.py` · `tests/test_rastro_oc.py`.
