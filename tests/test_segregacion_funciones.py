"""Segregación de funciones · quien compra no libera (26-jul).

Al generar el expediente que pidió la Dirección Técnica para autorizar el uso de EOS, el propio
documento detectó que **Catalina (Asistente de Compras) podía liberar materia prima de
cuarentena**. La Resolución 2214/2021 art. 10 asigna esa decisión a Calidad, y el docstring de
`aprobar_lote` ya lo decía: el permiso real contradecía la documentación del propio código.

Sebastián: *"Catalina no libera ya, fue mientras hacíamos pruebas"*. Se sacó.

Este archivo existe porque un permiso temporal de pruebas que nadie retira es exactamente cómo se
llega a una auditoría con un conflicto de segregación vivo desde hace meses. El documento lo
detecta al generarse, pero eso requiere que alguien lo genere; esto lo detecta en cada gate.
"""


def _conf():
    """`config` se importa DENTRO del test, no arriba: pytest importa todos los archivos antes de
    correr el primero, y a esa altura `api/` todavía no está en el path (lo agrega el fixture
    `app`). Por eso los tests piden `app` aunque sólo lean constantes."""
    import config
    return config


def test_quien_compra_no_libera_materia_prima(app):
    """El conflicto que frenaría una autorización: comprar el material y decidir que entra a
    producción son la misma persona."""
    C = _conf()
    compras = set(getattr(C, 'COMPRAS_ACCESS', set())) | set(getattr(C, 'CONTADORA_USERS', set()))
    admin = set(C.ADMIN_USERS)
    libera = (set(C.CALIDAD_USERS) | set(C.ASEGURAMIENTO_USERS) | set(C.TECNICA_USERS)
              | set(C.ADMIN_USERS) | set(getattr(C, 'MP_LIBERA_USERS', set())))
    cruce = sorted((compras & libera) - admin)
    assert not cruce, (
        'estas personas COMPRAN materia prima y además la LIBERAN de cuarentena: %s. '
        'Res. 2214/2021 art. 10 asigna la disposición del lote a Calidad. Si es deliberado, tiene '
        'que ser decisión explícita de la Dirección Técnica y quedar en '
        'EXPEDIENTE_AUTORIZACION_EOS.md.' % ', '.join(cruce))


def test_quien_fabrica_no_libera_el_lote(app):
    """Quien ejecuta el lote no puede aprobar su propio trabajo."""
    C = _conf()
    cruce = sorted((set(C.PLANTA_USERS) & set(C.CALIDAD_USERS)) - set(C.ADMIN_USERS))
    assert not cruce, ('estas personas ejecutan el lote y además pueden liberarlo: %s'
                       % ', '.join(cruce))


def test_ningun_usuario_dado_de_baja_conserva_rol(app):
    """Un empleado retirado que aparece con permisos en la matriz de accesos es una objeción
    segura en una autorización. El login puede estar bloqueado y aun así figurar en los roles,
    que es exactamente lo que pasaba con 'luis'."""
    C = _conf()
    BAJAS = {'luis'}       # dados de baja · mig 375
    roles = set()
    for n in dir(C):
        if n.endswith('_USERS') or n == 'COMPRAS_ACCESS':
            v = getattr(C, n)
            if isinstance(v, (set, frozenset, list, tuple)):
                roles |= set(v)
    quedan = sorted(BAJAS & roles)
    assert not quedan, (
        'personas dadas de baja que siguen en conjuntos de rol: %s. No se borra su usuario ni su '
        'historial (GMP conserva quién hizo qué), pero sí se retira de los roles.'
        % ', '.join(quedan))


def test_el_expediente_existe_y_declara_lo_que_falta():
    """El documento que autoriza el uso NO puede insinuar que el sistema está validado: tener los
    controles implementados y estar validado por un tercero son cosas distintas. Si alguien borra
    esa advertencia, la Dirección Técnica autorizaría sobre una premisa falsa."""
    import io
    import os
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    p = os.path.join(raiz, 'EXPEDIENTE_AUTORIZACION_EOS.md')
    assert os.path.exists(p), 'falta EXPEDIENTE_AUTORIZACION_EOS.md'
    s = io.open(p, encoding='utf-8').read()
    assert 'no cuenta con validación formal' in s, (
        'el expediente ya no declara que falta la validación formal por un tercero')
    for seccion in ('Matriz de accesos', 'Integridad de datos', 'Manual de uso'):
        assert seccion in s, 'al expediente le falta la sección "%s"' % seccion
