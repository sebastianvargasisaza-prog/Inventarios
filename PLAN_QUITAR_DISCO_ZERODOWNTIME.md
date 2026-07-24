# Plan · Quitar el disco persistente → deploys zero-downtime

> Objetivo: eliminar el disco `/var/data` (1 GB) del web service de Render para que
> los deploys sean **zero-downtime**. Hoy, con disco montado, Render apaga la
> instancia vieja antes de arrancar la nueva → **cada deploy tumba la app varios
> minutos** (M91 · la causa real de las "caídas recurrentes").
>
> Regla dura: **NO se puede perder ningún COA** (documentos regulados INVIMA) ni la
> evidencia histórica de backups. Este es un mini-proyecto por FASES, con verificación
> en cada paso. NADA se borra hasta confirmar que la copia nueva existe y se lee bien.

## Qué vive hoy en el disco (inventario verificado)

| Ruta | Contenido | Vínculo con BD | Clasificación |
|---|---|---|---|
| `/var/data/coa/` | COA de proveedor (Compras) · `coa_YYYYMMDD_<uuid>.ext` | ⚠ **NINGUNO** (solo `audit_log`) | CRÍTICO regulado |
| `/var/data/coas/` | COA de laboratorio micro/FQ (Calidad) · `<ref>.pdf` | ✅ `coa_url` en resultados micro/FQ | CRÍTICO regulado |
| `/var/data/backups/` | `pg_dump` `.gz` diarios (14d) + mensuales (~3 años INVIMA) | — | Evidencia · off-site HOY apagado → única copia |
| `/var/data/inventario.db` | SQLite legacy (migración may-2026) | — | Vestigial (backend = PG) |

Dependencias de path ancladas a `DB_PATH` que hay que re-apuntar:
- `COA_STORAGE_DIR` (default `/var/data/coa`) · `compras.py:12446`
- `_coas_dir()` = `dirname(DB_PATH)/coas` · `calidad.py:2787` (NO tiene env var propia)
- `BACKUPS_DIR` = `dirname(DB_PATH)/backups` · `backup.py:42-44`
- ⚠ Fallback efímero a `/tmp/coa` (`compras.py:12451, 12496`): si se quita el disco SIN reubicar, los COA de Compras caen a `/tmp` y **se pierden en cada deploy**. Este es el riesgo #1.

## Decisión previa (negocio · Sebastián): ¿dónde van los COA?

Necesito que elijas el almacenamiento externo. Opciones (todas S3-compatibles, el código
de backups YA soporta `BACKUP_OFFSITE_URL` presigned PUT → reusamos el mismo patrón):

- **Cloudflare R2** (recomendado): sin costo de egress, ~$0.015/GB-mes, S3-compatible. Los COA pesan poco (PDFs), costo casi nulo.
- **Backblaze B2**: muy barato, S3-compatible.
- **AWS S3**: estándar, egress con costo.

Da igual funcionalmente; R2 es el más barato para este uso. Con la cuenta creada me pasás
las credenciales (las cargás vos en el dashboard de Render, yo no las veo).

## Fases (cero pérdida · cada una verificable y reversible)

### Fase 0 · Provisionar almacenamiento (sin tocar prod)
- Crear bucket (ej. `eos-coa`) + credenciales S3. Cargar en Render: `S3_ENDPOINT`,
  `S3_BUCKET`, `S3_KEY`, `S3_SECRET` (sync:false, no van al repo).
- Endpoint diagnóstico read-only `/admin/almacenamiento-check`: escribe un archivo de
  prueba, lo lee, lo borra → confirma que las credenciales y el bucket funcionan ANTES de mover nada.

### Fase 1 · Backups off-site primero (lo más fácil y ya soportado)
- Setear `BACKUP_OFFSITE_URL` (o adaptar `backup.py` al mismo cliente S3) → los backups
  nuevos se replican al bucket automáticamente (`backup.py:69-103` ya lo hace).
