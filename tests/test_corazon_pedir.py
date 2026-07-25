"""PROPIEDAD 4 · "Pedir = el neto del foco, exacto" (Sebastián 11-jun-2026).

⚠ 25-jul · TEST REPARADO (el código está bien). El test leía `deficit[foco]` porque en
junio ESA era la cantidad que el front pedía. Hoy el campo que manda es `neto_a_pedir`:
  · 16-jul (#9 · motores de demanda) `_cantidadSugerida` (dashboard_html.py:23811) pasó a
    `const _src = it.neto_a_pedir || it.deficit;`
  · 22-jul (regla de neteo de Alejandro) el `deficit` quedó BRUTO de lo en camino
    (programacion.py:16287) y lo que descuenta stock + cuarentena + en-camino es
    `neto_a_pedir` (:16291), que además es lo que consume Generar OC (:16485).
La PROPIEDAD no cambió — "jalar exacto para N días, ni de más ni de menos, y un horizonte
cubierto NO arrastra del siguiente" — cambió el campo que la lleva. Se verifica sobre
`neto_a_pedir` y, de paso, que `deficit` sea el bruto.

Verifica empíricamente que /api/abastecimiento/consumo-horizontes devuelve, por MP:

    neto_a_pedir[h] = max(0, consumo[h] - stock - cuarentena - pendiente_compras)
    deficit[h]      = max(0, consumo[h] - stock - cuarentena)

(stock vía _lookup_stock_5tier, pendiente vía SOL/OC en vuelo).

Caso CONTROLADO con números calculados a mano (prefijo QAPEDIR):
  · Fórmula QAPEDIR-A: MP al 10%, lote 1 kg.
  · Fórmula QAPEDIR-B: MP al 30%, lote 1 kg (MISMA MP → demanda compartida).
  · Producción A: +5 días, 10 kg  → 10% × 10kg × 1000 = 1000 g  (entra en TODO horizonte)
  · Producción B: +70 días, 20 kg → 30% × 20kg × 1000 = 6000 g  (entra solo desde 90d; 70>60)
    ⇒ consumo_60 = 1000 g ;  consumo_90 = 7000 g
  · Stock físico  = 2500 g (movimiento Entrada) · cuarentena = 0
  · Cola (SOL Pendiente) = 1500 g
    ⇒ neto_90 = max(0, 7000 - 2500 - 1500) = 3000 g  EXACTO (ni más ni menos)
    ⇒ neto_60 = max(0, 1000 - 2500 - 1500) = 0      (horizonte cubierto → Pedir=0, no se pasa)
    ⇒ deficit_90 = max(0, 7000 - 2500) = 4500 g     (BRUTO de lo en camino)
"""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data
    return c


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        cur = conn.execute(sql, params); conn.commit(); return cur.lastrowid
    finally:
        conn.close()


def _mp(app, codigo):
    c = _login(app)
    r = c.get("/api/abastecimiento/consumo-horizontes?tipo=mp&horizontes=15,30,60,90")
    assert r.status_code == 200, r.data
    for m in r.get_json().get("mps", []):
        if (m.get("codigo") or "").upper() == codigo.upper():
            return m
    return None


def _cantidad_sugerida(it, cubrir_dias):
    """Réplica EXACTA de _cantidadSugerida (dashboard_html.py:23811):
       `const _src = it.neto_a_pedir || it.deficit`, lee _src[String(cubrirDias)],
       redondea, 0 si <=0.01. (El factor `_acelFactor` es 0 con el acelerador apagado,
       que es el default y el estado de este test.)"""
    if not it:
        return 0
    src = it.get("neto_a_pedir") or it.get("deficit")
    if not src:
        return 0
    dh = src.get(str(cubrir_dias))
    return round(dh) if (dh and dh > 0.01) else 0


