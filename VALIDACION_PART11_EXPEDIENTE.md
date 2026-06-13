# Expediente Técnico de Validación · EOS / EBR (Batch Record Digital)
### CFR 21 Part 11 (firmas y registros electrónicos) + marco CSV / GAMP 5 para INVIMA (cosmético)

> **Propósito de este documento.** Reúne, de forma trazable a código y pruebas, los **controles técnicos ya implementados** en EOS que satisfacen los requisitos de 21 CFR Part 11 y dan soporte a una validación de sistema computarizado (CSV) bajo GAMP 5. Está pensado para **entregarse al validador tercero independiente**: le permite mapear cada requisito a su evidencia sin re-descubrir el sistema, reduciendo horas de IQ/OQ/PQ y por lo tanto el **costo de la validación**.
>
> **Aclaración honesta (no re-litigar):** "controles implementados" ≠ "sistema validado". La validación formal (URS → IQ/OQ/PQ → informe firmado) la ejecuta un **tercero independiente**. Este expediente es el insumo, no el certificado.
>
> Última actualización: **2026-06-13** · Generado durante la auditoría de la sesión 12–13 jun.

---

## 1. Alcance

- **Sistema:** EOS — SaaS interno de manufactura para ÁNIMUS Lab + Espagiria Laboratorio (cosmético, regulado INVIMA en Colombia).
- **Subsistema regulado crítico (foco de Part 11):** **EBR / Batch Record Digital** (`api/blueprints/brd.py`) — reemplazo de MyBatch. Tres capas: **MBR** (Master Batch Record aprobado por QA) → **EBR** (ejecución de un lote real) → **IPCs** (controles en proceso con specs y bloqueo OOS) + cleaning log + pesajes + PDF maestro auditable.
- **Subsistemas regulados de soporte:** inventario/kardex (`inventario.py`), calidad/aseguramiento (`aseguramiento.py`, `calidad.py`), liberación de lote, desviaciones/CAPA.
- **Plataforma:** Flask monolito, PostgreSQL en Render (`app.eossuite.com`), 3 workers Gunicorn. Migraciones idempotentes versionadas (`api/database.py`, lista `MIGRATIONS`), aplicadas al boot.

---

## 2. Mapeo de requisitos CFR 21 Part 11 → control EOS → evidencia

Leyenda de evidencia: `archivo:símbolo` (código fuente) · `tabla` (esquema) · `test` (prueba automatizada de regresión).

### Subparte B — Registros electrónicos

