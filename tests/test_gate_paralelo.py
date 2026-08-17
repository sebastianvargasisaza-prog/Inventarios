# -*- coding: utf-8 -*-
"""El gate corre en PARALELO y reparte por ARCHIVO · medido el 17-ago-2026.

Sebastián: *"si quiero que resolvamos lo del tiempo para que avancemos más rápido"*.

El gate que corre el hook de pre-push tardaba **924 s** porque lanzaba los 271 archivos del
corazón en un solo proceso. Medido sobre los mismos 2359 tests, los tres verdes:

    serie                                   924 s   15m24
    -n 8  --dist loadfile  (por ARCHIVO)    411 s    6m51   <- 2,25x
    -n 12 --dist load      (por TEST)       508 s    8m28   <- peor, con MÁS workers

Repartir por TEST pierde porque casi todos los archivos del corazón siembran en un test y leen
en otro: cada worker termina re-sembrando lo mismo. `loadfile` manda el archivo entero a un
worker y conserva el orden de adentro.

Este guard existe porque la nota anterior del guardián afirmaba lo contrario ("el corazón no
paralela bien") y esa frase, sin nada que la midiera, es exactamente lo que haría que alguien
volviera a ponerlo en serie.
"""
import os
import re

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARDIAN = os.path.join(RAIZ, "scripts", "guardian.sh")


def _codigo():
    """El guardián SIN sus comentarios.

    ⚠ Sin esto el guard se encuentra a sí mismo: la nota que explica la medición contiene la
    tabla con `-n 12 --dist load`, o sea justo el texto que este test busca prohibir (M154).
    """
    with open(GUARDIAN, encoding="utf-8", errors="replace") as fh:
        lineas = fh.read().splitlines()
    return "\n".join(l for l in lineas if not l.lstrip().startswith("#"))


def test_el_gate_del_hook_corre_en_paralelo():
    """El modo por defecto (el que corre el hook de pre-push) no puede volver a la serie."""
    codigo = _codigo()
    m = re.search(r'PARALELO_CORAZON\s*=\s*"([^"]+)"', codigo)
    assert m, "desapareció PARALELO_CORAZON: el gate volvería a correr en serie"
    assert "-n " in m.group(1), "PARALELO_CORAZON sin cantidad de workers: %r" % m.group(1)
    assert "--dist loadfile" in m.group(1), (
        "el corazón se reparte por ARCHIVO, no por test: repartir por test midió 508 s contra "
        "411 s porque cada worker re-siembra lo mismo · valor actual %r" % m.group(1))
    # y el modo por defecto tiene que USARLO (declararlo y no aplicarlo no acelera nada)
    assert codigo.count('PARALELO="$PARALELO_CORAZON"') >= 2, (
        "el modo por defecto o el --full dejaron de usar PARALELO_CORAZON")


def test_el_modo_postgres_sigue_en_SERIE():
    """En `--pg` los workers comparten UNA sola base y se pisarían entre ellos.

    En SQLite cada worker levanta la suya (`test_workspace` es un mkdtemp por sesión y con
    xdist cada worker es un proceso). En PostgreSQL no: es una base sola, así que ahí el
    paralelo no sale gratis. Este test fija esa asimetría, que es la que hace seguro lo otro.
    """
    codigo = _codigo()
    i = codigo.find('if [ "$MODE" = "--pg" ]')
    assert i > 0, "no se encontró la rama --pg"
    j = codigo.find('elif [ "$MODE" = "--rapido" ]', i)
    assert j > i, "no se encontró el final de la rama --pg"
    rama = codigo[i:j]
    assert "PARALELO=" not in rama, (
        "la rama --pg está seteando paralelo: los workers comparten una sola base de "
        "PostgreSQL y se pisarían entre ellos")


def test_xdist_esta_instalado():
    """Un gate que declara `-n 8` sin xdist no corre: pytest muere con 'unrecognized arguments'
    y el push queda bloqueado sin que el error hable del código."""
    import xdist  # noqa: F401
