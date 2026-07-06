"""Sebastián 5-jul · Fase 1 forecast · _factores_estacionales: toggle OFF = sin efecto (todos 1.0);
ON = factor = mult[mes] / mult[mes_actual], capado al tope. (El plan usa esto para adelantar antes de nov.)"""


def test_factores_estacionales_toggle_normalizacion_tope(app, db_clean):
    from database import get_db
    from blueprints.programacion import _factores_estacionales
    with app.app_context():
        conn = get_db()
        for m in range(1, 13):
            conn.execute("UPDATE estacionalidad_meses SET mult_auto=1.0, mult_override=NULL WHERE mes=?", (m,))
        conn.execute("UPDATE estacionalidad_meses SET mult_auto=1.62 WHERE mes=11")   # noviembre Black Friday
        conn.execute("INSERT OR REPLACE INTO app_settings (clave, valor) VALUES ('estacionalidad_plan_activa', '0')")
        conn.execute("INSERT OR REPLACE INTO app_settings (clave, valor) VALUES ('estacionalidad_tope', '2.0')")
        conn.commit()

        # OFF → todos 1.0 (sin efecto)
        f_off = _factores_estacionales(conn)
        assert all(abs(v - 1.0) < 0.001 for v in f_off.values()), ("OFF debe dar todo 1.0", f_off)

        # ON → noviembre > 1 (mes actual mult=1.0 → nov=1.62)
        conn.execute("UPDATE app_settings SET valor='1' WHERE clave='estacionalidad_plan_activa'")
        conn.commit()
        f_on = _factores_estacionales(conn)
        assert 1.5 < f_on[11] <= 2.0, ("ON → nov factor ~1.62 (mes actual 1.0)", f_on[11])

        # TOPE: un mes exagerado se capa
        conn.execute("UPDATE estacionalidad_meses SET mult_auto=5.0 WHERE mes=11")
        conn.commit()
        f_cap = _factores_estacionales(conn)
        assert abs(f_cap[11] - 2.0) < 0.001, ("nov 5.0 debe caparse al tope 2.0", f_cap[11])

        # override de Alejandro gana sobre el auto
        conn.execute("UPDATE estacionalidad_meses SET mult_override=1.0 WHERE mes=11")
        conn.commit()
        f_ovr = _factores_estacionales(conn)
        assert abs(f_ovr[11] - 1.0) < 0.01, ("override 1.0 debe ganar sobre auto 5.0", f_ovr[11])
