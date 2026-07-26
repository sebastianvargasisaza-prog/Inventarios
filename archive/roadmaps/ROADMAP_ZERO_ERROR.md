# ROADMAP zero-error · auditoría sistemática 2-may-2026

> Auditoría zero-error de los 30 blueprints (~64k líneas) ejecutada en 6 agents paralelos.
> Este documento lista los findings priorizados que NO se aplicaron en esta sesión.

## ✅ Fixes APLICADOS en sesión 2-may-2026

### Aseguramiento (commits 6e4ae46, fd48da1)
- Migración 91: `audit_log.antes` + `audit_log.despues` columnas + 3 indexes
- Migración 92: 5 indexes para `mis-tareas` (detectado_por, solicitado_por, recibido_por, iniciado_por)
- Helper `_audit_log()` centralizado · removido los 8 `try: except: pass` que silenciaban audit fail
- Audit log agregado a 12 endpoints regulatorios faltantes (capacitaciones_firmar, cambio/recall_notificar_invima, recall_clasificar, etc.)
- Helper `_intentar_insert_con_retry()` race-safe para 4 generadores de código secuenciales
- `cambio_implementar` BLOQUEA si requiere_invima=1 sin notificar (Resolución 2214/2021)
- HMAC fallback `'fallback'` REMOVIDO · 503 si SECRET_KEY falta
- KPIs en 4 listados ya no basados en LIMIT 500 (query COUNT separada)
- Sentry `before_send` filtra 4xx + redacta PII
- `queja_triaje` atómica: rollback si crear desv falla
- 3 `SELECT *` → columnas explícitas
- 4 funciones JS `_post*Accion` consolidadas en `_postWorkflowAccion()`
- 10 modales con `role="dialog"` + `aria-modal` + `aria-label`

### Core/Auth (este commit)
- `/logout` ahora hace `session.clear()` (antes solo pop compras_user)
- 5xx errorhandler ya NO expone traceback al cliente (ni siquiera a admins)
- bug case `'Cuarentena'` → `'CUARENTENA'` en recibir_oc (FEFO ya no incluye cuarentena en disponible)
- `recibir_oc` UPDATE con `+=` en cantidad_recibida_g (recepciones parciales ya acumulan)
- `pagar_oc` valida over-payment + estado OC válido
- `clientes.py` 18 endpoints API ahora requieren `CLIENTES_ACCESS` (PII protegida)
- `rrhh.py` `before_request` gate para todos los endpoints API (PII protegida · Habeas Data)
- Comentario crítico en `prog_sync_stock_shopify` advirtiendo On hand vs Available

---

## 🚨 PENDIENTE · CRÍTICAS regulatorias

### Compliance INVIMA · audit log faltante
- [ ] **`compras.py pagar_oc`** sin audit_log (línea 2393)
- [ ] **`compras.py autorizar_oc`** sin audit_log (línea 2366)
- [ ] **`contabilidad.py cont_factura_anular`** sin audit_log (línea 508)
- [ ] **`contabilidad.py cont_factura_pago`** sin audit_log (línea 438)
- [ ] **`programacion.py prog_completar_evento`** dispensación sin audit_log (línea 4036)
- [ ] **`programacion.py _auto_asignar_operarios`** sin audit_log (línea 8415)
- [ ] **`calidad.py POST agua/CoA/NCs/CAPA/auditorías/specs/estabilidades/micro`** sin audit_log
- [ ] **`compliance.py` TODO** sin audit_log (cero inserts en 400 líneas)
- [ ] Centralizar helper `_audit_log()` ya creado en aseguramiento.py · moverlo a `database.py` para uso global

### MRP / lógica de negocio
- [ ] **`prog_sync_stock_shopify`**: implementar segunda API call a `/inventory_levels.json` con `inventory_item_ids` para obtener `available` real (en lugar de `inventory_quantity` que es On hand). Memoria explícita del usuario.
- [ ] **Hermanos SKUs unificación**: agregar job semanal automático que detecte hermanos no-unificados y notifique (hoy es manual `/api/planta/unificar-hermanos-skus`)
- [ ] **`prog_completar_evento` pre-check de stock disponible** antes de descontar (puede dejar stock negativo silenciosamente)
- [ ] **Margen 25/20 distinción**: `MARGEN_DIAS_ACTIVO` no diferencia entre ideal=25 y mínimo=20; mezcla ambos

