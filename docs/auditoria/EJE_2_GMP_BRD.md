# Eje 2 · Readiness regulatorio GMP / Batch Record digital

**Veredicto**: 🟡 **BASE PARCIAL** — hay infraestructura sustancial (audit_log centralizado, versionado de fórmulas con snapshot al ejecutar, control de cambios formal, desviaciones con CAPA, MFA admins, backups automáticos) pero faltan piezas no-negociables Part 11: audit trail append-only enforced, e-signature con re-auth+meaning, MBR/EBR como entidades de primera clase. Y **cero** pack CSV (URS/IQ/OQ/PQ).

**TL;DR (5 líneas honestas)**
1. EOS hoy es un ERP de planta con quality bolt-ons, no un BRD nativo. Tiene ~90 % de los datos brutos que un EBR necesita (lote, fórmula snapshot, inicio/fin real, operario por área, IPCs micro/CoA, equipos), pero ningún endpoint los compone en un legajo firmable y exportable.
2. Audit trail existe pero **no está blindado**: `audit_log` no tiene trigger SQL que bloquee UPDATE/DELETE, y todo INSERT está en la misma transacción que la operación auditada (un rollback aplicación borra evidencia).
3. Firma electrónica embrionaria: solo capacitaciones SOP usan HMAC vinculado al record (`api/blueprints/aseguramiento.py:823`), **sin re-autenticación**, sin meaning of signature, sin password challenge. Lejos de Part 11 §11.200.
4. **No existe MBR como entidad versionada vinculable a un lote**. La fórmula viaja como JSON snapshot dentro de `producciones`, pero no hay procedimiento paso-a-paso, ni ejecución secuencial, ni IPCs con specs aprobadas, ni equipment-cleaning log por equipo (solo por sala).
5. En 3-6 meses **es factible** llegar a un MVP de BRD vendible internamente y a labs pequeños (HHA, Espagiria), pero **NO** a un cliente farmacéutico GMP estricto sin antes adjuntar pack CSV — eso es trabajo paralelo de documentación, no de código.

## Checklist regulatorio (estado actual)

