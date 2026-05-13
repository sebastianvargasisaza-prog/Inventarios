# Auditoría · Salto a SaaS multi-tenant + Batch Record digital

> **Documento de decisión.** Consolidación de los 3 ejes auditados (multi-tenant, GMP/BRD, deuda técnica) con un veredicto único, decisiones que hay que tomar YA, y hoja de ruta priorizada para horizonte 3-6 meses.

**Fecha**: 2026-05-12
**Auditor**: Claude Code (3 sub-agentes paralelos · sources en `EJE_1_*.md`, `EJE_2_*.md`, `EJE_3_*.md`)
**Decisor**: Sebastián Vargas (CEO HHA Group · único dev)

---

## TL;DR

**El plan original de "EOS multi-tenant SaaS + Batch Record digital regulado en 3-6 meses" no es ejecutable** — requiere 9-15 meses con 1 dev, o 6-9 meses con 2 devs.

**Sí cabe en 3-6 meses una versión disciplinada**: BRD MVP funcional para uso interno HHA + foundation técnica para multi-tenant + 1 cliente piloto deploy-per-customer no-farma-estricto. Es un producto vendible y defendible, pero **no es "abrir el grifo SaaS público"**.

**La pregunta real que tienes que responder no es técnica sino de producto:**

> ¿Quieres lanzar **SaaS público autoservicio** (signup → Stripe → onboarding → uso) o **white-label hosted** (vender contratos, deployment-per-cliente, onboarding manual)?

La diferencia es 6-12 meses de trabajo y un perfil de cliente totalmente distinto.

---

## Veredicto consolidado por eje

| Eje | Veredicto | Sub-veredicto |
|---|---|---|
| **Multi-tenant SaaS** | 🔴 BLOQUEANTE | 0 `tenant_id` en 167 tablas. Hay un campo `empresa` mal normalizado que da falsa seguridad. RBAC por nombre propio (19 personas hardcoded). Cero billing/onboarding/SSO. **6-9 meses para SaaS lógico real.** |
| **GMP / Batch Record** | 🟡 BASE PARCIAL | Tienes ~90% de los datos brutos que un EBR necesita pero ningún workflow que los componga en un legajo firmable. 11 gaps no-negociables Part 11 (audit_log mutable, sin e-sign real, sin MBR/EBR, 465 timestamps en hora local). **MVP factible en 4-5 meses.** |
| **Deuda técnica** | 🔴 ALTO RIESGO | `admin.py` 22.570 LoC con 134 endpoints. `database.py` 524 KB. 47 cron jobs internos en worker pool. Sin staging, sin DR probado en CI, ratio test:código 1:2.9. **4-6 meses de refactor previo si quieres base validable.** |

**Veredicto único: 🔴 NO en 3-6 meses para "SaaS público + BRD GMP estricto vendible".**
**🟡 SÍ en 3-6 meses para "BRD MVP interno + foundation multi-tenant + 1 cliente deploy-per-customer".**

---

## 5 decisiones que tienes que tomar antes de arrancar

Estas no las puedo decidir yo. Una vez decidas, el plan baja en cascada.

### Decisión 1 · Modelo de negocio del SaaS

| Opción | Implica | Horizonte realista |
|---|---|---|
| **A. SaaS público autoservicio** (signup, Stripe, onboarding wizard) | Multi-tenancy lógico real + billing + SSO + soporte 24/7 | 9-15 meses |
| **B. White-label hosted** (contrato → deployment Render-per-cliente) | Multi-tenancy físico + branding por tenant + onboarding manual | 3-4 meses |
| **C. Híbrido** (B ahora, A en mes 12+) | Empezar con B y migrar a A cuando justifique | Recomendado |

**Mi recomendación**: **C**. Lanzas con deploy-per-cliente en mes 4-5, validas con 2-3 clientes reales, y al cliente #10 justificas el rewrite a multi-tenancy lógico con Postgres + RLS.

### Decisión 2 · Perfil de cliente para piloto externo

| Opción | Implica |
|---|---|
| **A. Lab cosmético colombiano regulado por INVIMA** | Necesitás CSV pack completo (URS/IQ/OQ/PQ + Risk Assessment), audit_log append-only, e-sign real. **NO cabe en 6 meses.** |
| **B. Lab cosmético chico no-regulado o microempresa B2C** | BRD opcional, sin CSV. **Cabe en 4 meses.** Margen menor. |
| **C. Solo HHA durante 6 meses, abrir externos en mes 12+** | Cero presión externa, foco total en BRD interno + foundation. |

**Mi recomendación**: **C** en mes 1-6 (HHA es tu validador), **B** en mes 6-9 (1-2 clientes piloto sin presión regulatoria), **A** en mes 12+ (cuando CSV pack esté hecho).

### Decisión 3 · Postgres ahora o después

