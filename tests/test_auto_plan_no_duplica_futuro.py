"""15-jun-2026 · Guard anti-duplicado del auto-plan diario.

Bug (Sebastián "el calendario se llena solo / vuelve a antes"): los triggers de
cadencia y cobertura-mínima de generar_plan NO miraban si el producto YA tenía un
lote futuro agendado → el auto-plan proponía OTRO lote en distinta fecha encima del
plan del usuario. Fix: _futuro_cubre_a_tiempo decide si el lote futuro ya cubre la
necesidad a tiempo (sin causar quiebres: si el stock se agota antes de que ese lote
esté disponible, SÍ se propone).
"""
import os
import sys
import datetime as _dt


def _helper():
    api_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "api")
    if api_dir not in sys.path:
        sys.path.insert(0, api_dir)
    from blueprints.auto_plan import _futuro_cubre_a_tiempo
    return _futuro_cubre_a_tiempo


HOY = _dt.date(2026, 6, 15)


def test_sin_lote_futuro_no_cubre_si_propone():
    f = _helper()
    assert f(None, HOY, 10) is False


def test_sin_velocidad_el_lote_futuro_cubre():
    # dias_inv_actual None = no se vende → no urge → el lote futuro cubre
    f = _helper()
    assert f('2026-08-01', HOY, None) is True


def test_lote_futuro_llega_a_tiempo_no_duplica():
    # stock dura 40d (agota 25-jul) · lote el 1-jul disponible ~8-jul ≤ 25-jul → cubre
    f = _helper()
    assert f('2026-07-01', HOY, 40) is True


def test_lote_futuro_llega_tarde_si_propone():
    # stock dura 10d (agota 25-jun) · lote el 1-jul disponible ~8-jul > 25-jun → NO cubre
    # (debe proponerse uno urgente · no causar quiebre)
    f = _helper()
    assert f('2026-07-01', HOY, 10) is False


def test_borde_pipeline_7d():
    # stock dura justo hasta que el lote esté disponible (prod + 7d == agota) → cubre
    f = _helper()
    # lote 18-jun + 7d = 25-jun ; agota = HOY + 10 = 25-jun → cubre (<=)
    assert f('2026-06-18', HOY, 10) is True
    # lote 19-jun + 7d = 26-jun > 25-jun → NO cubre → propone
    assert f('2026-06-19', HOY, 10) is False


def test_fecha_invalida_no_cubre():
    f = _helper()
    assert f('basura', HOY, 10) is False
