# Plan EOS · ERP vertical farma-cosmético + BRD integrado

> **Reframe 2026-05-12.** EOS NO es "una app + un BRD". Es **un ERP vertical
> para laboratorio cosmético/farmacéutico colombiano certificado INVIMA**
> que YA tiene módulos vivos (Inventario, Calendar, Compras, Aseguramiento,
> Animus, Espagiria, RRHH...) y que necesita:
>
> 1. **Fundación técnica fuerte** para que cualquier módulo escale sin
>    colapsar (la deuda no se "cierra después", se trabaja continua).
> 2. **Mejorar los módulos existentes** que ya están en uso (Planta es el
>    más mencionado, pero hay otros).
> 3. **Sumar BRD digital** como módulo nuevo regulatorio (no dominante).
> 4. **Estabilizar operaciones** (DR, observabilidad).
> 5. **Pre-venta** cuando esté listo (ambición SaaS, evaluable).
>
> Las 5 dimensiones se trabajan **en paralelo por bloques de 2-3 semanas**.
> Cada bloque mezcla deuda + ERP + BRD + ops para que la app crezca
> equilibrada, no torcida.

Fecha: 2026-05-12 · revisión post-cierre Fase 1 BRD.

---

## Visión

EOS = sistema operativo único para HHA Group (ÁNIMUS Lab + Espagiria
Laboratorio) que cubre:

- Operaciones diarias (Inventario, Compras, Calendar, Producción, RRHH).
- Cumplimiento regulatorio INVIMA (Aseguramiento, BRD digital, SGD).
- Capa comercial (Maquila B2B, Clientes Animus).
- Reportería ejecutiva (Gerencia, Finanzas).

Y que en mes 9-12 puede potencialmente venderse a otros labs colombianos
del mismo perfil (cosmético INVIMA). Pero esa decisión se toma cuando la
fundación esté sólida, no antes.

---

## Las 5 dimensiones (trabajo continuo, en paralelo)

### Dimensión 1 · Fundación técnica (código fuerte, escalable, mantenible)

**Por qué importa**: hoy la app funciona pero los monolitos (`admin.py`
22k LoC, `auto_plan.py` 10k LoC) hacen que cualquier cambio sea un
ejercicio de equilibrio. Sin fundación, el cliente #5 no entra y
mantenerlo sin enloquecer es imposible.

| Trabajo | Esfuerzo | Cuándo |
|---|---|---|
| Partir `admin.py` (22.570 LoC) en 4-5 sub-blueprints | 30-40h | Bloque temprano |
| Refactor `auto_plan.py` (10.853 LoC) en 3 módulos | 40-50h | Bloque medio |
| Bloque B UTC completo (~25 sites restantes) | 12-16h | Bloque temprano |
| Migrar `templates_py/` a Jinja2 + CSP nonce | 20-24h | Bloque medio |
| Decorator `@safe_endpoint` (reemplazar 1.290 except Exception) | 16-20h | Bloque medio |
| 23 CONTRACT_*.md restantes | 12-16h | Continuo |
| OpenAPI/Swagger auto-generado | 16h | Bloque tardío |
| Subir cobertura tests a 50%+ con `pytest --cov` en CI | continuo | Cada bloque |

### Dimensión 2 · ERP vivo (módulos existentes que necesitan refinamiento)

**Por qué importa**: la gente de HHA YA usa estos módulos todos los días.
Cada bug que arreglemos o feature que agreguemos mejora el día-a-día
real, no abstracciones futuras.

**Necesito que me digas las prioridades por módulo**, pero acá un mapa
de qué tenemos:

| Módulo | Estado | Posibles mejoras (necesito tu input) |
|---|---|---|
| **Planta** | 🟡 funcional, **necesita más trabajo según vos** | ⚠️ pendiente: top 3 dolores actuales |
| **Inventario / Bodega MP** | 🟢 sólido | mejoras menores (FEFO display, conteo móvil) |
| **Compras (3 fuentes SOL)** | 🟢 sólido | recepción mejorada, comprobante de pago |
| **Aseguramiento (CAPA, SGD)** | 🟢 sólido | workflow extras pendientes |
| **Calidad equipos** | 🟡 parcial | calibraciones, stocks repuestos |
| **Comercial / Maquila** | 🟡 parcial | pipeline B2B faltan E2E tests, dashboard cliente |
| **Animus (skincare)** | 🟢 sólido para HHA | conteo cíclico app móvil |
| **Espagiria** | 🟡 funcional | módulo dedicado en evolución |
| **RRHH** | 🟡 básico | onboarding workflow, vacaciones |
| **Marketing** | 🟡 bolt-on | métricas, influencers, sin tests |
| **Gerencia / Reportería** | 🟡 básico | dashboards ejecutivos |
| **Admin** | 🔴 monolito 22k | partir + refinar (Dim 1) |

### Dimensión 3 · BRD digital (módulo NUEVO regulatorio)

**Estado**: backend completo (Fase 1 cerrada hoy). UI v2 con firmas. Falta
hacerlo usable end-to-end con UI completa para operarios + importar
legado MyBatch + piloto real.

| Trabajo | Esfuerzo |
|---|---|
| UI ejecución pasos (botones iniciar/completar paso desde detalle EBR) | 12-16h |
| Form reportar IPC + pesaje desde UI | 14-18h |
| UI cleaning log (iniciar + validar QC) | 6-8h |
| Importar legado MyBatch (26 productos PT, 5 áreas, 52 OPs, 25 PDFs metadata) | 16-20h |
| Mig: agregar `codigo_pt`, `numero_op` (secuencial anual), `zona` áreas | 4h |
| Vista MyBatch-compatible (3 estados terminales + numero_op) | 6h |
| Importar SOPs SGD a pasos MBR (cuando existan) | 8-12h |
| Piloto interno HHA: 3 lotes reales en paralelo a MyBatch | ~30h |
| Iteración post-piloto sobre feedback Calidad | ~30h |

**Lo que NO falta**: el backend está completo. Triggers de inmutabilidad,
e-signatures, audit append-only, retención 3 años, PDF auditable, hook
auto-EBR al iniciar producción Calendar — todo eso ya está deployado.

### Dimensión 4 · Operaciones (DR, observabilidad, salud sistema)

**Por qué importa**: si Render se cae a las 3am o hay corrupción de DB,
hoy nadie se entera y se pierden datos. Para un sistema regulado eso es
inaceptable.

| Trabajo | Esfuerzo |
|---|---|
| Activar `BACKUP_OFFSITE_URL` real (S3/B2/GCS presigned) | 4h |
| UptimeRobot externo → `/api/health` con alertas email/SMS | 2h |
| Staging environment Render (clonar service + branch staging) | 4h |
| `pytest --cov` en CI (cobertura visible en cada PR) | 4h |
| Cron mensual `test_backup_restoration.py` en GitHub Actions | 2h |
| Endpoint `/metrics` Prometheus + Grafana Cloud free | 12h |
| Configurar 19 `PASS_<USER>` reales + completar `usuarios_identidad` | 6h |
| RTO/RPO documentado en RUNBOOK + drill mensual | 4h |
| C2 lock post-aprobación: triggers SQL en producciones, OC pagada, conteos cerrados | 16-20h |
| Pack URS + IQ + matriz tests (CSV mínimo) | 36h |

### Dimensión 5 · Pre-venta (decisión post mes 6)

**Por qué importa**: la ambición SaaS está pero NO debe contaminar el
trabajo de hoy. La decisión real se toma cuando HHA tenga 10+ lotes con
BRD funcionando y la fundación esté sólida.