| § | Requisito | Control implementado en EOS | Evidencia |
|---|---|---|---|
| **11.10(a)** | Validación del sistema (exactitud, fiabilidad, detección de registros inválidos) | Suite de ~247 *golden paths* + pruebas por módulo corren en cada push (CI `test.yml`); gate pre-push (`guardian.sh`). Reglas de invariantes documentadas (`MEMORY.md`, `CONTRACT_*.md`, `.claude/CERO_ERROR.md`). *La validación formal IQ/OQ/PQ es del tercero — esto es la base de evidencia.* | `tests/test_golden_paths.py`, `.github/workflows/test.yml`, `scripts/guardian.sh` |
| **11.10(b)** | Capacidad de generar copias exactas y completas (legibles/electrónicas) | **PDF maestro del EBR** con todas las estaciones (pasos, IPCs, pesajes, conciliación, despeje, artes, firmas). El footer lleva un **SHA-256 del CONTENIDO** (no de los bytes del PDF, que cambian con el timestamp) → el auditor verifica que el PDF corresponde a un EBR específico no alterado. | `brd.py:pdf_ebr` (hash en `content_hash = hashlib.sha256(...)`), INV-10 en `CONTRACT_brd.md` |
| **11.10(c)** | Protección de registros para recuperación precisa durante el período de retención (inmutabilidad) | **Triggers de base de datos** que bloquean UPDATE/DELETE de registros firmados/aprobados: MBR aprobado (`trg_mbr_*_aprobado`, mig 109), EBR liberado (`trg_ebr_liberado_no_edit`, mig 111), IPC specs (`trg_ipcspec_no_*_aprobado`, mig 112), cleaning log validado (`trg_limpieza_no_edit_qc`, mig 113), pesajes (`trg_pesajes_no_edit/no_delete_liberado`), conciliación (`trg_concmat_no_edit/no_delete_liberado`), artes (`trg_artescod_no_edit_liberado`). **Nunca DELETE de registros regulados** — descontinuar = `activo=0` (reversible, conserva historia). PostgreSQL gestionado en Render con respaldos. | `api/database.py` (CREATE TRIGGER, migs 109/111/112/113 y afines) |
| **11.10(d)** | Acceso limitado a personas autorizadas | Autenticación por sesión Flask + **conjuntos de roles por dominio** (`config.py`: `ADMIN_USERS`, `CALIDAD_USERS`, `PLANTA_USERS`, etc.). Gating por endpoint (`_require_qa_or_admin`, `_require_brd_ejecutor`, `_require_planta_write`). Datos sensibles (bancarios) gateados a admin+contadora (Habeas Data Ley 1581). | `api/config.py`, `brd.py:_require_*`, `auth.py` |
| **11.10(e)** | Audit trail seguro, time-stamped, generado por el sistema (quién, qué, cuándo); no oscurece registros previos; se conserva | Tabla **`audit_log`** (`usuario, accion, tabla, registro_id, detalle, ip, fecha`) en **toda** mutación regulada (inventario, SOL/OC, EBR/MBR, lote, desviaciones). Helper canónico `audit_log()`. Regla dura del proyecto: el audit va **antes** del commit (atómico) o en modo independiente autocommit si va después (M22 — nunca se pierde el rastro). Las descargas de PDF también auditan (`DOWNLOAD_EBR_PDF`). | `audit_helpers.py:audit_log`, tabla `audit_log`, M22 en `CERO_ERROR.md`, `test_audit_ebr_persiste.py` |
| **11.10(f)** | Comprobaciones de secuencia de pasos y eventos (según corresponda) | EBR: pasos en orden; **no se puede completar** con pasos pendientes ni IPCs obligatorios sin reportar/conformes; **no se puede liberar** con desviación abierta / CAPA inefectivo, IPC OOS sin resolver, artes sin aprobar, o (en modo strict) pesajes sin 2ª firma + conciliación + despeje. Transiciones de estado con **CAS** (compare-and-swap, anti-carrera multi-worker: un liberar y un rechazar concurrentes no pueden dejar estado contradictorio — M27/INV-11). | `brd.py:completar_ebr` / `liberar_ebr` / `rechazar_ebr` / `completar_paso_ebr`; INV-1..INV-11 en `CONTRACT_brd.md` |
| **11.10(g)** | Comprobaciones de autoridad (quién puede usar el sistema, firmar, acceder) | Cada acción regulada exige el rol correcto + la firma con el `meaning` correcto. **Segregación de funciones GMP:** el QC que supervisa un paso **no puede** ser el operario que lo ejecutó. | `brd.py:completar_paso_ebr` (chequeo QC ≠ operario), `_require_*` |
| **11.10(h)** | Comprobaciones de dispositivo/fuente de entrada (según corresponda) | Cantidades teóricas de pesaje **calculadas server-side** desde la fórmula (no se aceptan del cliente, anti-manipulación, INV-7). `cantidad_real_g` validada (>0). | `brd.py:reportar_pesaje` (`_calcular_teoricos_mp`), INV-7 |
| **11.10(k)** | Controles sobre la documentación del sistema (distribución, cambios, control de versiones) | Código en control de versiones (git); migraciones **append-only** versionadas; documentos de invariantes por módulo (`CONTRACT_*.md`) actualizados en el mismo commit que el cambio; catálogo de reglas anti-error (`CERO_ERROR.md`). MBR aprobado es inmutable: para cambiar → obsoletar versión + crear `versión+1`. | `api/database.py:MIGRATIONS`, `CONTRACT_*.md`, mig 109 |

### Subparte C — Firmas electrónicas

| § | Requisito | Control implementado en EOS | Evidencia |
|---|---|---|---|
| **11.50** | Manifestación de la firma (nombre del firmante, fecha/hora, significado de la firma) | Tabla **`e_signatures`**: `signer_username, signer_full_name, signer_cedula, signer_cargo, signed_at_utc, meaning, ip, auth_factor, comment`. El `meaning` distingue *ejecuta / supervisa / aprueba / libera / rechaza*. | tabla `e_signatures`, `brd.py` (consumo de `signature_id`) |
| **11.70** | Vínculo firma↔registro (no transferible/copiable a otro registro) | `e_signatures.record_table` + `record_id` enlazan la firma a su registro exacto; `record_hash` + `signature_hash` sellan el contenido firmado. `_validar_signature` verifica que el `signature_id` corresponde a *ese* registro, *ese* `meaning` y *ese* firmante antes de aceptar la acción. | `brd.py:_validar_signature` (líneas ~838), columnas `record_hash`/`signature_hash` |
| **11.100(a)** | Firma única, no reutilizable, no reasignable | `e_signatures` por evento (record_table+record_id+meaning+firmante); usuarios con identidad única (username) + snapshot de identidad (cédula/cargo) al firmar. | tabla `e_signatures` |
| **11.200(a)** | Componentes de la firma electrónica (no biométrica): ≥2 componentes; re-autenticación | **Re-autenticación por firma**: `POST /api/sign` exige password **+ TOTP** (si el usuario tiene MFA enrolado). El código cita explícitamente "21 CFR Part 11 §11.200(a)(1)(ii)". | `brd.py:1207` (doc §11.200), `firmas.py:_verify_password` + `_verify_totp_if_enrolled` |
| **11.300(a)(b)** | Controles sobre identificación/contraseñas (unicidad, expiración, hashing) | Contraseñas **solo** como hash `pbkdf2:sha256:600000` o `scrypt` — **plaintext rechazado** con warning CRÍTico al boot. Reset por admin re-hashea. | `core.py:1472` (rechazo plaintext), `admin.py:2682` (`generate_password_hash pbkdf2:sha256:600000`), `config.py` |
| **11.300(d)** | Salvaguardas contra uso no autorizado de credenciales (MFA, bloqueo) | **MFA TOTP** (pyotp) obligatorio para admins; rate-limit de login; cookie `mfa_trusted` controlada. | `firmas.py`, `core.py:1486` (flujo TOTP), `mfa.py` |