| Requisito | Estado | Evidencia | Esfuerzo |
|---|---|---|---|
| Audit trail append-only enforced (trigger SQL) | 🔴 | `api/database.py:5322-5326` define la tabla; los 22 triggers en `database.py` (líneas 325-482, 4225-4283) **no incluyen** uno sobre audit_log. Único DELETE encontrado: `tests/test_helpers.py:201` (test fixture). | 1 día |
| Audit trail captura usuario+ts+acción+antes+después+IP | 🟢 | `api/audit_helpers.py:31-86`. Migración 91 (`api/database.py:3720-3738`) agregó columnas antes/despues. | 0 |
| Audit trail captura "razón del cambio" | 🟡 | `motivo` se acepta en endpoints destructivos (`api/blueprints/inventario.py:2029,2156,2282`) pero NO se exige en `audit_helpers.audit_log()`. | 3 días |
| Audit trail timestamp UTC desde fuente confiable | 🔴 | 465 usos de `datetime('now')` (local Bogotá) vs ~30 usos de `datetime('now','utc')`. El propio audit_log usa local: `audit_helpers.py:62`. | 5-10 días |
| No hay UPDATE/DELETE sobre audit_log en producción | 🟢 | Grep solo retorna `tests/test_helpers.py:201`. | 0 |
| Audit log en transacción separada (no rollbackeable) | 🔴 | `audit_helpers.py:50-86`: mismo cursor que la operación. Defeats §11.10(e). | 2-3 días |
| E-signatures: meaning of signature | 🔴 | Solo `aseguramiento.py:823` firma (capacitaciones). Liberación de lote (`inventario.py:3104-3126`) no firma. | 5 días |
| E-signatures: linked to record (immutable) | 🟡 | `sgd_capacitaciones.firma_hash` (`database.py:4097`) usa HMAC-SHA256+SECRET_KEY. Bueno pero el campo puede UPDATE-arse. | 2 días |
| E-signatures: re-autenticación al firmar | 🔴 | `capacitaciones_firmar` (`aseguramiento.py:797-842`) usa `session.get('compras_user')` sin pwd ni TOTP re-prompt. | 5-7 días |
| MFA disponible y reutilizable | 🟢 | `api/blueprints/mfa.py` completo (TOTP RFC 6238 + backup code + admin-disable). | 0 |
| Versionado de fórmulas | 🟢 | `formulas_versiones` (migración 36, `database.py:2062-2071`) + `tecnica_versiones` (`tecnica.py:100`). | 0 |
| Versionado SGD | 🟢 | `sgd_documentos` + `sgd_versiones` (`database.py:4041-4086`). | 0 |
| Snapshot fórmula al ejecutar | 🟢 | Migración 99: `producciones.formula_snapshot_json` (`database.py:398-406`). | 0 |
| Records históricos no modificables post-aprobación | 🔴 | Ningún trigger anti-UPDATE con `WHEN OLD.estado IN (...)`. | 5 días |
| Backups automáticos | 🟢 | `api/backup.py` gzip + multi-worker lock + offsite opcional. Interval reducido a 6h tras incidente 12-may (`backup.py:38-41`). | 0 |
| Backups recuperables y auditables | 🟡 | Restauración manual documentada (`docs/OPERACIONES.md:51-59`). Sin test recurrente, sin audit de descargas. | 3 días |
| Retención ≥5 años (INVIMA) | 🔴 | `BACKUP_RETENTION_DAYS=14` (`backup.py:37`). Sin política long-term. | 5 días |
| RTO/RPO documentado | 🔴 | Grep RTO/RPO vacío en `RUNBOOK.md` y `docs/`. | 2 días |
| Change control aplicación | 🟢 | `control_cambios` + eventos (`database.py:3909-3974`). Endpoints en `aseguramiento.py:1238-1500`. | 0 |
| Change control fórmulas | 🟢 | `cambios_control_formula` (`tecnica.py:75-95`). | 0 |
| Change control de DEPLOYS | 🔴 | No hay tabla `deploys` ni vínculo commit↔change_control aprobado. | 5 días |
| CAPA/Desviaciones workflow | 🟢 | `desviaciones` + `desviaciones_eventos` (`database.py:3975-4033`) + endpoints `aseguramiento.py:868-1200`. | 0 |
| Desviación vinculable a lote | 🟡 | `desviaciones.lotes_afectados` es TEXT libre (`database.py:3988`), no FK. | 2 días |
| Especificaciones MP + farmacopea | 🟢 | `especificaciones_mp` (`database.py:2303-2317`). | 0 |
| CoA por lote vs spec | 🟢 | `coa_resultados` (`database.py:2321-2342`). | 0 |
| In-Process Controls (IPCs) | 🔴 | No existe `ipc_specs` ni `ipc_resultados`. Solo micro y CoA. | 7-10 días |
| Equipment cleaning log por equipo | 🔴 | Solo por sala (`area_eventos` tipos `inicio_limpieza/fin_limpieza`, `database.py:2914-2933`) y `limpieza_profunda_calendario`. Sin log por equipo individual. | 7 días |
| CSV: URS/IQ/OQ/PQ | 🔴 | Glob vacío. | 30-45 días (docs) |
| CSV: Risk Assessment | 🔴 | No existe. | 10 días |
| CSV: trazabilidad URS↔tests | 🟡 | 50 golden paths (`tests/test_golden_paths.py`) sin matriz formal. | 7 días |
| Time sync NTP | 🟡 | Render maneja NTP host; gap es BD en local time. | Cubierto por UTC |
| Password hashing PBKDF2 | 🟢 | `werkzeug.security` + plaintext rechazado (`SECURITY.md:12`, `CLAUDE.md:73`). | 0 |
| Session security HTTPOnly+Secure+SameSite | 🟢 | `SECURITY.md:11`. | 0 |
| MFA enforced en admins | 🟢 | Commit `09e892b`. | 0 |
| Identity uniqueness (user↔humano) | 🟡 | Users hardcoded en env vars `PASS_<USER>`. Sin tabla identidad con cédula+cargo. | 3 días |

## Lo que YA tienes y sirve de base para BRD