| Trabajo (solo si se decide post mes 6) | Esfuerzo |
|---|---|
| Tablas `tenants`, `users`, `tenant_users`, `roles`, `tenant_settings` | 24h |
| Refactor RBAC: eliminar nombres propios, mover constantes a `tenant_settings` | 30h |
| Provisioning script Render-per-cliente | 16h |
| Branding por tenant (logo, brand_name, company_legal en PDFs) | 12h |
| `tenant_integrations` cifrado at-rest (Calendar, Shopify, GHL por tenant) | 16h |
| Onboarding manual + facturación manual primeros 5 clientes | ~40h |
| SSO Google OAuth | 16h |

**Recomendación**: NO trabajar en esta dimensión hasta mes 6 mínimo.

---

## Filosofía de bloques (no fases lineales)

En lugar de "Fase 1 BRD, Fase 2 deuda, Fase 3 ops" (que da apps torcidas),
trabajamos en **bloques de 2-3 semanas** que mezclan dimensiones:

**Cada bloque típico contiene:**
- 1 trabajo de Dimensión 1 (fundación · 30-50% del tiempo)
- 1 trabajo de Dimensión 2 (mejora ERP existente · 30-40%)
- 1 trabajo de Dimensión 3 o 4 (BRD o ops · 20-30%)

Esto garantiza que cada 2-3 semanas la app está **mejor en varias
dimensiones**, no solo en una.

---

## Bloques propuestos para 2026 H2

### Bloque B1 · "Fundación + Planta + UI BRD" (3 semanas)

| Item | Dim | Esfuerzo |
|---|---|---|
| Bloque B UTC completo (~25 sites blueprints) | 1 | 14h |
| **TOP 3 dolores Planta** (necesito tu input) | 2 | 30h |
| UI ejecución pasos BRD (iniciar/completar paso) | 3 | 14h |
| Form reportar IPC desde UI | 3 | 8h |

**Entregable**: app más limpia + Planta mejorado + BRD usable end-to-end
para flujos básicos.

### Bloque B2 · "Partir admin.py + Importar MyBatch" (3 semanas)

| Item | Dim | Esfuerzo |
|---|---|---|
| Partir `admin.py` en 4-5 sub-blueprints (sólo MOVE) | 1 | 35h |
| Importar legado MyBatch (productos PT, áreas, OPs, PDFs metadata) | 3 | 18h |
| Mig agregar codigo_pt + numero_op + zona | 3 | 4h |
| 1-2 mejoras Aseguramiento o Compras | 2 | 15h |

**Entregable**: codebase admin manageable + BRD continuidad histórica.

### Bloque B3 · "Operaciones + Templates Jinja + Piloto BRD inicio" (3 semanas)

| Item | Dim | Esfuerzo |
|---|---|---|
| BACKUP_OFFSITE_URL + UptimeRobot + staging Render | 4 | 12h |
| `pytest --cov` CI + restore test mensual | 4 | 6h |
| Migrar 5 templates_py más críticos a Jinja2 (proof of concept) | 1 | 16h |
| Iniciar piloto BRD HHA (1 lote real Blush Balm) | 3 | 12h |

**Entregable**: ops sólidas + 1 lote real con BRD digital.

### Bloque B4 · "Endurecer regulatorio + 1-2 mejoras ERP" (3 semanas)

| Item | Dim | Esfuerzo |
|---|---|---|
| C2 lock post-aprobación (triggers en producciones, OC) | 4 | 18h |
| Migrar 50 audit_log call sites a Part 11 puro | 1 | 14h |
| Pack URS mínimo + matriz tests | 4 | 20h |
| Mejora ERP a definir (módulo X) | 2 | 15h |

**Entregable**: defensible en auditoría INVIMA + 1 módulo más sólido.

### Bloque B5 · "Refactor auto_plan + Piloto BRD escalado" (4 semanas)

| Item | Dim | Esfuerzo |
|---|---|---|
| Refactor `auto_plan.py` en 3 módulos + cobertura 60% | 1 | 45h |
| 2-3 lotes más con BRD piloto | 3 | 25h |
| 1 mejora ERP a definir | 2 | 15h |

