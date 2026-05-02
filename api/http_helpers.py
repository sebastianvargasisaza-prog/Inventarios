"""HTTP helpers reutilizables · retries exponenciales con jitter.

Sebastián 2-may-2026 · audit zero-error · Día 3 ROADMAP.

Antes los call-sites a Shopify/Meta/GHL fallaban inmediato ante 429/5xx,
sin reintentos. Una caída transitoria de 5s rompía el sync. Este helper
reintenta hasta 3 veces con backoff exponencial (1s, 2s, 4s) + jitter
aleatorio ±25%.
"""
from __future__ import annotations

import logging
import random
import time
from urllib import error as _urllib_error
from urllib import request as _urllib_request

log = logging.getLogger('http_helpers')


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
