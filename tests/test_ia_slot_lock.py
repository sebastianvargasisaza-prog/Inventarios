"""Lock '1 IA en vuelo' (anti-saturación de workers · M89/M91). Fail-open y correcto."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))


def test_ia_slot_exclusivo_y_reentrante(app):
    from http_helpers import ia_slot
    with app.app_context():
        from database import get_db
        get_db().execute("INSERT INTO app_settings (clave,valor) VALUES ('ia_en_vuelo','0') "
                         "ON CONFLICT (clave) DO NOTHING")
        get_db().commit()
        with ia_slot() as a:
            assert a is True, 'el primero debe tomar el slot'
            with ia_slot() as b:
                assert b is False, 'el segundo (concurrente) NO debe tomar el slot'
        # tras liberar, se puede volver a tomar
        with ia_slot() as c:
            assert c is True, 'tras liberar, el slot vuelve a estar libre'


def test_ia_slot_libera_ante_excepcion(app):
    """Si el bloque protegido lanza, el slot se libera igual (finally)."""
    from http_helpers import ia_slot
    with app.app_context():
        from database import get_db
        get_db().execute("UPDATE app_settings SET valor='0' WHERE clave='ia_en_vuelo'")
        get_db().commit()
        try:
            with ia_slot() as a:
                assert a is True
                raise RuntimeError('boom')
        except RuntimeError:
            pass
        with ia_slot() as c:
            assert c is True, 'una excepción dentro del slot no debe dejarlo tomado'


def test_ia_slot_release_no_pisa_dueno_ajeno(app):
    """Si otro worker readquirió el slot (tras nuestro TTL), nuestro release NO debe borrar su lock (CAS por token)."""
    from http_helpers import ia_slot
    with app.app_context():
        from database import get_db
        get_db().execute("UPDATE app_settings SET valor='0' WHERE clave='ia_en_vuelo'")
        get_db().commit()
        with ia_slot() as a:
            assert a is True
            # simular que OTRO tomó el slot mientras nosotros lo teníamos (token distinto)
            get_db().execute("UPDATE app_settings SET valor='9999999999' WHERE clave='ia_en_vuelo'")
            get_db().commit()
        v = get_db().execute("SELECT valor FROM app_settings WHERE clave='ia_en_vuelo'").fetchone()[0]
        assert str(v) == '9999999999', 'el release NO debe pisar el lock de otro dueño'
