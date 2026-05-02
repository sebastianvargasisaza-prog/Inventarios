# Manual operacional · Inventarios HHA Group

> Procedimientos para administrar la app `app.eossuite.com` en Render.
> Última actualización: 2-may-2026 · post-ROADMAP_ZERO_ERROR.

## 1. Configuración de variables de entorno (Render Dashboard)

### Críticas (obligatorias)
| Variable | Propósito | Ejemplo |
|---|---|---|
| `DB_PATH` | Path del SQLite | `/var/data/inventario.db` |
| `BACKUPS_DIR` | Directorio de backups locales | `/var/data/backups` |
| `SECRET_KEY` | Firma de sesiones + HMAC capacitaciones | (random ≥48 chars) |
| `PASS_*` | Hash PBKDF2 por usuario | `pbkdf2:sha256:600000$...` |

### Recomendadas (security/observability)
| Variable | Propósito | Cómo obtener |
|---|---|---|
| `SENTRY_DSN` | Captura de errores | Sentry.io > Project Settings |
| `EOS_WEBHOOK_SECRET` | HMAC del webhook EOS leads | Cualquier random ≥32 chars |
| `BACKUP_OFFSITE_URL` | Upload backups a S3/B2/GCS | Presigned PUT URL (cron mensual) |
| `BACKUP_OFFSITE_TIMEOUT` | Timeout offsite en segundos | `120` (default) |
| `FORMULA_PIN` | PIN para desbloquear fórmulas | (no público) |

### Opcionales (integraciones)
| Variable | Sin esto se deshabilita... |
|---|---|
| `ANTHROPIC_API_KEY` | Agencia Ads + análisis IA |
| `GHL_API_KEY` | GoHighLevel sync |
| `SHOPIFY_TOKEN` | Shopify sync (Animus) |
| `INSTAGRAM_TOKEN` | Instagram sync |
| `META_APP_ID` | Meta refresh token |
| `EMAIL_PASSWORD` | Notificaciones por email |

---

## 2. Backups

### Backup local automático
- Se ejecuta cada `BACKUP_INTERVAL_HOURS` horas (default 23h) vía `before_request`.
- Lock multi-worker vía SQL · solo 1 worker hace el backup.
- Retención `BACKUP_RETENTION_DAYS` (default 7d).
- Listar desde `/admin` o `/api/admin/backups`.

### Backup off-site (configurar)
1. Crear bucket en S3/B2/GCS con cifrado at-rest.
2. Generar **presigned PUT URL** con expiración larga (ej. 1 año).
3. Setear en Render: `BACKUP_OFFSITE_URL=https://...`
4. Verificar: el siguiente backup mostrará `offsite=ok` en logs.

### Restauración (desastre)
```bash
# 1. Descargar el .db.gz más reciente desde panel /admin
# 2. Decomprimir
gunzip inventario_YYYYMMDD_HHMMSS.db.gz
# 3. Reemplazar en Render Shell
mv inventario_YYYYMMDD_HHMMSS.db /var/data/inventario.db
# 4. Reiniciar servicio en Render Dashboard
```

---

## 3. Cron jobs

Los cron jobs corren en thread interno · se trigger desde `before_request`.
Schedule en `api/blueprints/auto_plan_jobs.py:JOBS_SCHEDULE`.

| Job | Hora | Frecuencia | Propósito |
|---|---|---|---|
| `lunes_7am_workflow` | 07:00 | Lunes | Workflow planta completo |
| `sync_shopify` | 06:00 | Diaria | Stock PT desde Shopify |
| `auto_asignar_areas` | 06:30 | Diaria | Asignación áreas planta |
| `auto_d20` | 08:00 | Diaria | Compras D20 (≤20% stock) |
| `agua_recordatorio` | 12:00 | L-V | Alerta sistema agua |
| `equipos_vencimientos` | 07:30 | Diaria | Calibraciones T-30/T-7/T-0 |
| `desv_plazos` | 08:00 | Diaria | Desviaciones en plazo vencido |
| `cambios_plazos` | 08:30 | Diaria | Control de cambios atrasados |
| `quejas_plazos` | 09:00 | Diaria | Quejas críticas sin responder |
| `recalls_plazos` | 09:30 | Diaria | Recalls Clase I sin INVIMA |

### Forzar ejecución manual
```bash
# Desde /admin o llamada directa con HMAC
POST /api/cron/run/<job_name>
Headers: X-Cron-Secret: <CRON_SHARED_SECRET>
```

---

## 4. Audit log INVIMA (Resolución 2214/2021)

Todos los endpoints regulatorios escriben a `audit_log`:
- usuario, accion, tabla, registro_id, antes (JSON), despues (JSON), ip, fecha

