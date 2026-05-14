"""Timezone Colombia (UTC-5 sin DST) · centralizado.

Sebastián 13-may-2026: "veo errores en la programacion las fechas estan
raras como hacemos para solucionar esas fechas? porque si revisas salta
mucho no tiene consistencia, te pasaba cuando lo extraias de google
calendar".

Causa raíz: Render corre en UTC pero la planta opera en Colombia
(UTC-5 fijo · Colombia no observa DST). Después de las 7pm Colombia,
`date.today()` del server salta al día siguiente y `date('now')` de
SQLite también. Resultado: todos los cálculos de "hoy", "días desde",
"horizonte" se desplazan 1 día según la hora del request.

Solución: forzar UTC-5 en CUALQUIER cálculo de fecha o "ahora" en el
backend, sin importar el TZ del servidor.

Uso:
    from api.tz_colombia import hoy_colombia, now_colombia, SQLITE_DATE_NOW

    hoy = hoy_colombia()
    rows = c.execute(f"SELECT * FROM x WHERE fecha = {SQLITE_DATE_NOW}")
"""
from datetime import datetime, timezone, timedelta, date as _date


# Colombia es UTC-5 fijo (no observa DST desde 1992)
TZ_COLOMBIA = timezone(timedelta(hours=-5))

# Modificadores SQLite para que date('now') / datetime('now') usen
# zona horaria Colombia en lugar de UTC.
SQLITE_DATE_NOW = "date('now', '-5 hours')"
SQLITE_DATETIME_NOW = "datetime('now', '-5 hours')"


def hoy_colombia():
    """Fecha de hoy en zona horaria Colombia.

    Reemplaza date.today() del server (UTC en Render). Devuelve date.
    """
    return datetime.now(TZ_COLOMBIA).date()


def now_colombia():
    """Datetime ahora en zona horaria Colombia · con tzinfo.

    Reemplaza datetime.now() o datetime.utcnow(). Devuelve datetime
    aware (con tzinfo=TZ_COLOMBIA).
    """
    return datetime.now(TZ_COLOMBIA)


def fecha_colombia_iso():
    """Fecha de hoy en Colombia formato YYYY-MM-DD string."""
    return hoy_colombia().isoformat()


def datetime_colombia_iso():
    """Datetime ahora en Colombia formato ISO con offset."""
    return now_colombia().isoformat()