- ✓ Stock por lote individual con kardex SUM(movimientos) único (`MEMORY.md:22-29`, `programacion.py:_get_mp_stock`)
- ✓ Producción programada con timestamps reales: `inicio_real_at`, `fin_real_at`, `inventario_descontado_at` (`database.py:2689,2909,2910`)
- ✓ Snapshot de fórmula al ejecutar — migración 99 (`database.py:398-406`); inventario lo escribe en `inventario.py:1150`
- ✓ 4 columnas `operario_*_id` en `produccion_programada` (`database.py:2787-2790`) + triggers que bloquean violaciones tipo Mayerlin (`database.py:4225-4283`)
- ✓ 5 salas con estados + `area_eventos` timeline auditable (`database.py:2914-2933`)
- ✓ SGD electrónico con versionado + capacitaciones firmadas vía HMAC (`database.py:4041-4123`, `aseguramiento.py:797-842`)
- ✓ Workflow CAPA/desviaciones/control-de-cambios completo (`aseguramiento.py:868-1500`)
- ✓ CoA + especificaciones + estabilidades + micro (`database.py:2303-2400`, `3155-3208`)
- ✓ Equipos planta con hoja de vida `equipos_eventos` y cronograma calibraciones (migración 85)
- ✓ MFA TOTP completo y reutilizable (`api/blueprints/mfa.py`)
- ✓ Audit log centralizado con helper único + JSON antes/después (`api/audit_helpers.py`)
- ✓ Backups gzip + offsite opcional + multi-worker lock (`api/backup.py`)
- ✓ CI gates anti-regresión (`scripts/guardian.sh`, `scripts/reviewer.py`, 50 golden paths) — base de OQ trazables

## Gaps NO-NEGOCIABLES para vender BRD a un lab regulado

1. **Trigger SQL append-only sobre `audit_log`** (≈30 líneas DDL).
2. **Audit log en connection independiente con autocommit** — un rollback no debe borrar evidencia §11.10(e).
3. **E-signature workflow real** (re-auth pwd+TOTP, meaning enum, link inmutable).
4. **Lock de records post-aprobación** — triggers RAISE(ABORT) cuando estado IN ('liberado','aprobado','cerrado').
5. **Timestamps UTC unificados** — 465 sitios usan local time.
6. **Tabla `usuarios_identidad` con cédula+cargo+manager** — Part 11 §11.100(b).
7. **Modelo MBR (Master Batch Record) versionado** — fórmula tiene versión, "cómo se fabrica" no.
8. **Modelo EBR (Executed Batch Record)** que componga MBR vigente + ejecución paso-a-paso + IPCs + firmas + desviaciones + reconciliación + liberación QC. Es **el producto** del proyecto.
9. **Equipment cleaning log por equipo individual vinculado a lote** (no solo por sala).
10. **In-Process Controls con specs aprobadas y registros firmados QC**.
11. **Pack CSV mínimo** (URS + Risk Assessment + IQ/OQ/PQ + matriz de trazabilidad).

## Gaps deseables pero postergables

- Migración SQLite → Postgres (aplazada con criterios claros en `SECURITY.md:118-141`)
- CSP nonce sin `'unsafe-inline'` (`SECURITY.md:94-113`)
- Multi-tenancy real (hoy single-tenant)
- Generación PDF nativa con weasyprint/reportlab (HTML imprimible bastaría inicialmente)

## Componentes nuevos que hay que construir para BRD