---

## 3. Marco CSV / GAMP 5 — qué hace el validador, qué aporta EOS

La validación formal es un proceso del **tercero independiente**. EOS aporta los insumos:

| Fase CSV (GAMP 5) | Responsable | Insumo que EOS ya tiene |
|---|---|---|
| **URS** (User Requirements Specification) | Conjunto (Sebastián + validador) | Reglas de negocio e invariantes documentadas (`MEMORY.md`, `CONTRACT_*.md`) → base directa para redactar la URS. |
| **Evaluación de riesgo / categoría GAMP** | Validador | Sistema configurable a medida (categoría 5). Este expediente cubre los controles. |
| **IQ** (Installation Qualification) | Validador | Arquitectura, entorno (Render/PG), variables, procedimiento de deploy y migraciones (`RUNBOOK.md`, `api/database.py`). |
| **OQ** (Operational Qualification) | Validador | Casos de prueba ejecutables (`tests/test_golden_paths.py` + por módulo) → evidencia objetiva de que las funciones operan según especificación; el validador puede re-ejecutarlos. |
| **PQ** (Performance Qualification) | Validador (en producción, con usuarios) | Trazas de sesión / audit_log reales como evidencia de desempeño. |
| **Informe de validación + plan de mantenimiento** | Validador | Control de cambios vía git + migraciones versionadas + `CONTRACT`/`CERO_ERROR` como SOP de cambios. |

---

## 4. Índice de evidencia (dónde vive cada control)

- **Firmas electrónicas:** `api/blueprints/firmas.py` (`POST /api/sign`, verificación password+TOTP), `api/blueprints/brd.py:_validar_signature`, tabla `e_signatures`.
- **Audit trail:** `api/audit_helpers.py:audit_log`, tabla `audit_log`; regla M22 (`CERO_ERROR.md`).
- **Inmutabilidad:** triggers en `api/database.py` (migs 109/111/112/113 y `trg_*_no_edit/no_delete_*`).
- **Gates de liberación/completar (secuencia + autoridad + OOS fail-closed):** `api/blueprints/brd.py` (`completar_ebr`, `liberar_ebr`, `rechazar_ebr`, `completar_paso_ebr`, `reportar_pesaje`, `reportar_ipc_resultado`).
- **Roles / acceso:** `api/config.py`, `api/blueprints/auth.py`.
- **Contraseñas / MFA:** `api/blueprints/core.py`, `api/blueprints/mfa.py`, `scripts/gen_password_hashes.py`.
- **Invariantes y su prueba:** `api/blueprints/CONTRACT_brd.md` (INV-1..INV-11), `tests/test_ebr_*.py`, `tests/test_audit_ebr_persiste.py`.

---

## 5. Brechas honestas / qué debe verificar el validador (no ocultar)

1. **Validación formal pendiente:** no existe aún el paquete URS/IQ/OQ/PQ firmado por un tercero. Este expediente lo habilita y abarata, no lo sustituye.
2. **Modo de enforcement del EBR (`EBR_MODE`):** se enciende por fases `off → warn → strict`. Para uso regulado pleno debe operar en **strict** (exige pesajes verificados + conciliación + despeje antes de liberar). Confirmar el modo de producción al momento de la validación.
3. **Retención y respaldo:** PostgreSQL gestionado por Render incluye respaldos; el validador debe documentar la **política de retención** (años) y el procedimiento de restauración como parte del IQ.
4. **Sellado de tiempo:** los timestamps usan UTC del servidor (`datetime('now','utc')` / `*_at_utc`); para auditoría se presentan en zona Colombia. El validador debe constatar la fuente de tiempo confiable.
5. **Cualificación de usuarios / SOPs / capacitación:** Part 11 presupone procedimientos administrativos (políticas de firma, capacitación, responsabilidad del firmante §11.10(j)). Eso es **organizacional**, fuera del software — debe existir en papel/SOP.
6. **Trazabilidad lote MP → producto terminado:** `ebr_pesajes.lote_mp` registra el lote de MP pesado; verificar con el validador la cadena completa MP→PT para recall.

---

## 6. Postura de datos y seguridad (contexto para el validador)

- Auth en capa de aplicación (sesiones + roles); EOS conecta a PG con un solo rol dueño. No se usa PostgreSQL RLS (decisión arquitectónica).
- Headers de seguridad (HSTS, X-Frame-Options, CSP, etc.) y verificación de Origin/Referer (CSRF) en métodos que mutan.
- Datos personales/bancarios bajo Habeas Data (Ley 1581): visibles solo a admin+contadora.
- Nada destructivo sin respaldo + reversibilidad (audit_log guarda valor previo); descontinuar = `activo=0`, nunca DELETE.

---

*Documento vivo. Mantener sincronizado con el código en el mismo commit cuando cambie un control regulado. Verificado contra el código fuente real (no aspiracional) durante su redacción.*