- Copiar los `.gz` existentes de `/var/data/backups/` al bucket (endpoint one-time que
  corre EN Render, con acceso al disco). Verificar que los mensuales (evidencia 3 años) están arriba.
- Resultado: la historia de backups deja de depender del disco.

### Fase 2 · COA: inventariar → copiar → cambiar código (el corazón)
1. **Índice de COA de Compras (hoy no existe):** tabla `coa_documentos (id, filename,
   codigo_mp, lote_proveedor, mime, size_kb, subido_por, subido_at, ruta_storage)`.
   Backfill escaneando `/var/data/coa/` + cruzando con `audit_log` (accion='COA_UPLOAD',
   el `despues` trae codigo_mp/lote/size). Así cada archivo queda rastreable ANTES de moverlo.
   Los de Calidad ya están indexados (`coa_url`).
2. **Copiar** todos los archivos de `/var/data/coa/` y `/var/data/coas/` al bucket
   (endpoint one-time en Render con preview + progreso + conteo origen==destino). NO borrar el disco todavía.
3. **Cambiar upload**: `coa-upload` (Compras) y `importar-eml` (Calidad) escriben al bucket
   (PUT), guardando la key en BD. Quitar el fallback a `/tmp` (que enmascara pérdidas).
4. **Cambiar serve**: `coa-download` y `micro/coa/<f>` leen del bucket (stream o redirect a
   presigned GET, manteniendo el gate de rol). **Transición segura**: leer del bucket y, si no
   está, caer al disco → así los archivos viejos siguen sirviéndose durante la ventana.
5. **Verificar**: abrir varios COA de cada almacén desde la app (Compras + Calidad) leyendo del bucket.

### Fase 3 · SQLite legacy
- Subir UNA copia del snapshot de migración (`inventario.db`) al bucket como archivo histórico.
- El endpoint `/api/admin/diagnostico-migracion` (`plan.py:25189`) que lo lee es de un solo uso
  (comparación may-2026) → o se descarga el snapshot on-demand, o se retira el endpoint. No bloquea.

### Fase 4 · Quitar el disco (el momento zero-downtime)
- Solo cuando Fases 1-3 estén verdes: quitar el bloque `disk:` de `render.yaml` (`:41-44`) +
  re-apuntar `DB_PATH`/`BACKUPS_DIR` fuera de `/var/data`.
- Deploy → Render pasa a **zero-downtime** (sin disco, arranca la nueva instancia antes de
  apagar la vieja). Desde acá, los deploys dejan de tumbar la app.
- Verificar: subir un COA nuevo, descargarlo, correr un backup manual, `/api/health` verde.

## Riesgos y mitigaciones
- **COA de Compras sin índice** → se backfillea desde audit_log ANTES de mover (Fase 2.1). Si algún
  archivo no cruza con audit_log, se cataloga igual por su filename (no se pierde).
- **Fallback `/tmp` silencioso** → se elimina en Fase 2.3 (que un COA caiga a `/tmp` es pérdida).
- **Backups única-copia en disco** → Fase 1 los pone off-site ANTES de tocar el disco.
- **Ventana de transición** → los serve leen bucket con fallback a disco hasta confirmar 100%.
- **Reversible**: mientras el disco siga montado (Fases 0-3), todo es aditivo; recién Fase 4 es el cambio duro (y es revertible re-agregando el `disk:`).

## Lo que NO cambia
- Backend = PostgreSQL (ya es la BD real · el `.db` es vestigial).
- Logo y assets (ya en `app_settings`/repo, no en disco).
- Gates de rol de los COA (Compras: compras_user · Calidad: CALIDAD/ASEGURAMIENTO/ADMIN).

## Estado
- [x] Mapa del disco verificado (este documento).
- [ ] Decisión de almacenamiento (Sebastián: R2 / B2 / S3) + credenciales.
- [ ] Fases 0-4 (arrancan cuando haya bucket).