### Race conditions (medias críticas)
- [ ] **OC/SOL/factura código secuencial** en compras.py:626/1413/2189/2382 · usar el helper `_intentar_insert_con_retry()` ya existente en aseguramiento
- [ ] **OOS-NNN, DESV-NNN, HLZ-XXX-NNN** en calidad.py:1074 + compliance.py:143/257 · mismo helper
- [ ] **`pagar_oc` race**: dos pagos paralelos sin numero_factura pueden ambos pasar over-payment check si llegan antes del INSERT
- [ ] **`registrar_recepcion` UPDATE estado=`Cuarentena`** vs FEFO con UPPER(estado) (ya fixed en compras.py, falta verificar inventario.py)

### Money handling FLOAT vs Decimal
- [ ] Migrar columnas críticas (`monto`, `valor_total`, `total`, `subtotal`) a INTEGER cents o usar `Decimal` en cálculos
- [ ] `pagos_oc.monto`, `ordenes_compra.valor_total`, `pedidos.valor_total`, `facturas_pagos.monto` actualmente FLOAT
- [ ] `marketing.py:1759` Shopify orders sin conversión USD→COP explícita

---

## 🔴 PENDIENTE · ALTAS

### Seguridad / RBAC
- [ ] **`maquila.py` 16 de 17 endpoints sin auth check** · usar before_request gate igual que rrhh
- [ ] **`compras.py recibir_oc/revisar_oc/editar_oc/agregar_item_oc`** solo verifican session, no rol
- [ ] **`compras.py pagar_oc` no respeta `LIMITES_APROBACION_OC`** (catalina puede pagar OCs grandes)
- [ ] **`gerencia.py /api/admin/cleanup-test-data` LIKE '%test%'** frágil → puede borrar datos reales con palabra "test"
- [ ] **CSRF strict-deny si no Origin/Referer** (auth.py:252) · hoy se permite y solo se loguea
- [ ] **CSRF token rotación tras login MFA** (mfa.py:417 no borra pre-auth state)
- [ ] **`mfa_setup` TOCTOU** (mfa.py:130) · permite hijack del enrollment si víctima tiene MFA disabled
- [ ] **`mfa_admin_disable` requiere admin pero no reauth** (password+TOTP)
- [ ] **`/api/admin/inventario-reset-aplicar` sin MFA step** adicional para acción destructiva
- [ ] **Reducir cookie lifetime de 30d a 8h** (alinea con `check_session_timeout` 8h)

### CSRF en mutaciones
- [ ] **9 módulos sin validar X-CSRF-Token** en POST/PATCH/DELETE: rrhh, admin, chat, comunicacion, bienestar, marketing, comercial, financiero, gerencia. La infra ya existe en auth.py:32-43 pero nadie la enforce.

### XSS en emails HTML
- [ ] **`chat.py:812`** `<i>{contenido[:500]}</i>` sin `markupsafe.escape`
- [ ] **`comunicacion.py:75-83`** `td["titulo"]`, `td.get("descripcion","")` directos en HTML email
- [ ] **`hub.py` + core.py `.replace('{usuario}', usuario.capitalize())`** sin escape (defense-in-depth)

### Datos sensibles
- [ ] **Bienestar: datos médicos en plaintext** (descripcion, adjunto_url de tipo `salud`/`cita_medica`/`enfermedad`/`licencia`) · encriptar AES-256
- [ ] **`JEFES_AREA` con 5 personas** leyendo notif médicas sin audit log · restringir a RRHH+Admin para datos sensibles
- [ ] **`rrhh.py:537 _bank_data`** cuentas bancarias hardcodeadas en código fuente · mover a env vars encriptadas
- [ ] **Audit log de acceso a PII** · tabla `pii_access_log(usuario, endpoint, registro_id, ts, ip)` para SELECT en empleados/nómina/clientes/quejas