| Opción | Pros | Contras |
|---|---|---|
| **Migrar a Postgres en Mes 1-2** | Multi-tenant lógico real posible. Concurrencia. RLS. | 6-9 sem migrando 352 INSERT OR REPLACE, 59 triggers, 161 AUTOINCREMENT. Riesgo romper 50 golden paths. |
| **Quedarse en SQLite + deploy-per-cliente** | Cero riesgo de migración. Aislamiento físico perfecto. Backups por tenant triviales. | Tope ~10 clientes en 1 disco Render. Multi-tenancy lógico imposible. |

**Mi recomendación**: **SQLite hasta mes 12.** Combinar con deploy-per-cliente de Decisión 1 = consistente. Postgres se vuelve necesario cuando haya cliente #11+ y un caso de negocio que justifique el rewrite.

### Decisión 4 · Contratar ayuda

Hoy sos único dev, CEO, MD, médico. Los 3 ejes coinciden en que el bus factor de 1 es el riesgo #1. Para horizonte 3-6 meses agresivo:

| Opción | Costo aproximado | Capacidad ejecutiva |
|---|---|---|
| **A. Tú solo, 6 meses** | $0 | 600-900 hrs · realista bajo a moderado |
| **B. + 1 senior backend full-time** | $4-7k USD/mes | 1.200-1.800 hrs · realista alto |
| **C. + 1 senior backend half-time + 1 QA validación GMP** | $6-9k USD/mes | 1.500 hrs + expertise CSV · ideal para BRD |

**Mi recomendación**: **C** si BRD es prioridad real. **B** si lo principal es vender SaaS rápido. **A solo es viable si recortas alcance** (ej: solo BRD interno sin SaaS).

### Decisión 5 · Información que faltó al auditor (responder antes de arrancar)

Los sub-agentes te dejaron 4 preguntas pendientes:

1. **MYBATCH** (sistema actual de batch records que reemplazan): ¿qué módulos críticos hay que asegurar de no perder en regresión? El agente solo encontró 4 JSONs catálogo en `archive/mybatch-snapshot/`.
2. **Resolución INVIMA 3131/1998**: ¿conoces el plazo textual de retención de batch records cosméticos? (típicamente 3-5 años post-vencimiento, hay que confirmar para fijar política de backups).
3. **PI de fórmulas**: `formula_items` tiene 21 fórmulas reales de HHA (Blush Balm, Suero Vit C, etc., mig 104). ¿El provisioning a otros clientes va a NO seedear este catálogo, correcto?
4. **Mayerlin trigger SQL** (mig 82): específica de tu staff. ¿La movemos a `tenant_settings` o eliminamos el trigger y validamos en Python?

---

## Hoja de ruta recomendada · 6 meses · alcance honesto

> Asume Decisiones C/C/SQLite/B-o-C/responder pendientes.
> Si trabajas solo: cada mes representa ~150 hrs reales. Multiplica por 1.5 si seguís haciendo CEO en paralelo.

### Fase 0 · Foundation crítica (Mes 1-2)

**Objetivo**: cerrar bloqueantes Part 11 y multi-tenant scaffolding sin lanzar.

| # | Trabajo | Eje | Esfuerzo |
|---|---|---|---|
| 1 | Trigger SQL append-only sobre `audit_log` | E2 | 1 día |
| 2 | Audit log en conexión separada con autocommit (rollback no borra evidencia) | E2 | 3 días |
| 3 | Migración masiva 465 sitios `datetime('now')` → UTC con backfill | E2 | 7 días |
| 4 | Tabla `usuarios_identidad` (cédula + cargo + manager) | E2 | 3 días |
| 5 | E-signature workflow core (`/api/sign/challenge` + `/api/sign/<resource>`) reutilizando MFA | E2 | 7 días |
| 6 | Lock de records post-aprobación (triggers RAISE(ABORT) WHEN OLD.estado IN ('liberado','aprobado','cerrado')) | E2 | 5 días |
| 7 | Tablas `tenants`, `users`, `tenant_users`, `roles`, `user_roles`, `tenant_settings`, `tenant_integrations` (mig 105-110) sin lanzar | E1 | 7 días |
| 8 | Refactor RBAC: eliminar `ADMIN_USERS` constante, mover a `has_role(user, 'admin')` | E1 | 7 días |
| 9 | Eliminar nombres propios de SQL (`WHERE LOWER(email) LIKE '%alejandro%'` y similares, ~150 lugares) | E1 | 5 días |
| 10 | Mover constantes hardcoded a `tenant_settings`: `LIMITES_APROBACION_OC`, `FORMULA_PIN`, threshold gerencia 5%, `AREA_USERS`, `USER_EMAILS`, branding | E1 | 5 días |
| 11 | Quick wins E3: `pytest --cov` en CI, `test_backup_restoration.py` mensual cron, UptimeRobot externo, staging Render, LIMIT 200 default | E3 | 3 días |
| 12 | Partir `admin.py` (22.570 LoC) en 4-5 sub-blueprints por dominio | E3 | 8 días |