def test_pedir_es_neto_foco_exacto(app, db_clean):
    cod = "MP-PEDIRZZ"
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
          "VALUES (?, 'Material Pedir ZZ', 'PEDIR INCI ZZ', 1)", (cod,))
    for prod, pct in [("QAPEDIR-A", 10), ("QAPEDIR-B", 30)]:
        _exec("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES (?, 1, 1)", (prod,))
        _exec("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
              "VALUES (?, ?, 'Material Pedir ZZ', ?, 0)", (prod, cod, pct))
    # A en +5 días, 10 kg → entra en todos los horizontes (1000 g)
    _exec("INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado, cantidad_kg, origen) "
          "VALUES ('QAPEDIR-A', date('now','-5 hours','+5 days'), 1, 'pendiente', 10, 'eos_plan')")
    # B en +70 días, 20 kg → entra solo desde 90d (6000 g)
    _exec("INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado, cantidad_kg, origen) "
          "VALUES ('QAPEDIR-B', date('now','-5 hours','+70 days'), 1, 'pendiente', 20, 'eos_plan')")
    # Stock físico: 2500 g (movimiento Entrada con lote real)
    _exec("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, lote, fecha) "
          "VALUES (?, 'Material Pedir ZZ', 2500, 'Entrada', 'QAPEDIR-LOTE-1', date('now','-5 hours'))", (cod,))
    # Cola: SOL Pendiente de 1500 g (sin OC) → cuenta como pendiente_compras
    _exec("INSERT INTO solicitudes_compra (numero, estado, numero_oc) VALUES ('SOL-QAPEDIR', 'Pendiente', '')")
    _exec("INSERT INTO solicitudes_compra_items (numero, codigo_mp, cantidad_g) VALUES ('SOL-QAPEDIR', ?, 1500)", (cod,))

    mp = _mp(app, cod)
    assert mp is not None, "la MP debe aparecer (match producción↔fórmula OK)"

    cons = mp["consumo"]
    defc = mp["deficit"]
    neto = mp["neto_a_pedir"]
    stock = mp["stock_actual_g"]
    cuar = mp.get("cuarentena_g", 0) or 0
    cola = mp["pendiente_compras_g"]

    # --- Premisas del caso (verifican que el setup llegó al endpoint) ---
    assert abs(stock - 2500) < 1, f"stock_actual_g debe ser 2500 · got {stock}"
    assert abs(cuar - 0) < 1, f"sin cuarentena en este caso · got {cuar}"
    assert abs(cola - 1500) < 1, f"pendiente_compras_g debe ser 1500 · got {cola}"
    assert abs(cons["60"] - 1000) < 1, f"consumo_60 = solo A (1000g) · {cons}"
    assert abs(cons["90"] - 7000) < 1, f"consumo_90 = A+B acumulado (7000g) · {cons}"

    disponible = stock + cuar + cola  # = 4000

    # --- PROPIEDAD 4 · neto_a_pedir[90] = max(0, consumo_90 - stock - cuar - cola) EXACTO ---
    esperado_90 = max(0.0, cons["90"] - disponible)  # = 3000
    assert abs(neto["90"] - esperado_90) < 0.5, (
        f"neto_a_pedir_90 debe ser EXACTO {esperado_90} (consumo {cons['90']} - "
        f"disp {disponible}) · got {neto['90']}")
    assert abs(neto["90"] - 3000) < 0.5, f"neto_90 calculado a mano = 3000 · got {neto['90']}"
    # el déficit del mismo horizonte queda BRUTO de lo en camino (regla Alejandro 22-jul)
    assert abs(defc["90"] - 4500) < 0.5, (
        f"deficit_90 = consumo - stock - cuarentena (bruto de en-camino) = 4500 · got {defc['90']}")

    # --- "ni de más ni de menos": el foco lee EXACTAMENTE ese horizonte ---
    # El front pide _cantidadSugerida(it, 90) = round(neto_a_pedir['90']).
    pedir_90 = _cantidad_sugerida(mp, 90)
    assert pedir_90 == 3000, f"Pedir(foco=90) debe jalar EXACTO el neto de 90d (3000) · got {pedir_90}"

    # --- horizonte CUBIERTO no se pasa a uno posterior ---
    # consumo_60 (1000) < disponible (4000) → neto_60 = 0 → Pedir(foco=60)=0,
    # aunque 90 tenga déficit. (regresión del bug "se pasaba a horizonte posterior")
    assert abs(neto["60"] - max(0.0, cons["60"] - disponible)) < 0.5, neto
    assert neto["60"] == 0, f"neto_60 debe ser 0 (cubierto) · got {neto['60']}"
    assert _cantidad_sugerida(mp, 60) == 0, "Pedir(foco=60) NO debe jalar del 90 · debe ser 0"

    # --- consistencia general en TODO horizonte ---
    for h in ("15", "30", "60", "90"):
        assert abs(neto[h] - max(0.0, round(cons[h] - disponible, 1))) < 0.5, (
            f"neto_a_pedir[{h}] debe ser max(0, consumo - stock - cuar - cola) · {neto} {cons}")
        assert abs(defc[h] - max(0.0, round(cons[h] - stock - cuar, 1))) < 0.5, (
            f"deficit[{h}] debe ser max(0, consumo - stock - cuar) · {defc} {cons}")