### Trazabilidad lote → cliente (recall imposible)
- [ ] **`/api/despachos`**: persistir `lote_pt` real (que efectivamente descontó FEFO) en `despachos_items`, NO el que mandó el frontend
- [ ] **Shopify DTC sin lote**: `marketing.py:1696-1771` `mkt_sync` no graba lote en orders sincronizadas → recall DTC imposible. Agregar columna `lote_asignado` y FIFO contra stock_pt al sync
- [ ] **Webhook EOS público sin firma HMAC**: `comercial.py:181` permite leads infinitos sin auth · agregar HMAC + IP allowlist + rate-limit

### Performance
- [ ] **N+1 en `cont_facturas_list`** (200 facturas → 201 queries) · convertir a LEFT JOIN agregado
- [ ] **N+1 en `handle_solicitudes_compra` GET fallback** · loop sobre filas con SELECT por SOL
- [ ] **N+1 en `clientes.ficha360`** (4 queries secuenciales) · combinable en JOIN
- [ ] **N+1 en marketing dashboard SKUs** (líneas 2218-2247)
- [ ] **`date(columna)` invalida indexes** en cron jobs y dashboard (auto_plan_jobs.py 1538 + 5 más sitios)
- [ ] **HTTP retries exponenciales** en Shopify/Meta/GHL ante 429/5xx (hoy fail inmediato)

### Bugs específicos
- [ ] **`registrar_recepcion` (inventario.py:2033)** acepta cualquier `fecha_vencimiento` sin tope (1900 / 2099 / etc.)
- [ ] **`registrar_recepcion`** no valida que `numero_oc` exista realmente
- [ ] **`eliminar_lote` (inventario.py:1719)** permite borrar lote con stock positivo sin doble confirmación
- [ ] **`cuarentena` reservas colgadas**: sin auto-rechazo a los N días si nadie aprueba
- [ ] **`prog_crear_evento`** acepta fecha pasada sin advertir, no valida producto exista, no detecta duplicados producto+fecha+lotes

---

## 🟡 PENDIENTE · MEDIAS

### Calidad/Compliance (mismos bugs que Aseguramiento tenía)
- [ ] **RBAC simétrico**: agregar `CALIDAD_USERS|ADMIN_USERS` a TODOS los POST de calidad.py (NC, CAPA, auditorías, CoA, specs, agua, estabilidades, micro) y compliance.py (cronograma, capa, hallazgos)
- [ ] **KPIs basados en LIMIT en bandeja calidad** (LIMIT 100/50/30) · misma corrección que aseguramiento
- [ ] **Validación rango agua**: pH 0-14, conductividad 0-50, micro≥0, TOC≥0 · rechazar valores físicamente imposibles
- [ ] **Bloqueo equipos vencidos**: validación en CoA POST y producción que rechace `equipo_id` con calibración vencida
- [ ] **Notif previa vencimiento calibración**: cron T-30/T-7/T-0 con push_notif_multi
- [ ] **Decisión arquitectónica CAPA**: consolidar `compliance.capa_desviaciones` + `calidad.capa_acciones` + `aseguramiento.desviaciones` en un solo modelo o documentar claramente qué va dónde

### Tests
- [ ] **Cron jobs sin tests** (4 jobs ASG: desv_plazos, cambios_plazos, quejas_plazos, recalls_plazos)
- [ ] **RBAC negative tests** (~10 endpoints con role check sin test que verifique 403)
- [ ] **PII access tests** para rrhh, clientes, bienestar
- [ ] **Race condition tests** (bajo threading) para validar generadores de código
- [ ] **Idempotencia migrations** (correr 2 veces y verificar no-op)
- [ ] **Audit log assertions** después de cada cierre regulatorio

### Performance · cache
- [ ] **Cache-Control en JSON API** dashboard + mis-tareas (ahorra 9-10 queries por F5)
- [ ] **ETag basado en MAX(actualizado_en)** en endpoints de listado para 304 Not Modified

### A11y
- [ ] **`role="tab"` + tabindex + aria-selected** en sistema de tabs
- [ ] **`for=` en 75 labels** del frontend de aseguramiento
- [ ] **`aria-hidden="true"`** en iconos emoji decorativos