**Entregable**: codebase más sano + BRD validado en producción HHA.

### Bloque B6 · "Decisión SaaS + observabilidad final" (3 semanas)

| Item | Dim | Esfuerzo |
|---|---|---|
| Endpoint `/metrics` Prometheus + Grafana | 4 | 12h |
| Refinar `/api/admin/health-detailed` con 20+ checks | 4 | 8h |
| **Decisión D4 SaaS post-mes-6** (Fase 6 entra o no) | meta | — |
| 1-2 mejoras ERP a definir | 2 | 20h |

---

## Lo que necesito que me digas

### Q1 · Top 3 dolores de Planta (más urgente)
> Vos dijiste "planta necesita más trabajo". ¿Qué específicamente?
> Ejemplos posibles: visualización del cronograma, asignación de operarios,
> auto-asignación áreas, control de envasado, vista del operario en piso,
> reportes de yield, rotación turnos, integración con BRD, etc.

### Q2 · Qué módulos del ERP necesitan refinamiento prioritario
> Aparte de Planta, ¿qué otros módulos están molestando hoy en HHA?
> Compras, Aseguramiento, Comercial, RRHH, Reportería?

### Q3 · ¿Cuándo querés iniciar piloto BRD real con HHA?
> A · Esta semana (rapidez · acepta bugs)
> B · En 2-3 semanas cuando UI ejecución esté terminada
> C · Después de importar MyBatch (mes 1-2)

### Q4 · ¿Decisión SaaS post-mes 6 o ya te comprometés?
> Si ya querés vender = trabajamos pre-venta en paralelo desde Bloque B3.
> Si esperamos = la dejamos congelada hasta tener 10+ lotes BRD reales.

---

## Lo que recomiendo NO HACER

1. **No abandonar el ERP existente para enfocar todo en BRD.** La gente que lo usa
   todos los días notaría. BRD es ADICIONAL.
2. **No trabajar la deuda solo "cuando sobre tiempo".** Sin Bloque 1 cada
   2 bloques, los monolitos crecen y la app se vuelve insostenible.
3. **No prometer SaaS público antes de mes 9.** Sin Bloque B6 + decisión
   formal, es promesa vacía.
4. **No tocar SQLite → Postgres en 2026.** Aguanta HHA fácil. Postgres es
   problema 2027.
5. **No agregar features sin tests.** Cada bloque debe sumar 2-5 golden paths.

---

## Resumen ejecutivo

| Métrica | Hoy | Meta mes 6 |
|---|---|---|
| Golden paths | 110 | 150+ |
| Módulos sólidos (🟢) | 6 de 12 | 10 de 12 |
| Cobertura tests | ~30% (estimada) | 50%+ |
| LoC monolitos top 4 | 53k | <30k (refactorizado) |
| BRD lotes reales | 0 | 10+ |
| MyBatch activo | sí | apagado o standby |
| DR probado | no | mensual automatizado |
| Off-site backup | no | sí |
| CONTRACT.md | 4 / 27 | 27 / 27 |
| `tenant_id` | 0 ocurrencias | 0 (decisión post-6m) |

**Bandwidth Sebastián**: ~40-50h/mes dev (CEO + médico).
**6 bloques de 3 semanas = 18 semanas = ~4.5 meses** = mediados de octubre.

Total horas estimadas Bloques B1-B6 = ~440-500h.
40-50h/mes × 5 meses = 200-250h. **Necesitamos priorizar fuerte o aceptar
que Fase 6 (pre-venta) queda para 2027.**

---

## Próximo paso concreto

Si me decís Q1-Q3 (Q4 puede esperar), arrancamos **Bloque B1**.

Mientras: el plan completo sigue accesible acá. Lo iremos revisando al
cierre de cada bloque y ajustando según lo que aprendimos.
