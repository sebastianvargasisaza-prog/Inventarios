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
