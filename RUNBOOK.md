# RUNBOOK — Operaciones críticas

Procedimientos para situaciones comunes y de emergencia. Mantener al día.

---

## Deploy normal

1. `git push origin main` → Render auto-deploy detecta el push
2. Render rebuild (~2-3 min) → aplica migraciones automáticamente al startup
3. Verificar en Render dashboard que el deploy quedó "Live"
4. Smoke test: `python scripts/smoke_test.py https://app.eossuite.com`
5. Si smoke test falla → ver "Rollback de emergencia" abajo

---

## Post-deploy del audit zero-error (1-may-2026)

Después del primer deploy con migraciones 81-84:

1. **Verificar que migraciones se aplicaron** (Render shell):
   ```bash
   sqlite3 /var/data/inventario.db "SELECT version, descripcion FROM schema_migrations ORDER BY version DESC LIMIT 5"
   ```
   Debe mostrar versiones 81, 82, 83, 84.

2. **Limpiar producciones con Mayerlin mal-asignada** (1 click desde dashboard):
   ```
   POST /api/planta/reasignar-operarios-conflictos
   ```
   Esto reasigna producciones próximas 14 días que tienen operarios fija_en_dispensacion=1
   en roles ≠ dispensación. Sin esto, las producciones viejas siguen mal hasta el
   próximo `job_self_heal` (7am diario).

3. **Verificar triggers BD activos**:
   ```bash
   sqlite3 /var/data/inventario.db "SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'trg_pp_fija%'"
   ```
   Debe listar 6 triggers (3 UPDATE + 3 INSERT para op_elab/env/acond).

---

## Rollback de emergencia (deploy rompió producción)

### Opción A: Revert al commit anterior (más seguro)
```bash
cd Inventarios/
git revert HEAD --no-edit
git push origin main
```
Render detecta el push y deploya el revert. ~3 minutos.

### Opción B: Rollback en Render UI
1. Ir a https://dashboard.render.com → service `inventarios-0363`
2. Tab "Deploys" → encontrar el último deploy verde
3. Click "Rollback to this deploy"

**IMPORTANTE — migraciones NO se reversan:**
- SQLite no tiene `ALTER TABLE DROP COLUMN` simple
- Las columnas/tablas/triggers nuevos quedan en la BD aunque revertás el código
- Si necesitas forzar rollback de schema: ver "Rollback de migración" abajo

### Rollback de migración específica
SOLO si el problema es una migración mala. Generalmente NO necesario.

```bash
# 1. SSH a Render shell
sqlite3 /var/data/inventario.db

# 2. Borrar trigger problemático (ejemplo: trigger 82 falla)
DROP TRIGGER IF EXISTS trg_pp_fija_elab_block;
DROP TRIGGER IF EXISTS trg_pp_fija_env_block;
DROP TRIGGER IF EXISTS trg_pp_fija_acond_block;
DROP TRIGGER IF EXISTS trg_pp_fija_elab_block_ins;
DROP TRIGGER IF EXISTS trg_pp_fija_env_block_ins;
DROP TRIGGER IF EXISTS trg_pp_fija_acond_block_ins;

# 3. Marcar migración como NO aplicada (forzar re-run en próximo deploy)
DELETE FROM schema_migrations WHERE version = 82;
```

---

## Backups

- Render hace backup automático diario de `/var/data/inventario.db`
- Retención: según plan Render
- Manual backup desde Render shell:
  ```bash
  sqlite3 /var/data/inventario.db ".backup /tmp/backup-$(date +%Y%m%d).db"
  # Luego scp a tu máquina o sube a S3/Drive
  ```

### Restore desde backup
```bash
# 1. Detener app en Render (Settings → Suspend)
# 2. Render shell:
cp /var/data/inventario.db /var/data/inventario.db.broken
cp /path/to/backup.db /var/data/inventario.db
# 3. Reactivar app
```

---

## Variables de entorno críticas (Render)