**Total Fase 0: ~60 días-dev = 2 meses solo, 1 mes con +1 senior.**

### Fase 1 · MVP Batch Record interno HHA (Mes 3-4)

**Objetivo**: piloto BRD con producto real (ej: SUERO NIACINAMIDA 5%) desplegado solo en HHA.

| # | Trabajo | Esfuerzo |
|---|---|---|
| 1 | Modelo MBR (Master Batch Record) versionado: `mbr_templates` + `mbr_pasos` con workflow draft→submit→approve(QA)→obsolete | 10 días |
| 2 | Importar 5 productos piloto desde "Formulas Maestras/" como MBR draft | 3 días |
| 3 | UI aprobación QA de MBR con e-signature | 5 días |
| 4 | Modelo EBR (Executed Batch Record): `ebr_ejecuciones` + `ebr_pasos_ejecutados` vinculado a `produccion_programada` | 10 días |
| 5 | UI wizard operario paso-a-paso (sin saltos, captura observaciones, dispara desviaciones inline) | 12 días |
| 6 | IPCs (`ipc_specs` + `ipc_resultados`) con bloqueo de avance si out-of-spec | 8 días |
| 7 | Equipment cleaning log por equipo individual con bloqueo de inicio si no hay cleaning | 7 días |
| 8 | Reconciliación teórico vs real (vista + endpoint + dashboard) vinculada al kardex | 5 días |
| 9 | PDF maestro auditable EBR (weasyprint o reportlab) con hash SHA256 + QR | 7 días |
| 10 | Piloto interno HHA: producir 3 lotes con BRD digital, comparar vs MYBATCH | 10 días |

**Total Fase 1: ~75 días-dev = 2.5 meses solo, 1.5 con +1 senior.**

### Fase 2 · Foundation multi-tenant + 1 cliente piloto (Mes 5-6)

**Objetivo**: probar deployment-per-cliente con 1 lab piloto no-regulado.

| # | Trabajo | Esfuerzo |
|---|---|---|
| 1 | Wizard `/onboarding` (empresa → primer admin → seed catálogos blancos) | 7 días |
| 2 | `scripts/provision_tenant.sh` que crea Render service via API + DB blank + subdominio | 5 días |
| 3 | `tenant_integrations` cifrado at-rest (Calendar, Shopify, GHL, Email por tenant) | 7 días |
| 4 | Refactor sync Calendar/Shopify/GHL para credenciales por DB | 5 días |
| 5 | Cron jobs reciben `tenant_id` (47 jobs en `multi-cron`) | 5 días |
| 6 | Suite tests cross-tenant (50+ tests "A nunca ve B") | 7 días |
| 7 | Documentar `RUNBOOK_TENANT_PROVISIONING.md` | 2 días |
| 8 | Onboarding manual de 1 cliente piloto (lab cosmético chico no-INVIMA) | 5 días |
| 9 | CSV pack mínimo para HHA (URS + Risk Assessment + IQ/OQ/PQ del piloto BRD interno) | 15 días (paralelo, no requiere dev) |

**Total Fase 2: ~45 días-dev + 15 días docs = 1.5 meses solo, 1 mes con +1 senior.**

### Lo que NO entra en 6 meses

- Multi-tenancy lógico real (sigue deploy-per-cliente)
- Postgres
- SAML/SSO enterprise (Google OAuth tal vez en mes 7)
- Marketplace de fórmulas
- White-label completo (dominio + email + branding 100% del cliente)
- Stripe/Bold/Wompi billing automatizado (puede ser facturación manual hasta mes 9)
- BRD para clientes farmacéuticos GMP estrictos (necesita CSV completo + auditoría externa)
- SOC 2 / ISO 27001
- Refactor `auto_plan.py` (10.853 LoC, 5-10% coverage)

---

## Lo que recomiendo NO HACER

1. **No te metas con Postgres en estos 6 meses.** SQLite + deploy-per-cliente cumple. Postgres = 6-9 sem extra de migración con riesgo de romper 50 golden paths. Reserva para mes 12+.
2. **No prometas a clientes externos un BRD validado INVIMA antes del mes 9.** Sin CSV pack es indefendible en auditoría.
3. **No abras signup público.** Onboarding manual durante los primeros 5-10 clientes. Después, automatizar.
4. **No pretendas hacerlo solo en 6 meses sin recortar alcance.** Bus factor 1 + CEO + MD = horizonte se duplica realista. Decisión 4 es crítica.
5. **No extiendas el campo `empresa` existente como tenant_id.** Está roto (mal normalizado, queries case-sensitive ad-hoc, solo en 16 tablas). Crear `tenant_id` paralelo y migrar luego.
6. **No metas tests "para tener cobertura" en `auto_plan.py`** todavía. 10.853 LoC con 89 endpoints — tests ahora son cementables. Refactorizar primero (mes 7+) y luego cubrir.