### Frontend
- [ ] **Disable buttons during fetch** para evitar doble-click en endpoints regulatorios (recalls, cierres)
- [ ] **Toast notifications no-bloqueantes** en lugar de ~30 `alert()`
- [ ] **Loading spinners** en pestañas (hoy solo "Cargando...")
- [ ] **Cache 30s en goTab()** para reducir 70% de fetches al navegar
- [ ] **Reemplazar `prompt()`** para SGD PDF/conflictos con modales propios
- [ ] **Mostrar request_id en errores 500** (ya viene en X-Request-Id header, no se aprovecha)

### Infra
- [ ] **Backups off-site**: subir gz a S3/B2/GCS tras `do_backup` (hoy solo local en Render)
- [ ] **HSTS preload directive** + register en hstspreload.org
- [ ] **`SECRET_KEY` ausente debería refuse-to-boot** en producción
- [ ] **Email queue persistente** para comprobantes (hoy thread daemon que se pierde en deploy)

---

## 🟢 PENDIENTE · BAJAS

- [ ] Mover endpoints "destructivos" cleanup-test-data, influencers-reset-pendientes a `requires_admin + audit_log`
- [ ] Tokens unsubscribe en emails (CAN-SPAM/GDPR)
- [ ] Imports muertos: `rrhh.py:5` import hmac/time sin uso
- [ ] `maquila.py` imports masivos legacy de templates de otros módulos
- [ ] Soft-delete con protección: verificar pedidos pendientes antes de desactivar
- [ ] Documentar SQL rollback en comentario de migraciones (forward-only ahora)

---

## 🎯 PRIORIZACIÓN sugerida próxima sesión

**Día 1 — Compliance regulatorio (4-6h)**
1. Mover `_audit_log()` helper a `database.py` para uso global
2. Agregar audit_log a `pagar_oc`, `autorizar_oc`, `cont_factura_anular/pago`
3. Agregar audit_log a `prog_completar_evento` + `_auto_asignar_operarios`
4. Agregar audit_log a 5 POSTs críticos de calidad.py
5. Migrar money de FLOAT a INTEGER cents en `pagos_oc.monto`, `ordenes_compra.valor_total`, `pedidos.valor_total`
6. Race-safe códigos secuenciales en compras + calidad usando helper existente

**Día 2 — RBAC + CSRF (3-4h)**
7. `maquila.py` before_request gate
8. CSRF strict-deny si no Origin/Referer
9. RBAC en `compras.py recibir/revisar/editar OC`
10. `pagar_oc` respeta `LIMITES_APROBACION_OC`

**Día 3 — MRP + recall (3-4h)**
11. Shopify Available real con segunda API call
12. Trazabilidad lote→cliente en despachos + Shopify DTC
13. Webhook EOS HMAC + rate limit
14. Retries exponenciales en integraciones externas

**Día 4 — Calidad/Compliance (4-5h)**
15. Calidad: RBAC simétrico en POSTs + KPIs sin LIMIT + validación rango agua
16. Compliance: helper audit_log + race-safe códigos
17. Bloqueo equipos vencidos + notif T-30/T-7/T-0
18. Decisión arquitectónica CAPA

**Día 5 — Polish + tests (3-4h)**
19. Tests cron jobs + RBAC negative + race conditions
20. Frontend a11y completo + toasts + loading states
21. Backups off-site
22. Documentación

---

## 📝 NOTAS estratégicas

- **Aseguramiento es el módulo más completo zero-error** después de la sesión 2-may-2026.
- **Calidad y Compliance siguen pre-audit**: tienen los MISMOS bugs que aseguramiento tenía antes (audit_log mismatch, race en código secuencial, KPIs LIMIT, POSTs sin RBAC).
- **Compras tiene gaps regulatorios serios** (over-payment ya fixed, audit_log y RBAC pendientes).
- **Trazabilidad lote→cliente en Shopify DTC es BLOQUEANTE para recall** real.
- **PII de RRHH ya protegida** post-fix (Habeas Data Ley 1581/2012 cumple ahora).
- **Helpers reutilizables** ya existen en aseguramiento.py: `_audit_log()`, `_intentar_insert_con_retry()`, `_siguiente_codigo_secuencial()`. Mover a `database.py` o crear `api/helpers/regulatorio.py`.

---

Generado por `/zero-error-enterprise` audit · 6 agents paralelos cubriendo todos los blueprints.
