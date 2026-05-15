"""
backup.py — Backups automáticos de la base de datos SQLite.

Diseño:
  - Usa sqlite3.Connection.backup() — atómico, NO bloquea writes en curso.
  - Comprime con gzip (DB típica de 10MB → ~2MB en gzip).
  - Guarda en BACKUPS_DIR (variable de entorno o subdirectorio del DB_PATH).
  - Rotación: borra backups con más de RETENTION_DAYS días.
  - Lock multi-worker: vía tabla backup_log con INSERT atómico que reserva
    el slot. Solo 1 worker hace el backup; los otros ven el slot y skip.
  - Trigger oportunista: should_run_backup() chequea si el último completado
    fue hace > BACKUP_INTERVAL_HOURS. Llamado desde before_request en index.py.

Restauración (manual, en caso de desastre):
  1. Descargar el .db.gz más reciente del panel /admin
  2. gunzip inventario_YYYYMMDD_HHMMSS.db.gz
  3. Reemplazar /var/data/inventario.db (Render → Shell)
  4. Reiniciar el servicio
"""
import gzip
import logging
import os
import shutil
import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Sebastián 12-may-2026 Bloque B parcial: helper local UTC-aware para
# reemplazar datetime.utcnow() (deprecado en Python 3.12+).
def _utcnow_naive():
    """Devuelve datetime UTC naive (sin tzinfo) para compat con queries SQLite
    legacy que usan strptime(...,'%Y-%m-%d %H:%M:%S'). Equivalente a la vieja
    datetime.utcnow() pero sin DeprecationWarning."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

from config import DB_PATH

# ── Configuración ────────────────────────────────────────────────────────────
BACKUPS_DIR = os.environ.get(
    "BACKUPS_DIR",
    str(Path(DB_PATH).parent / "backups")
)
# Sebastián 12-may-2026 Bloque E: retención dual para alinear con política
# de records 3 años. INVIMA Res. 3131/1998 + práctica GMP típica = mantener
# evidencia 3+ años post-vencimiento. Hoy:
#   - DAILY: 30 días (1 mes) en disco rápido. Recovery operativo.
#   - MONTHLY: 36 meses (3 años) snapshot mensual marcado con sufijo
#              "__monthly" que NO entra en la rotación diaria. Auditoría.
# El snapshot mensual se hace copiando el primer backup de cada mes natural.
# Sebastián 15-may-2026: corrupción intermitente recurrente del disco
# de Render. Retención horaria 14 días (suficiente para recovery),
# snapshot mensual 3 años para auditoría INVIMA.
RETENTION_DAYS = int(os.environ.get("BACKUP_RETENTION_DAYS", "14"))
MONTHLY_RETENTION_DAYS = int(os.environ.get("BACKUP_MONTHLY_RETENTION_DAYS", "1100"))
# Sebastián 15-may-2026: tras 2da corrupción del disco en un día,
# intervalo bajado de 6h a 1h. 24 backups/día · una corrupción pierde
# 1 hora máximo. Con retention 14 días = ~336 backups (~2-3GB).
BACKUP_INTERVAL_HOURS = int(os.environ.get("BACKUP_INTERVAL_HOURS", "1"))

# Off-site backup opcional · Día 5 ROADMAP zero-error
# Si BACKUP_OFFSITE_URL está configurado (S3/B2/GCS pre-signed PUT URL),
# después de hacer el backup local se hace upload a la URL.
# Formato esperado: URL pre-signed PUT con expiración (ej. S3 presigned).
# La política de generar URLs pre-signed se delega al admin (cron mensual o
# integración con el SDK del provider).
BACKUP_OFFSITE_URL = os.environ.get("BACKUP_OFFSITE_URL", "").strip()
BACKUP_OFFSITE_TIMEOUT = int(os.environ.get("BACKUP_OFFSITE_TIMEOUT", "120"))

_logger = logging.getLogger("inventario.backup")


def _upload_offsite(file_path: str) -> dict:
    """Sube el archivo a BACKUP_OFFSITE_URL vía PUT (S3/B2/GCS presigned).

    Args:
        file_path: ruta del .db.gz local.

    Returns:
        dict {ok, status, size, error}.
    """
    if not BACKUP_OFFSITE_URL:
        return {"ok": False, "skipped": True, "reason": "BACKUP_OFFSITE_URL no configurado"}
    try:
        from urllib import request as _ur
        with open(file_path, "rb") as f:
            data = f.read()
        size = len(data)
        # PUT con presigned URL · S3/B2/GCS aceptan este patrón
        req = _ur.Request(BACKUP_OFFSITE_URL, data=data, method="PUT")
        req.add_header("Content-Type", "application/gzip")
        with _ur.urlopen(req, timeout=BACKUP_OFFSITE_TIMEOUT) as resp:
            status = resp.status
        if 200 <= status < 300:
            _logger.info("offsite_upload_ok size=%d status=%d", size, status)
            return {"ok": True, "status": status, "size": size}
        _logger.warning("offsite_upload status=%d", status)
        return {"ok": False, "status": status}
    except Exception as e:
        _logger.error("offsite_upload_failed: %s", e)
        return {"ok": False, "error": str(e)[:200]}

# Lock para evitar múltiples backups simultáneos en el MISMO worker
# (entre workers, el lock es vía backup_log SQL).
_local_lock = threading.Lock()


def _ensure_backups_dir():
    """Crea el directorio de backups si no existe."""
    Path(BACKUPS_DIR).mkdir(parents=True, exist_ok=True)


def _backup_filename(now=None):
    """Genera nombre de archivo con timestamp UTC."""
    now = now or _utcnow_naive()
    return f"inventario_{now.strftime('%Y%m%d_%H%M%S')}.db.gz"


def _claim_backup_slot(conn, triggered_by="auto"):
    """Intenta reservar un slot de backup en la tabla backup_log.

    Retorna el ID del slot si tuvo éxito (este worker hace el backup), o None
    si otro worker ya está haciendo uno (visto en backup_log con status='running'
    en los últimos 5 minutos).

    Multi-worker safe: el INSERT es atómico, y el chequeo previo evita doble
    trabajo si dos workers entran al mismo tiempo (el segundo ve el row del
    primero recién insertado).
    """
    # ¿Hay otro backup running iniciado hace < 5 min? (worker activo).
    # Formato del timestamp: SQLite datetime('now', 'utc') devuelve
    # 'YYYY-MM-DD HH:MM:SS' (con espacio, no T). Usamos el mismo formato
    # para que la comparación lexicográfica sea correcta.
    stale_threshold = _utcnow_naive() - timedelta(minutes=5)
    row = conn.execute(
        """SELECT id FROM backup_log
           WHERE status='running' AND started_at > ?
           ORDER BY id DESC LIMIT 1""",
        (stale_threshold.strftime("%Y-%m-%d %H:%M:%S"),)
    ).fetchone()
    if row:
        return None
    # Reservar slot
    cur = conn.execute(
        "INSERT INTO backup_log (status, triggered_by) VALUES ('running', ?)",
        (triggered_by,)
    )
    conn.commit()
    return cur.lastrowid


def _close_backup_slot(conn, slot_id, file_path=None, size_bytes=None,
                       status="ok", error=None):
    """Cierra el slot de backup con su resultado."""
    conn.execute(
        """UPDATE backup_log SET
            completed_at = datetime('now', 'utc'),
            file_path    = ?,
            size_bytes   = ?,
            status       = ?,
            error        = ?
           WHERE id = ?""",
        (file_path, size_bytes, status, (error or "")[:500], slot_id)
    )
    conn.commit()


def _do_sqlite_backup_to_gz(target_gz_path):
    """Backup atómico de la DB → archivo .db.gz.

    Usa sqlite3.Connection.backup() que es online (no bloquea writes).
    Pasos:
      1. Copia la DB a un .db temporal usando .backup() (transaccionalmente
         consistente, incluso con writes activos).
      2. Comprime con gzip.
      3. Borra el .db temporal.
      4. Verifica integridad: PRAGMA integrity_check sobre la copia.
    """
    target_dir = Path(target_gz_path).parent
    target_dir.mkdir(parents=True, exist_ok=True)
    tmp_db = str(target_gz_path) + ".tmp.db"

    try:
        # Paso 1: backup atómico a archivo temporal
        src = sqlite3.connect(DB_PATH, timeout=30.0)
        try:
            dst = sqlite3.connect(tmp_db)
            try:
                src.backup(dst)
            finally:
                dst.close()
        finally:
            src.close()

        # Paso 2: verificar integridad de la copia
        verify = sqlite3.connect(tmp_db)
        try:
            result = verify.execute("PRAGMA integrity_check").fetchone()
            if result[0] != "ok":
                raise RuntimeError(f"integrity_check failed: {result[0]}")
        finally:
            verify.close()

        # Paso 3: comprimir
        with open(tmp_db, "rb") as f_in, gzip.open(target_gz_path, "wb",
                                                  compresslevel=6) as f_out:
            shutil.copyfileobj(f_in, f_out, length=64 * 1024)

    finally:
        # Limpieza del .tmp.db incluso si algo falló
        if os.path.exists(tmp_db):
            try:
                os.remove(tmp_db)
            except OSError:
                pass


def _rotate_old_backups():
    """Borra backups expirados aplicando política dual:
    - daily (sin sufijo): borrar si edad > RETENTION_DAYS (30d default).
    - monthly (sufijo __monthly): borrar si edad > MONTHLY_RETENTION_DAYS (1100d / 3 años).
    Retorna cuántos borró.
    """
    now = time.time()
    cutoff_daily = now - (RETENTION_DAYS * 86400)
    cutoff_monthly = now - (MONTHLY_RETENTION_DAYS * 86400)
    deleted = 0
    backups_path = Path(BACKUPS_DIR)
    if not backups_path.exists():
        return 0
    for f in backups_path.glob("inventario_*.db.gz"):
        try:
            mtime = f.stat().st_mtime
            es_monthly = "__monthly" in f.name
            cutoff = cutoff_monthly if es_monthly else cutoff_daily
            if mtime < cutoff:
                f.unlink()
                deleted += 1
        except OSError:
            pass
    return deleted


def _ensure_monthly_snapshot(daily_path):
    """Si todavía no hay snapshot mensual de este mes, copia el daily como monthly.

    Política: el primer backup completado de cada mes natural se preserva 3
    años (1100d) como evidencia regulatoria. Los daily se rotan a 30d.

    Args:
        daily_path: ruta del .db.gz daily recién creado.
    Returns:
        dict {created, monthly_path} o {created: False, reason}.
    """
    try:
        now = _utcnow_naive()
        mes_tag = now.strftime("%Y%m")  # YYYYMM
        backups_path = Path(BACKUPS_DIR)
        # ¿Ya existe snapshot monthly de este mes?
        existing = list(backups_path.glob(f"inventario_{mes_tag}*__monthly.db.gz"))
        if existing:
            return {"created": False, "reason": "monthly snapshot ya existe este mes",
                    "monthly_path": str(existing[0])}
        # Crear copy con sufijo __monthly del archivo daily
        daily_name = Path(daily_path).name  # inventario_YYYYMMDD_HHMMSS.db.gz
        # Reemplazar extensión: .db.gz → __monthly.db.gz
        if daily_name.endswith(".db.gz"):
            monthly_name = daily_name[:-len(".db.gz")] + "__monthly.db.gz"
        else:
            monthly_name = daily_name + "__monthly"
        monthly_path = str(backups_path / monthly_name)
        shutil.copy2(daily_path, monthly_path)
        return {"created": True, "monthly_path": monthly_path}
    except Exception as e:
        _logger.warning("monthly_snapshot_failed: %s", e)
        return {"created": False, "reason": str(e)[:200]}


def do_backup(triggered_by="auto"):
    """Ejecuta un backup completo: claim slot → backup → rotar → close slot.

    Args:
        triggered_by: 'auto' (cron oportunista) o 'manual' (admin click).

    Returns:
        dict con resultado: {ok, file_path, size_bytes, error, skipped}.
    """
    if not _local_lock.acquire(blocking=False):
        return {"ok": False, "skipped": True, "error": "another backup running in this worker"}

    conn = None
    slot_id = None
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10.0)
        slot_id = _claim_backup_slot(conn, triggered_by)
        if slot_id is None:
            return {"ok": False, "skipped": True,
                    "error": "another worker is running a backup"}

        _ensure_backups_dir()
        filename = _backup_filename()
        target = os.path.join(BACKUPS_DIR, filename)

        _do_sqlite_backup_to_gz(target)
        size = os.path.getsize(target)

        # Snapshot mensual (Bloque E · retención 3 años para INVIMA).
        # Si todavía no hay un __monthly de este mes, copia el daily.
        monthly_result = _ensure_monthly_snapshot(target)

        # Upload off-site (best effort · no falla el backup local si offsite falla).
        # Si el monthly se acaba de crear, lo subimos también para tener
        # 3 años de evidencia fuera del disco Render.
        offsite_result = None
        offsite_monthly_result = None
        if BACKUP_OFFSITE_URL:
            offsite_result = _upload_offsite(target)
            if monthly_result.get("created"):
                offsite_monthly_result = _upload_offsite(monthly_result["monthly_path"])

        deleted = _rotate_old_backups()
        _close_backup_slot(conn, slot_id, file_path=target, size_bytes=size,
                           status="ok")
        _logger.info(
            "backup_completed file=%s size=%d rotated=%d trigger=%s offsite=%s monthly=%s",
            filename, size, deleted, triggered_by,
            'ok' if (offsite_result and offsite_result.get('ok')) else
            ('skipped' if not BACKUP_OFFSITE_URL else 'failed'),
            'created' if monthly_result.get('created') else 'skip'
        )
        return {"ok": True, "file_path": target, "filename": filename,
                "size_bytes": size, "rotated": deleted,
                "offsite": offsite_result,
                "monthly": monthly_result,
                "offsite_monthly": offsite_monthly_result}

    except Exception as e:
        _logger.error("backup_failed: %s", e, exc_info=True)
        if conn is not None and slot_id is not None:
            try:
                _close_backup_slot(conn, slot_id, status="error", error=str(e))
            except Exception:
                pass
        return {"ok": False, "error": str(e)[:500]}
    finally:
        if conn is not None:
            conn.close()
        _local_lock.release()


def should_run_backup(conn):
    """Decide si un backup automático debe correr ahora.

    True si el último backup completado (status='ok') fue hace más de
    BACKUP_INTERVAL_HOURS, o si nunca se ha hecho uno.
    """
    try:
        row = conn.execute(
            "SELECT MAX(completed_at) FROM backup_log WHERE status='ok'"
        ).fetchone()
    except Exception:
        # Tabla aún no migrada
        return False

    if not row or not row[0]:
        return True   # nunca se hizo un backup

    # SQLite datetime('now','utc') devuelve "YYYY-MM-DD HH:MM:SS" (sin T).
    # fromisoformat acepta ambos formatos en Python 3.11+; defensivo igual.
    try:
        last = datetime.strptime(row[0][:19], "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return True

    age = _utcnow_naive() - last
    return age > timedelta(hours=BACKUP_INTERVAL_HOURS)


def list_backups():
    """Lista los backups disponibles en disco, más recientes primero."""
    backups_path = Path(BACKUPS_DIR)
    if not backups_path.exists():
        return []
    items = []
    for f in backups_path.glob("inventario_*.db.gz"):
        try:
            st = f.stat()
            items.append({
                "filename": f.name,
                "size_bytes": st.st_size,
                "size_mb": round(st.st_size / 1024 / 1024, 2),
                "modified": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            })
        except OSError:
            pass
    items.sort(key=lambda x: x["filename"], reverse=True)
    return items


def get_backup_path(filename):
    """Resuelve filename → path absoluto, validando que esté en BACKUPS_DIR.

    Retorna None si filename es sospechoso (path traversal) o no existe.
    """
    if "/" in filename or "\\" in filename or ".." in filename:
        return None
    if not filename.startswith("inventario_") or not filename.endswith(".db.gz"):
        return None
    full = os.path.join(BACKUPS_DIR, filename)
    if not os.path.isfile(full):
        return None
    # Resolver y verificar que sigue dentro de BACKUPS_DIR
    real = os.path.realpath(full)
    real_dir = os.path.realpath(BACKUPS_DIR)
    if not real.startswith(real_dir + os.sep):
        return None
    return real


def trigger_backup_async(triggered_by="auto"):
    """Lanza un backup en un thread daemon. No bloquea el caller.

    Usado desde before_request hooks — el backup corre mientras el worker
    sirve el siguiente request.
    """
    t = threading.Thread(
        target=do_backup,
        args=(triggered_by,),
        daemon=True,
        name="backup-worker",
    )
    t.start()
    return t
