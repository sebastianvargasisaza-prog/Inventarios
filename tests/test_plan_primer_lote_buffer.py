"""El PRIMER lote de la cadena sale del stock disponible, no de "hoy" (Sebastián 25-jul).

"Desde lo que hay aún disponible para vender cuánto alcanza · la regla es producir 20 días antes
de que se agote."

Los tres caminos que arman una cadena deben fechar el primer lote igual:
  · modal de Necesidades  → `diasGond - buffer`                        (ya lo hacía)
  · proyección a 2 años   → simula el agotamiento y dispara en buffer  (ya lo hacía)
  · botón "Generar plan"  → arrancaba en HOY para TODOS                (era el desalineado)

El botón le ponía un lote HOY a un producto con meses de góndola. Ahora arranca en
`cobertura − buffer`, con el offset CLAMPEADO a una cadencia para que sea estructuralmente
imposible repetir el bug viejo de "cobertura sobre-estimada manda los lotes a 2027".
"""
import inspect

# ⚠ `blueprints` solo entra al sys.path con el fixture `app` → importar DENTRO de cada test.


def test_el_primer_lote_no_arranca_siempre_en_hoy(app):
    """El offset inicial ya no es 0 fijo: sale de la cobertura menos el buffer."""
    from blueprints.plan import _generar_plan_desde_hoy
    src = inspect.getsource(_generar_plan_desde_hoy)
    assert "off = int(max(0, min(round(_dias_cob - BUFFER_REORDEN_DIAS), cad)))" in src, \
        "el 1er lote debe fecharse por cobertura - buffer"
    assert "\n        off = 0\n" not in src, "no volver al arranque-en-hoy incondicional"


def test_usa_la_misma_metrica_de_timing_que_la_proyeccion(app):
    """Ambos generadores deben fechar con `stock_proyeccion_g` (acotada por el cuello de góndola).

    Si uno usara `stock_g` (el bulk completo, que Abastecimiento usa para la MP) fecharía más
    tarde que el otro y las dos rutas volverían a divergir.
    """
    from blueprints.plan import _generar_plan_desde_hoy
    src = inspect.getsource(_generar_plan_desde_hoy)
    assert "stock_proyeccion_g" in src, "debe usar la métrica de timing, no el bulk"


def test_el_offset_esta_acotado_a_una_cadencia(app):
    """La fórmula clampea a `cad`: ningún producto puede irse lejos por cobertura inflada."""
    from blueprints.plan import BUFFER_REORDEN_DIAS
    def _off(dias_cob, cad):
        return int(max(0, min(round(dias_cob - BUFFER_REORDEN_DIAS), cad)))

    # sin stock → produce ya
    assert _off(0, 60) == 0
    assert _off(15, 60) == 0, "con menos stock que el buffer, produce ya"
    # con stock, espera hasta 'buffer días antes de agotarse'
    assert _off(50, 60) == 30
    assert _off(80, 60) == 60
    # cobertura absurda (el bug de 2027) → tope de una cadencia, nunca más
    assert _off(3000, 60) == 60, "una cobertura inflada NO puede mandar el lote lejos"
    assert _off(3000, 30) == 30


def test_generar_plan_dry_run_no_fecha_nada_en_el_pasado(app):
    """Correr el generador de verdad (dry-run): ninguna fecha puede quedar antes de hoy."""
    from datetime import datetime, timedelta

    from blueprints.plan import _generar_plan_desde_hoy
    from database import get_db
    with app.app_context():
        res = _generar_plan_desde_hoy(get_db(), dias=730, usuario='test', dry_run=True)
    assert isinstance(res, dict), res
    hoy = (datetime.utcnow() - timedelta(hours=5)).date().isoformat()
    for f in (res.get('fechas') or []):
        assert str(f)[:10] >= hoy, 'lote fechado en el pasado: %s' % f
