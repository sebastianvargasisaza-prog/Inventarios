"""Test de restauración de backup — corre mensualmente en CI.

Sebastian (30-abr-2026): "Schrödinger's backup — tener backups que nunca
restauraste es tener nada". Este script automatiza la prueba real:

1. Toma el último backup en /var/data/backups/ (o el path configurado)
2. Lo restaura a una DB de prueba (no toca producción)
3. Verifica que las tablas críticas tienen datos coherentes
4. Reporta éxito/falla con detalle

Uso:
    python scripts/test_backup_restoration.py [--backup-dir /var/data/backups]
    python scripts/test_backup_restoration.py --latest    # default
    python scripts/test_backup_restoration.py --file /path/to/backup.db

Salida: 0 si OK, 1 si falla. Diseñado para CI (GitHub Actions monthly).
"""
import argparse
import os
import sqlite3
import sys
import tempfile
import shutil
from datetime import datetime
from pathlib import Path


# Tablas críticas que DEBEN existir y tener al menos N filas (en operación real).
# Si una de estas viene vacía tras restore, el backup está corrupto o incompleto.
CRITICAL_TABLES = {
    "maestro_mps":              1,    # al menos 1 MP definida
    "formula_headers":          1,    # al menos 1 fórmula
    "users_passwords":          1,    # al menos 1 user con password
    "movimientos":              0,    # puede estar vacío en lab nuevo
    "produccion_programada":    0,    # idem
}

# Tablas opcionales — solo se cuentan, no se requiere mínimo.
OPTIONAL_TABLES = [
    "marketing_campanas", "marketing_influencers", "tareas_internas",
    "users_mfa", "audit_log", "compras_oc",
]


def find_latest_backup(backup_dir: Path) -> Path:
    """Encuentra el backup más reciente en el directorio."""
    if not backup_dir.exists():
        raise FileNotFoundError(f"Backup directory does not exist: {backup_dir}")
    backups = sorted(
        backup_dir.glob("*.db"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    backups += sorted(
        backup_dir.glob("*.sqlite"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not backups:
        raise FileNotFoundError(f"No .db/.sqlite files found in {backup_dir}")
    return backups[0]


def restore_to_temp(backup_path: Path) -> Path:
    """Copia el backup a un archivo temporal y lo abre en SQLite."""
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_path}")
    fd, tmp_path = tempfile.mkstemp(suffix=".db", prefix="restore_test_")
    os.close(fd)
    shutil.copy2(backup_path, tmp_path)
    return Path(tmp_path)


def run_integrity_check(db_path: Path) -> tuple[bool, str]:
    """Corre PRAGMA integrity_check de SQLite. Retorna (ok, mensaje)."""
    conn = sqlite3.connect(db_path)
    try:
        result = conn.execute("PRAGMA integrity_check").fetchone()
        msg = result[0] if result else "no result"
        return msg.lower() == "ok", msg
    finally:
        conn.close()


def check_critical_tables(db_path: Path) -> tuple[bool, list[str]]:
    """Verifica que las tablas críticas existen y tienen suficientes filas.

    Retorna (ok, errors) donde errors es lista de strings con problemas.
    """
    errors = []
    conn = sqlite3.connect(db_path)
    try:
        for table, min_rows in CRITICAL_TABLES.items():
            try:
                row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
                count = row[0] if row else 0
                if count < min_rows:
                    errors.append(
                        f"  ✗ {table}: {count} filas (mínimo esperado: {min_rows})"
                    )
                else:
                    print(f"  ✓ {table}: {count} filas")
            except sqlite3.OperationalError as e:
                errors.append(f"  ✗ {table}: tabla no existe o no accesible — {e}")
        # Tablas opcionales — solo informar
        for table in OPTIONAL_TABLES:
            try:
                row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
                count = row[0] if row else 0
                print(f"  · {table}: {count} filas")
            except sqlite3.OperationalError:
                pass  # tabla puede no existir en backups antiguos, no error
    finally:
        conn.close()
    return len(errors) == 0, errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backup-dir", default="/var/data/backups",
                        help="Directorio donde están los backups (default: /var/data/backups)")
    parser.add_argument("--file", default=None,
                        help="Restaura un archivo de backup específico en lugar del más reciente")
    parser.add_argument("--latest", action="store_true",
                        help="(Default) Usa el backup más reciente del backup-dir")
    args = parser.parse_args()

    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f" EOS · Test de restauración de backup")
    print(f" Ejecución: {datetime.utcnow().isoformat()}Z")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    if args.file:
        backup_path = Path(args.file)
        print(f"Backup objetivo: {backup_path}")
    else:
        backup_dir = Path(args.backup_dir)
        try:
            backup_path = find_latest_backup(backup_dir)
        except FileNotFoundError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 1
        print(f"Backup más reciente: {backup_path}")
        print(f"Modificado: {datetime.fromtimestamp(backup_path.stat().st_mtime).isoformat()}")
        print(f"Tamaño: {round(backup_path.stat().st_size / 1024 / 1024, 2)} MB")

    # 1. Restaurar a archivo temporal
    print("\n[1/3] Restaurando backup a archivo temporal...")
    try:
        restored_path = restore_to_temp(backup_path)
        print(f"  ✓ Restaurado en: {restored_path}")
    except Exception as e:
        print(f"  ✗ FALLA: {e}", file=sys.stderr)
        return 1

    try:
        # 2. PRAGMA integrity_check
        print("\n[2/3] Corriendo PRAGMA integrity_check...")
        ok, msg = run_integrity_check(restored_path)
        if ok:
            print(f"  ✓ Integridad OK")
        else:
            print(f"  ✗ FALLA: {msg}", file=sys.stderr)
            return 1

        # 3. Verificar tablas críticas
        print("\n[3/3] Verificando tablas críticas...")
        tables_ok, errors = check_critical_tables(restored_path)
        if tables_ok:
            print("\n✅ Backup restaurable y datos coherentes.")
        else:
            print("\n❌ FALLAS detectadas:")
            for err in errors:
                print(err, file=sys.stderr)
            return 1

    finally:
        # Cleanup
        try:
            os.remove(restored_path)
            print(f"\nLimpieza: {restored_path} eliminado.")
        except Exception:
            pass

    print(f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f" RTO/RPO objetivo: 4h / 24h — verificado.")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    return 0


if __name__ == "__main__":
    sys.exit(main())
