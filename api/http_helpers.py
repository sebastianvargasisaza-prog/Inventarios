"""HTTP helpers + money validators reutilizables.

Sebastián 2-may-2026 · audit zero-error.

- fetch_with_retry: retries exponenciales con jitter para integraciones.
- validate_money: sanity check sobre montos antes de persistir.
"""
from __future__ import annotations

import contextlib
import logging
import math
import random
import time
from urllib import error as _urllib_error
from urllib import request as _urllib_request

log = logging.getLogger('http_helpers')


@contextlib.contextmanager
def ia_slot(ttl: int = 110):
    """Lock distribuido '1 IA en vuelo' (anti-saturación de workers Gunicorn · M89/M91).

    Cede `True` si tomó el slot; `False` si ya hay OTRA llamada IA corriendo (el caller debe usar su
    fallback determinista o devolver 'IA ocupada'). Así 2-3 llamadas IA síncronas concurrentes no
    saturan los 3 workers → no 502 app-wide.

    - Conexión INDEPENDIENTE autocommit (`_audit_conn`) → NO interfiere con la transacción del request.
    - CAS sobre `app_settings('ia_en_vuelo')` (clave es PK · `ON CONFLICT` nativo, seguro SQLite+PG).
    - TTL (default 110s < gunicorn --timeout 120): si un holder muere, el slot se libera solo.
    - **Fail-open**: ante CUALQUIER error del lock cede `True` (jamás bloquea la IA por un fallo del lock).
    - Solo libera si REALMENTE adquirió (no pisa el lock de otro cuando fue fail-open).
    """
    acquired = False
    got = False
    token = None
    try:
        from audit_helpers import _audit_conn
        ahora = time.time()
        token = str(ahora)  # identidad del holder · el release solo libera si el slot SIGUE siendo nuestro
        conn = _audit_conn()
        try:
            conn.execute("INSERT INTO app_settings (clave, valor) VALUES ('ia_en_vuelo','0') "
                         "ON CONFLICT (clave) DO NOTHING")
            cur = conn.execute(
                "UPDATE app_settings SET valor=? WHERE clave='ia_en_vuelo' AND "
                "(COALESCE(valor,'0')='0' OR CAST(valor AS REAL) < ?)",
                (token, ahora - ttl))
            acquired = (getattr(cur, 'rowcount', 0) == 1)
            got = acquired
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        log.warning('ia_slot lock falló (fail-open · cede paso): %s', e)
        got = True
        acquired = False
    try:
        yield got
    finally:
        if acquired and token is not None:
            try:
                from audit_helpers import _audit_conn
                c2 = _audit_conn()
                try:
                    # CAS de propiedad: solo libera si el slot SIGUE con nuestro token (si excedimos el TTL
                    # y otro worker ya lo readquirió, NO le pisamos su lock · el suyo lo libera su propio release).
                    c2.execute("UPDATE app_settings SET valor='0' WHERE clave='ia_en_vuelo' AND valor=?", (token,))
                finally:
                    try:
                        c2.close()
                    except Exception:
                        pass
            except Exception as e:
                log.warning('ia_slot release falló (el TTL lo liberará): %s', e)


def fetch_with_retry(req, *, timeout: int = 30, max_intentos: int = 3,
                       backoff_base: float = 1.0, retry_on: tuple = (429, 500, 502, 503, 504)):
    """urlopen con retry exponencial ante 429/5xx + timeout.

    Args:
        req: urllib.request.Request o URL string.
        timeout: timeout por intento en segundos.
        max_intentos: cuántas veces reintenta (incluye el primero).
        backoff_base: segundos para el primer retry (1s · 2s · 4s con base=1).
        retry_on: tuple de status codes que deben reintentar.

    Returns:
        respuesta de urlopen (caller debe .read()).

    Raises:
        urllib.error.HTTPError si el último intento falla con código no-retry.
        urllib.error.URLError si timeout/red en último intento.
    """
    ultimo_error = None
    for intento in range(max_intentos):
        try:
            return _urllib_request.urlopen(req, timeout=timeout)
        except _urllib_error.HTTPError as e:
            ultimo_error = e
            if e.code not in retry_on or intento == max_intentos - 1:
                raise  # no retry-eable o último intento
            wait = backoff_base * (2 ** intento) * (1.0 + random.uniform(-0.25, 0.25))
            log.warning('HTTP %d · retry %d/%d en %.1fs', e.code, intento+1, max_intentos, wait)
            time.sleep(wait)
        except _urllib_error.URLError as e:
            ultimo_error = e
            if intento == max_intentos - 1:
                raise
            wait = backoff_base * (2 ** intento) * (1.0 + random.uniform(-0.25, 0.25))
            log.warning('URLError %s · retry %d/%d en %.1fs', e, intento+1, max_intentos, wait)
            time.sleep(wait)
        except Exception:
            raise  # otro error · no retry
    # Inalcanzable, pero por seguridad
    if ultimo_error:
        raise ultimo_error
    raise RuntimeError('fetch_with_retry: sin intentos válidos')


# ─── Money validators ─────────────────────────────────────────────────────

# Cap razonable para evitar errores absurdos (1 billón COP = 1e12).
# Si alguna OC genuinamente excede esto, ajustar después de revisar uso.
MAX_MONTO_COP = 1_000_000_000_000  # 1B COP


def validate_money(valor, *, allow_zero: bool = False, max_value: float = None,
                    field_name: str = 'monto') -> tuple:
    """Valida un valor monetario · sanity check antes de persistir.

    Antes los endpoints aceptaban NaN/Infinity/negativos/valores absurdos
    en `monto`/`valor_total`. Audit zero-error agregó esta validación.

    Args:
        valor: el valor a validar (puede ser str, int, float, None).
        allow_zero: si False (default), rechaza 0 y negativos.
        max_value: cap superior · default MAX_MONTO_COP.
        field_name: nombre del campo para el error message.

    Returns:
        (valor_float, None) si OK · (None, dict_error) si inválido.
    """
    if max_value is None:
        max_value = MAX_MONTO_COP
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return None, {'error': f'{field_name} debe ser numérico',
                      'codigo': 'MONTO_INVALIDO'}
    if math.isnan(v) or math.isinf(v):
        return None, {'error': f'{field_name} es NaN o Infinity',
                      'codigo': 'MONTO_INVALIDO'}
    if not allow_zero and v <= 0:
        return None, {'error': f'{field_name} debe ser > 0',
                      'codigo': 'MONTO_INVALIDO'}
    if allow_zero and v < 0:
        return None, {'error': f'{field_name} no puede ser negativo',
                      'codigo': 'MONTO_INVALIDO'}
    if v > max_value:
        return None, {'error': f'{field_name}={v:.0f} excede el cap razonable ({max_value:.0f})',
                      'codigo': 'MONTO_FUERA_DE_RANGO'}
    return v, None