| Variable | Default | Descripción |
|---|---|---|
| `DB_PATH` | `/var/data/inventario.db` | Ruta SQLite |
| `SECRET_KEY` | (requerida) | Flask session signing |
| `AUTO_PLAN_CRON_KEY` | (opcional) | Token para cron endpoints |
| `HMAC_CRON_REQUIRED` | `0` | `1`=exigir HMAC en cron URLs |
| `MARGEN_PLANEACION_DIAS` | `25` | Margen ideal · floor 20 |
| `SENTRY_DSN` | (opcional) | URL Sentry para alertas |
| `GCAL_ICAL_URL` | (opcional) | iCal feed Calendar |
| `GOOGLE_API_KEY` | (alt) | Calendar API (alternativa a iCal) |
| `APP_BASE_URL` | `https://app.eossuite.com` | URL canónica |

---

## Endpoints de diagnóstico

| Endpoint | Uso |
|---|---|
| `GET /api/health` | Health check público |
| `GET /api/planta/health-check` | Diagnóstico planta (auth requerida) |
| `GET /api/planta/cron-jobs-status` | Estado de cron jobs (último run, errores) |
| `GET /api/planta/diagnostico-calendar` | Estado integración Calendar |
| `POST /api/planta/self-heal` | Forzar ejecución manual de self-heal |
| `POST /api/planta/reasignar-operarios-conflictos` | Limpia operarios mal-asignados |
| `GET /api/planta/validar-hermanos-skus` | Detecta SKUs hermanos con productos distintos |

---

## Errores comunes y solución

### "database is locked" en logs Render
- SQLite con WAL+busy_timeout=5s normalmente lo resuelve
- Si persiste: cron está corriendo y tarda mucho. Ver `cron_jobs_runs` para ver job lento
- Mitigación temporal: reducir frecuencia del cron problemático

### Mayerlin aparece en op_elaboracion (UI muestra rol incorrecto)
- Datos viejos pre-migración 82. Ejecutar `POST /api/planta/reasignar-operarios-conflictos`
- Si ya se ejecutó y reaparece: verificar que trigger 82 está activo:
  ```sql
  SELECT name FROM sqlite_master WHERE type='trigger' AND name='trg_pp_fija_elab_block';
  ```
  Debe retornar 1 fila.

### Cron jobs duplican datos
- Pre-migración 81: race entre workers. Migración 81 introduce `cron_locks` que lo previene.
- Verificar que tabla existe: `SELECT * FROM cron_locks LIMIT 1`
- Si hay lock vencido (>2h): se limpia automáticamente al próximo intento

### "fija_en_dispensacion: este operario solo puede ir a dispensacion" en logs
- Trigger 82 bloqueó un INSERT/UPDATE inválido. **Comportamiento correcto** — alguien intentó violar la regla.
- Investigar el path que disparó el INSERT. Puede ser UI de edición manual, script de migración mal escrito, etc.

### Producciones no se asignan automáticamente
1. Verificar cron habilitado: `SELECT habilitado FROM auto_plan_cron_state WHERE id=1`
2. Verificar último run: `SELECT * FROM cron_jobs_runs ORDER BY id DESC LIMIT 5`
3. Verificar lock no atorado: `SELECT * FROM cron_locks` (si tiene >2h, esperar o `DELETE`)
4. Forzar manualmente: `POST /api/planta/self-heal`

---

## Contactos / Escalación

- **CEO + tech lead**: Sebastián Vargas
- **Co-fundador**: Alejandro
- **Compras**: Catalina
- **Contabilidad**: Mayra
- **Render dashboard**: https://dashboard.render.com
- **GitHub**: https://github.com/sebastianvargasisaza-prog/Inventarios
- **Sentry** (si configurado): https://sentry.io

---

## Cambios mayores recientes

| Fecha | Cambio | Migración |
|---|---|---|
| 2026-05-01 | Audit zero-error: defense-in-depth Mayerlin + race fix cron + UNIQUE numero | 81-84 |
| 2026-04-29 | Auto-plan cron + workflow lunes 7am | 75-80 |
| 2026-04-27 | RBAC abierto: planta operativa multi-rol | varios |