---

## Riesgos consolidados (top 10)

| # | Riesgo | Severidad | Mitigación |
|---|---|---|---|
| 1 | **Bus factor 1** (Sebastián único dev + CEO + MD) | 🔴 Crítico | Contratar 1 senior (Decisión 4) |
| 2 | **Cross-tenant data leak** si se mete un 2º cliente al mismo deployment sin tenant_id real | 🔴 Crítico | Nunca permitir 2 tenants en mismo Render service hasta mes 12+ |
| 3 | **Audit log mutable** (sin trigger append-only) | 🔴 Crítico | Fix Fase 0 trabajo #1 |
| 4 | **PI de fórmulas HHA** seedeada accidentalmente a otros clientes (`formula_items` con 21 fórmulas reales, mig 104) | 🔴 Crítico | Provisioning con catálogos blancos. Validar Decisión 5.3 |
| 5 | **Auditor INVIMA experto destruye el BRD** por falta de CSV/append-only/re-auth en firmas | 🟡 Alto | Pack CSV completo antes de vender a farma estricto. Postergar mes 9+ |
| 6 | **Sin staging** (push main → prod directo) en sistema regulado | 🟡 Alto | Quick win Fase 0: clonar service Render branch staging |
| 7 | **`admin.py` no validable GMP** (22.570 LoC, 134 endpoints, 196 fetchall) | 🟡 Alto | Fase 0 trabajo #12 (partir en 4-5 blueprints) |
| 8 | **47 cron jobs en worker pool Gunicorn** (job lento bloquea HTTP) | 🟡 Alto | Mes 7+: mover a worker dedicado o Render Cron Jobs externos |
| 9 | **Mayerlin trigger SQL** específico de staff Espagiria (mig 82) — rompe golden paths si se generaliza | 🟡 Medio | Decisión 5.4 + golden path nuevo cross-tenant |
| 10 | **104 migraciones N veces por cada deployment-per-cliente** (15-30s startup) | 🟢 Bajo | Snapshot DB ya migrada al provision (Fase 2 trabajo #2) |

---

## Tres caminos posibles · elegí uno

### Camino A · "EOS interno HHA + BRD MVP" (lo más conservador)
- Solo Fase 0 + Fase 1.
- Termina en mes 4 con BRD funcionando internamente, foundation multi-tenant lista pero no lanzada.
- Sin clientes externos en 6 meses. Validación con HHA durante mes 5-6.
- **Recomendado si**: querés calidad sobre velocidad, sos solo, INVIMA es prioridad.

### Camino B · "BRD interno + 1 cliente piloto no-regulado" (mi recomendación)
- Fase 0 + Fase 1 + Fase 2 completas.
- Termina en mes 6 con BRD HHA + 1 cliente piloto cosmético chico activo.
- Validación dual: regulado interno + no-regulado externo.
- **Recomendado si**: querés validar el modelo SaaS sin riesgo regulatorio externo.

### Camino C · "SaaS público con BRD validado en 6 meses" (no recomendado)
- Requiere 2-3 devs full time + QA validación + abogado regulatorio.
- Costo: $25-40k USD/mes durante 6 meses = $150-240k USD total.
- Riesgo: 50/50 de no llegar.
- **Recomendado solo si**: tenés capital, equipo, y el primer cliente firmado por anticipado.

---

## Próximos pasos (esta semana)

1. **Tomar las 5 decisiones** de la sección anterior.
2. **Responder las 4 preguntas pendientes** de los auditores (MYBATCH, retención INVIMA, PI fórmulas, Mayerlin trigger).
3. **Si Camino B**: arrancar Fase 0 trabajo #1 (trigger append-only audit_log) — es 1 día y cierra el gap regulatorio más visible.
4. **Si vas a contratar**: empezar búsqueda de senior backend con experiencia GMP/CSV (perfil Colombia o LatAm hispano hablante para alineación con HHA).
5. **Crear repo separado** `eos-csv-pack` para empezar a documentar URS en paralelo al desarrollo (no bloquea nada).

---

## Referencias

- `docs/auditoria/EJE_1_MULTITENANT.md` — análisis multi-tenant completo
- `docs/auditoria/EJE_2_GMP_BRD.md` — análisis Part 11 / GMP completo
- `docs/auditoria/EJE_3_DEUDA_TECNICA.md` — análisis deuda técnica completo
- `MEMORY.md` — reglas de dominio
- `RUNBOOK.md` — operaciones
- `SECURITY.md` — postura de seguridad
- `GOLDEN_PATHS_INVENTORY.md` — cobertura E2E
