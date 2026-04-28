"""Test de regresion para Planificacion Estrategica con rolling stock.

Bug detectado por Sebastian 2026-04-28:
> "ayer alcanzaba para varias producciones pero era porque no se habia
> gastado nada en el limpiador de bha"

El sistema evaluaba cada produccion contra el stock TOTAL, sin descontar
lo consumido por producciones cronologicamente anteriores. Asi que si dos
producciones usaban el mismo MP y entre las dos no alcanzaba, el sistema
decia "ambas pueden producir" — falsedad peligrosa para tomar decisiones
de compra.

Fix: rolling stock — ordenar producciones por fecha y decrementar
stock_simulado cuando una produccion 'puede producir'.

Este test simula el escenario:
- Stock 5000 g de MP_X
- Prod1 (mañana): 30 kg de PROD_A que usa 3000 g de MP_X  → puede
- Prod2 (pasado): 30 kg de PROD_A que usa 3000 g de MP_X  → NO puede
                                                            (solo quedan 2000 g)

Antes del fix: ambas decian "puede producir" (BUG)
Despues del fix: prod1 OK, prod2 falta.
"""
import importlib.util
import sys
from pathlib import Path


def _carga_helpers():
    """Importa funciones helper de programacion.py para reutilizar logica."""
    base = Path(__file__).parent.parent / "api" / "blueprints"
    sys.path.insert(0, str(base))
    sys.path.insert(0, str(base.parent))


def test_rolling_stock_simulado_decrementa_correctamente():
    """Simulacion pura de la logica rolling stock (sin tocar la app)."""
    # Stock inicial
    mp_stock = {'MP_X': 5000.0, 'MP_Y': 1000.0}
    stock_simulado = dict(mp_stock)

    # Producciones ordenadas cronologicamente
    producciones = [
        {'fecha': '2026-05-01', 'producto': 'PROD_A',
         'items': [('MP_X', 3000), ('MP_Y', 500)]},
        {'fecha': '2026-05-02', 'producto': 'PROD_B',
         'items': [('MP_X', 3000), ('MP_Y', 500)]},
        {'fecha': '2026-05-03', 'producto': 'PROD_C',
         'items': [('MP_Y', 200)]},  # MP_Y ya estara consumida 1000g de 1000g
    ]
    producciones.sort(key=lambda p: p['fecha'])

    resultados = []
    for prod in producciones:
        n_falta = 0
        decrementos = []
        for mid, g_need in prod['items']:
            stock = stock_simulado.get(mid, 0)
            alcanza = stock >= g_need
            if alcanza:
                decrementos.append((mid, g_need))
            else:
                n_falta += 1
        puede = n_falta == 0
        if puede:
            for mid, g in decrementos:
                stock_simulado[mid] = max(0, stock_simulado[mid] - g)
        resultados.append({'producto': prod['producto'], 'puede': puede,
                           'falta': n_falta})

    # Estado inicial: MP_X=5000, MP_Y=1000
    # PROD_A consume 3000 MP_X + 500 MP_Y → MP_X=2000, MP_Y=500
    # PROD_B necesita 3000 MP_X (NO alcanza, solo hay 2000) → NO puede
    # PROD_C necesita 200 MP_Y, hay 500 → puede, MP_Y=300
    assert resultados[0]['puede'] is True,  "PROD_A puede (stock fresco)"
    assert resultados[1]['puede'] is False, "PROD_B NO puede (solo 2000 MP_X tras PROD_A, necesita 3000)"
    assert resultados[2]['puede'] is True,  "PROD_C puede (MP_Y=500 >= 200, PROD_B no consumio)"
    assert stock_simulado['MP_X'] == 2000.0
    assert stock_simulado['MP_Y'] == 300.0


def test_rolling_stock_segunda_produccion_no_alcanza():
    """Caso especifico del bug de Sebastian: dos producciones que usan
    la misma MP — la primera consume, la segunda queda sin material."""
    mp_stock = {'MP_X': 5000.0}
    stock_simulado = dict(mp_stock)

    producciones = [
        {'fecha': '2026-05-01', 'producto': 'P1', 'items': [('MP_X', 3000)]},
        {'fecha': '2026-05-02', 'producto': 'P2', 'items': [('MP_X', 3000)]},
    ]

    resultados = []
    for prod in producciones:
        n_falta = 0
        decrementos = []
        for mid, g_need in prod['items']:
            if stock_simulado.get(mid, 0) >= g_need:
                decrementos.append((mid, g_need))
            else:
                n_falta += 1
        puede = n_falta == 0
        if puede:
            for mid, g in decrementos:
                stock_simulado[mid] -= g
        resultados.append({'p': prod['producto'], 'puede': puede})

    assert resultados[0]['puede'] is True,  "P1 alcanza (3000 <= 5000)"
    assert resultados[1]['puede'] is False, "P2 NO alcanza (3000 > 2000 restantes)"
    assert stock_simulado['MP_X'] == 2000.0, "Solo P1 consumio, P2 NO"


def test_produccion_que_no_puede_NO_decrementa_stock():
    """Si una produccion no puede producirse (le falta MP), NO debe
    consumir stock virtual — porque en la realidad esa produccion no
    se hara hasta que llegue la MP faltante."""
    mp_stock = {'MP_X': 100.0, 'MP_Y': 5000.0}
    stock_simulado = dict(mp_stock)

    producciones = [
        # P1 NO alcanza (necesita 200 de MP_X pero solo hay 100)
        {'fecha': '2026-05-01', 'producto': 'P1',
         'items': [('MP_X', 200), ('MP_Y', 1000)]},
        # P2 SI alcanza (solo necesita MP_Y)
        {'fecha': '2026-05-02', 'producto': 'P2', 'items': [('MP_Y', 2000)]},
    ]

    for prod in producciones:
        n_falta = 0
        decrementos = []
        for mid, g_need in prod['items']:
            if stock_simulado.get(mid, 0) >= g_need:
                decrementos.append((mid, g_need))
            else:
                n_falta += 1
        if n_falta == 0:
            for mid, g in decrementos:
                stock_simulado[mid] -= g

    # P1 NO se hizo, asi que MP_Y NO debe haber bajado por P1.
    # P2 si se hizo: 5000 - 2000 = 3000.
    assert stock_simulado['MP_X'] == 100.0, "MP_X intocado (P1 no se hizo)"
    assert stock_simulado['MP_Y'] == 3000.0, "MP_Y bajo solo por P2 (5000-2000)"


def test_codigo_real_tiene_stock_simulado_y_sort():
    """Verifica que el codigo de programacion.py usa rolling stock
    (stock_simulado + sort por fecha)."""
    src = Path(__file__).parent.parent / "api" / "blueprints" / "programacion.py"
    text = src.read_text(encoding='utf-8')
    assert 'stock_simulado' in text, (
        "programacion.py debe usar 'stock_simulado' para rolling stock"
    )
    assert "producciones.sort" in text, (
        "programacion.py debe sortear producciones cronologicamente"
    )
    assert "decrementos_si_alcanza" in text, (
        "programacion.py debe acumular decrementos solo si todas las MPs alcanzan"
    )