### Acciones registradas
- `PAGAR_OC`, `AUTORIZAR_OC`, `FACTURA_PAGO`, `FACTURA_ANULAR`
- `COMPLETAR_PRODUCCION` (dispensación)
- `CERRAR_DESVIACION`, `CAMBIO_APROBACION`, `CERRAR_CAMBIO`
- `CERRAR_QUEJA`, `INICIAR_RECALL`, `CERRAR_RECALL`
- `RECALL_CLASIFICAR`, `RECALL_NOTIFICAR_INVIMA`, `RECALL_NOTIFICAR_DIST`
- `CAMBIO_NOTIFICAR_INVIMA`, `CAMBIO_IMPLEMENTAR`
- `SGD_GUARDAR`, `SGD_PDF`, `SGD_FIRMAR_CAP`
- `CREAR_NC`, `CREAR_SPEC_MP`, `CREAR_COA`, `CREAR_OOS`, `REGISTRAR_AGUA`
- `CRONOGRAMA_CUMPLIR`, `CREAR_CAPA_DESV`, `CREAR_HALLAZGO`
- `DESACTIVAR_ALIADO`

### Consultar audit log
```sql
-- Cierre de cierre regulatorio del último mes
SELECT usuario, accion, registro_id, fecha
FROM audit_log
WHERE fecha >= date('now','-30 days')
  AND accion LIKE 'CERRAR_%'
ORDER BY fecha DESC;

-- Quién pagó cuánto últimamente
SELECT usuario, registro_id, despues, fecha
FROM audit_log
WHERE accion='PAGAR_OC'
ORDER BY fecha DESC LIMIT 50;
```

---

## 5. Workflows ASG (módulo /aseguramiento)

### Helpers reutilizables (`api/audit_helpers.py`, `api/http_helpers.py`)
- `audit_log()` · INSERT centralizado a audit_log.
- `intentar_insert_con_retry()` · race-safe ante UNIQUE(codigo).
- `siguiente_codigo_secuencial()` · genera DESV-AAAA-NNNN, OC-AAAA-NNNN, etc.
- `fetch_with_retry()` · HTTP con backoff exponencial 1s/2s/4s + jitter.
- `validate_money()` · sanity check de montos (≤1B COP, no NaN/Infinity).

### Roles de Calidad
- `CALIDAD_USERS` (config.py): laura, miguel, yuliel, alejandro, sebastian.
- `RESPONSABLES_BPM` (compliance.py): set adicional para hallazgos/CAPA.

### Pestañas del módulo
1. Dashboard · KPIs consolidados + alertas críticas
2. Mis tareas · vista personalizada por usuario
3. SGD electrónico · 124 docs centralizados (52 únicos importados pendiente)
4. Capacitaciones · firmar SOPs con HMAC
5. Mis firmas · capacitaciones del usuario actual
6. Desviaciones (ASG-PRO-001) · workflow detectada→cerrada
7. Control de Cambios (ASG-PRO-007) · workflow con notif INVIMA
8. Quejas Cliente (ASG-PRO-013) · workflow con cross-link a desv
9. Recall (ASG-PRO-004) · workflow Clase I/II/III + INVIMA
10. Conflictos SGD · 13 conflictos detectados pendientes de resolución

---

## 6. Recovery procedures

### App caída
1. Revisar Sentry (errores recientes)
2. Revisar Render Dashboard (logs + health)
3. Si DB corrupta → restaurar último backup
4. Si código roto → revertir último deploy en Render

### Sesiones rotas tras deploy
- Causa típica: `SECRET_KEY` no configurada → cada worker genera key efímera distinta.
- Fix: setear `SECRET_KEY` en Render como variable persistente.

### CSRF strict-deny rechaza requests legítimas
- Causa: cliente no envía `Origin` ni `Referer` headers.
- Fix temporal: el cliente debe agregar `Origin: https://app.eossuite.com` al header.
- Si es cron interno: usar el endpoint con HMAC vía `X-Cron-Secret`.

### Rate limit 429 en webhook EOS
- Causa: 5 req/min/IP excedido.
- Fix: el rate limit es por IP · si web3forms cambia de IP el contador se reinicia.

---

## 7. Checklist post-deploy

- [ ] `/api/health` responde 200 con commit hash correcto
- [ ] `/aseguramiento` redirige a `/login` (no autorizado)
- [ ] Login funciona con cualquier user válido
- [ ] Audit log recibe entries (verificar con SELECT recientes)
- [ ] Cron jobs corren a sus horas (revisar logs Render)
- [ ] Backup local se hizo en últimas 23h (`/admin/backups`)
- [ ] Sentry recibe events (sin PII filtrada)