1. **MBR templates versionados** — `mbr_templates(producto_id, version, estado, vigente_desde, aprobado_por_qa, aprobado_at)` + `mbr_pasos(orden, descripcion, tipo, equipo_requerido_id, tiempo_est_min, ipc_spec_ids[], material_consumo_pct[])`. Endpoints draft→submit→approve(firma QA)→obsolete. Vinculado a `formulas_versiones`.
2. **EBR ejecución paso-a-paso** — `ebr_ejecuciones(lote, mbr_template_id, mbr_version, produccion_id FK, estado, iniciado_por, iniciado_at, cerrado_at)` + `ebr_pasos_ejecutados(ebr_id, paso_id, estado, operario, iniciado_at, completado_at, observaciones, e_sign_id FK)`. UI wizard que evita salto de pasos y captura desviaciones inline.
3. **Reconciliación teórico vs real** — vista por EBR (teórico = sum mbr_pasos × kg_lote vs real = sum movimientos WHERE produccion_id=?). Tabla `lote_reconciliaciones(ebr_id, teorico_kg, real_kg, yield_pct, dentro_spec, justificacion, aprobado_por_qa)`.
4. **IPCs** — `ipc_specs(producto, paso_mbr_id, parametro, unidad, min, max, metodo, frecuencia)` + `ipc_resultados(ebr_id, ipc_spec_id, valor, conforme, medido_por, e_sign_qc_id)`. Bloqueo: out-of-spec → desviación automática + bloqueo avance.
5. **E-signature workflow centralizado** — `e_signatures(table_name, record_id, meaning, signer, signer_full_name, signer_cedula, signed_at_utc, ip, signature_hash, prev_state_hash, comment, challenge_id)` + `e_sign_challenges(username, expires_at, mfa_verified, password_verified)`. Endpoints `POST /api/sign/challenge` y `POST /api/sign/<resource>`.
6. **Equipment cleaning log** — `equipo_limpieza_log(equipo_codigo FK, lote_anterior, lote_siguiente, tipo_limpieza, operario, e_sign_operario, e_sign_qc, verificacion_visual_ok, ts_inicio_utc, ts_fin_utc)`. Bloquea inicio de producción si último uso del equipo no tiene cleaning_log + visual_ok.
7. **PDF maestro auditable EBR** — `GET /api/ebr/<id>/pdf` con weasyprint/reportlab. Header lote+producto+MBR_version + fórmula snapshot + pasos con timestamps+operarios+firmas + IPCs + desviaciones + CAPA + reconciliación + liberación QC/QA. Hash SHA256 + QR. Tabla `ebr_pdf_exports` con audit de descargas.
8. **CSV Pack** — URS, FMEA Risk Assessment, IQ (deploy Render), OQ (50 GPs como base con matriz), PQ (30 días en producción), SOP de uso.

## Hoja de ruta sugerida (3-6 meses)

- **Mes 1** (foundation Part 11): triggers append-only audit_log/sgd_capacitaciones/producciones/desviaciones; audit_log en conn separada autocommit; migración masiva `datetime('now')` → UTC con backfill; tabla `usuarios_identidad` + UI; e-signature core (`/api/sign/challenge`, `/api/sign/<resource>`) reutilizando MFA.
- **Mes 2-3** MVP MBR+EBR: modelar MBR + UI aprobación; importar 5 productos piloto desde "Formulas Maestras/"; EBR con UI wizard operario; conectar a `produccion_programada.iniciar`; integrar e-signatures.
- **Mes 4-5** IPCs+reconciliación+cleaning: `ipc_specs/ipc_resultados` con bloqueo de avance; reconciliación teórico-vs-real (vista+endpoint+dashboard); `equipo_limpieza_log` con bloqueo automático.
- **Mes 6** PDF + validation pack + piloto: PDF auditable EBR con hash+QR; piloto interno HHA con "SUERO NIACINAMIDA 5%"; empaquetar URS+RA+IQ+OQ del piloto.

## Riesgos regulatorios

1. **Falsa sensación de cumplimiento** — auditor experto demuele en 15 min por falta de trigger append-only y re-auth en firmas.
2. **Hora local Bogotá embebida en 465 sitios** sin TZ flag. Auditor extranjero pierde precisión legal.
3. **Audit log dentro de la transacción** — rollback aplicación borra evidencia (data loss reportable en GMP).
4. **MYBATCH (sistema reemplazado)** — no tengo acceso al detalle funcional desde el código (`archive/mybatch-snapshot/` solo tiene 4 JSONs catalog). **Pídeme aclarar qué módulos críticos de MYBATCH (PDF maestro de batch, workflow firmado paso-a-paso) hay que asegurar de no perder regresión funcional**.
5. **Resolución INVIMA 3131/1998** — no estoy 100 % seguro del plazo textual de retención de batch records cosméticos en Colombia (típicamente 3-5 años post-vencimiento del producto). **Pídeme confirmar plazo exacto** antes de fijar política de retención.
6. **Decisión Andina 516/777** — no exige sistemas computarizados validados explícitamente, pero inspectores INVIMA usan Part 11 como benchmark. Sin URS+OQ formales, primer hallazgo será "sistema computarizado en uso GxP sin validación documentada" — observación crítica.
7. **Single point of failure operativo** — `BACKUP_OFFSITE_URL` es opcional. Si Render colapsa sin offsite, perdemos hasta 6 h (fuera de RPO GMP-defendible).
8. **Identity binding débil** — usernames hardcoded sin tabla identidad humana formal.
