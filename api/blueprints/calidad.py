# blueprints/calidad.py · extraído de index.py (Fase C)
import os
import json
import logging
import sqlite3
import hmac
import time
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, Response, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from config import DB_PATH, COMPRAS_USERS, ADMIN_USERS, CONTADORA_USERS, CALIDAD_USERS
from database import get_db
from auth import _client_ip, _is_locked, _record_failure, _clear_attempts, _log_sec, sin_acceso_html
from audit_helpers import audit_log, intentar_insert_con_retry, registrar_documento

log = logging.getLogger('calidad')


def _require_calidad():
    """Audit zero-error 2-may-2026 · gating PII + decisiones regulatorias.

    Antes los POSTs de NCs, CAPA, CoA, agua, especificaciones, micro,
    estabilidades NO tenían RBAC: cualquier compras_user creaba/modificaba
    estos registros (operario podía inyectar lecturas falsas de agua,
    CoAs ficticios, etc.).
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    u = session.get('compras_user', '')
    if u not in (set(CALIDAD_USERS) | set(ADMIN_USERS)):
        return jsonify({'error': 'Solo Calidad/Admin pueden mutar registros de Calidad'}), 403
    return None, None


def _validar_e_sign_cal(c, signature_id, *, record_table, record_id, meaning, signer):
    """Valida una e-firma Part 11 (§11.200) sobre un registro de Calidad. La firma debe
    existir en e_signatures, ser del usuario actual, sobre este registro y meaning."""
    if not signature_id:
        return False
    try:
        return c.execute(
            "SELECT id FROM e_signatures WHERE id=? AND record_table=? AND record_id=? "
            "AND meaning=? AND signer_username=?",
            (int(signature_id), record_table, str(record_id), meaning, signer),
        ).fetchone() is not None
    except Exception:
        return False
from templates_py.rrhh_html import RRHH_HTML
from templates_py.compromisos_html import COMPROMISOS_HTML
from templates_py.home_html import HOME_HTML
from templates_py.hub_html import HUB_HTML
from templates_py.clientes_html import CLIENTES_HTML
from templates_py.calidad_html import CALIDAD_HTML
from templates_py.gerencia_html import GERENCIA_HTML
from templates_py.financiero_html import FINANCIERO_HTML
from templates_py.login_html import LOGIN_HTML
from templates_py.compras_html import COMPRAS_HTML
from templates_py.recepcion_html import RECEPCION_HTML
from templates_py.salida_html import SALIDA_HTML
from templates_py.solicitudes_html import SOLICITUDES_HTML
from templates_py.dashboard_html import DASHBOARD_HTML

bp = Blueprint('calidad', __name__)

@bp.route('/calidad')
def calidad_page():
    if 'compras_user' not in session:
        return redirect('/login?next=/calidad')
    u = session.get('compras_user', '')
    # VER la pantalla sale de la matriz de módulos (la única fuente · la usan el menú y el
    # gate global); MUTAR sigue gateado aparte por `_require_calidad` (CALIDAD_USERS), que
    # es justo la separación que config.py declara: cambiar quién VE una pantalla no puede
    # cambiar quién FIRMA. Antes esta página usaba CALIDAD_USERS para las dos cosas, así
    # que el menú le ofrecía Calidad a Miguel, al director técnico, a Catalina y a Luz -que
    # la matriz sí incluye- y al entrar les rebotaba (M32/M97/M161).
    try:
        from config import puede_ver_modulo as _puede_mod
        _permitido = _puede_mod(u, 'calidad')
    except Exception:
        _permitido = u in CALIDAD_USERS
    if not _permitido:
        return Response(sin_acceso_html('Calidad BPM'), mimetype='text/html')
    # Tooltips premium "para qué sirve" (data-tip) · mismo sistema global que el resto de EOS
    html = CALIDAD_HTML
    try:
        from templates_py.ui_help import TOOLTIP_CSS
        html = html.replace('</style>', TOOLTIP_CSS + '\n</style>', 1)
    except Exception:
        pass
    return Response(html, mimetype='text/html')

@bp.route('/api/calidad/dashboard')
def calidad_dashboard():
    conn = get_db(); c = conn.cursor()
    # Lotes en cuarentena · Sebastian 5-may-2026 (audit zero-error):
    # UPPER() para matchear ambos 'Cuarentena' y 'CUARENTENA' que coexisten
    # en DB · antes este KPI mostraba menos lotes de los reales.
    # Fix 28-may · alinear con la bandeja (calidad_bandeja) que cuenta SOLO
    # estado explícito CUARENTENA/_EXTENDIDA · antes el dashboard sumaba además
    # todo lote con estado_lote NULL → inflaba el KPI vs la bandeja.
    c.execute("""SELECT COUNT(*) FROM movimientos
                 WHERE tipo='Entrada'
                   AND UPPER(COALESCE(estado_lote,'')) IN ('CUARENTENA','CUARENTENA_EXTENDIDA')""")
    cuarentena = c.fetchone()[0]
    # Aprobados y rechazados ultimos 30d · H2-F4 (12-jun): contar DECISIONES de QC
    # desde audit_log, no del estado_lote actual. Antes contaba estado_lote='APROBADO'
    # -> tras M23 (aprobar-lote ahora escribe VIGENTE, no APROBADO) el KPI subcontaba
    # (no incluia las liberaciones del panel de recepcion). audit_log captura ambas
    # rutas: APROBAR_LOTE (panel) + CC_REVIEW_APROBADO (cc-review). Robusto: cuenta
    # el evento de aprobacion, no el token transitorio del lote.
    c.execute("""SELECT COUNT(*) FROM audit_log
                 WHERE accion IN ('APROBAR_LOTE','CC_REVIEW_APROBADO')
                   AND fecha >= date('now', '-5 hours', '-30 days')""")
    aprobados = c.fetchone()[0]
    c.execute("""SELECT COUNT(*) FROM audit_log
                 WHERE accion IN ('RECHAZAR_LOTE','CC_REVIEW_RECHAZADO')
                   AND fecha >= date('now', '-5 hours', '-30 days')""")
    rechazados = c.fetchone()[0]
    # NC abiertas
    c.execute("SELECT COUNT(*) FROM no_conformidades WHERE estado='Abierta'")
    nc_abiertas = c.fetchone()[0]
    # Calibraciones vencidas
    hoy = datetime.now().strftime('%Y-%m-%d')
    c.execute("SELECT COUNT(*) FROM calibraciones_instrumentos WHERE fecha_proxima < ? OR estado='Vencida'", (hoy,))
    cals_vencidas = c.fetchone()[0]
    # PT liberados y rechazados ultimos 30d
    c.execute("""SELECT COUNT(*) FROM liberaciones
                 WHERE estado='Liberado'
                 AND fecha_liberacion >= date('now', '-5 hours', '-30 days')""")
    liberados_mes = c.fetchone()[0]
    c.execute("""SELECT COUNT(*) FROM liberaciones
                 WHERE estado='Rechazado'
                 AND fecha_liberacion >= date('now', '-5 hours', '-30 days')""")
    rechazados_pt = c.fetchone()[0]
    total_lib = liberados_mes + rechazados_pt
    tasa_liberacion = round((liberados_mes / total_lib * 100), 1) if total_lib > 0 else None
    # Actividad reciente: últimas NC + últimas acciones CC
    actividad = []
    c.execute("""SELECT 't#C' as tipo, descripcion, area, fecha, estado, impacto
                 FROM no_conformidades ORDER BY id DESC LIMIT 5""")
    for r in c.fetchall():
        color = 'rojo' if r[2] in ('Alto','Critico') else 'amari'
        actividad.append({'titulo': f'NC · {r[1][:55]}',
                          'subtitulo': f'{r[2]} · {r[4]}', 'fecha': r[3], 'color': color})
    c.execute("""SELECT material_nombre, lote, estado_lote, fecha
                 FROM movimientos WHERE tipo='Entrada'
                 AND estado_lote IN ('Aprobado','Rechazado')
                 ORDER BY id DESC LIMIT 5""")
    for r in c.fetchall():
        color = 'verde' if r[2] == 'Aprobado' else 'rojo'
        actividad.append({'titulo': f'Lote {r[1] or "s/n"} · {r[2]}',
                          'subtitulo': r[0][:50], 'fecha': r[3], 'color': color})
    c.execute("""SELECT l.producto, l.lote, l.estado, l.fecha_liberacion, l.aprobado_por, l.cliente
                 FROM liberaciones l
                 WHERE l.estado IN ('Liberado','Rechazado')
                 ORDER BY l.id DESC LIMIT 5""")
    for r in c.fetchall():
        color = 'verde' if r[2] == 'Liberado' else 'rojo'
        cliente_txt = f' -> {r[5]}' if r[5] else ''
        actividad.append({'titulo': f'PT {r[2]} -- {r[0][:40]}',
                          'subtitulo': f'Lote {r[1] or "s/n"} · {r[4] or ""}{cliente_txt}',
                          'fecha': r[3] or '', 'color': color})
    actividad.sort(key=lambda x: x.get('fecha','') or '', reverse=True)
    return jsonify({
        'cuarentena': cuarentena,
        'aprobados': aprobados,
        'rechazados': rechazados,
        'nc_abiertas': nc_abiertas,
        'cals_vencidas': cals_vencidas,
        'liberados_mes': liberados_mes,
        'rechazados_pt': rechazados_pt,
        'tasa_liberacion': tasa_liberacion,
        'actividad_reciente': actividad[:10]
    })

# ════════════════════════════════════════════════════════════════════════
# CUADRO DE MANDO DE INDICADORES DE CALIDAD · Fase 1 (14-jun-2026)
# Cada indicador trae meta/objetivo (de calidad_kpi_metas) + valor actual +
# semáforo verde/amarillo/rojo + tendencia 6 meses (para los de tasa). Le da a
# la jefa de calidad un cuadro de mando con metas claras que cumplir.
# Cálculos 100% cross-DB (sin julianday/strftime; ventanas de mes en Python).
# ════════════════════════════════════════════════════════════════════════

def _semaforo_kpi(valor, meta, umbral, direccion):
    """verde = cumple meta · amarillo = entre meta y umbral · rojo = peor · gris = sin dato."""
    if valor is None or meta is None:
        return 'gris'
    if direccion == 'mayor_mejor':
        if valor >= meta:
            return 'verde'
        if umbral is not None and valor >= umbral:
            return 'amarillo'
        return 'rojo'
    # menor_mejor
    if valor <= meta:
        return 'verde'
    if umbral is not None and valor <= umbral:
        return 'amarillo'
    return 'rojo'


def _meses_ventanas(c, n=6):
    """Devuelve [(label 'YYYY-MM', ini 'YYYY-MM-01', fin_exclusivo 'YYYY-MM-01')] de los
    últimos n meses (más viejo primero), anclado a la fecha de Colombia (M24)."""
    hoy = c.execute("SELECT date('now','-5 hours')").fetchone()[0]  # 'YYYY-MM-DD'
    y, m = int(hoy[0:4]), int(hoy[5:7])

    def win(yy, mm):
        ini = f"{yy:04d}-{mm:02d}-01"
        ny, nm = (yy + 1, 1) if mm == 12 else (yy, mm + 1)
        return ini, f"{ny:04d}-{nm:02d}-01"

    out, yy, mm = [], y, m
    for _ in range(n):
        ini, fin = win(yy, mm)
        out.append((f"{yy:04d}-{mm:02d}", ini, fin))
        mm -= 1
        if mm == 0:
            mm, yy = 12, yy - 1
    out.reverse()
    return hoy, out


def _ratio_pct(num, den):
    return round(num / den * 100, 1) if den else None


@bp.route('/api/calidad/indicadores', methods=['GET'])
def calidad_indicadores():
    """Cuadro de mando: indicadores con meta, valor actual, semáforo y tendencia."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    hoy, meses = _meses_ventanas(c, 6)
    mes_ini, mes_fin = meses[-1][1], meses[-1][2]  # mes actual

    # Memo POR REQUEST del contador (PERF 7-ago · medido con la sonda local).
    #
    # Esta pantalla calcula cada métrica mes a mes sobre 6 meses, y varias comparten ventana: el
    # mes EN CURSO se vuelve a contar hasta 4 veces con la MISMA consulta y los MISMOS parámetros
    # (la serie, el valor del mes actual, la tasa y el conteo de MP liberadas lo piden por
    # separado). Medido: 133 consultas, 40 de ellas repetidas exactas. Sobre PostgreSQL cada una
    # es un viaje de red.
    #
    # ⚠ Es un memo por REQUEST: dentro de un request la BD no cambia, así que el resultado es
    # idéntico al camino lento -- un atajo que puede contestar distinto no es un atajo (M128). Y
    # NO puede ser de módulo: un CoA firmado hace un minuto tiene que verse en la carga siguiente,
    # y este es un indicador regulado (M9).
    _memo_cont = {}

    def cont(sql, params=()):
        _k = (sql, tuple(params or ()))
        if _k in _memo_cont:
            return _memo_cont[_k]
        r = c.execute(sql, params).fetchone()
        _v = (r[0] or 0) if r else 0
        _memo_cont[_k] = _v
        return _v

    # ── Un conteo por MES, con UNA consulta por metrica ───────────────────
    #
    # PERF 8-ago (medido con la sonda local): esta pantalla hacia **133 consultas**. Cada metrica
    # se contaba mes a mes sobre 6 meses, asi que un `COUNT(*)` por metrica se volvia 6-7
    # consultas. Sobre PostgreSQL cada una es un viaje de red: 133 viajes para pintar 8 series.
    #
    # Ahora cada metrica es UNA consulta agrupada por mes (`GROUP BY substr(fecha,1,7)`), leida
    # de un dict. Es el mismo patron con el que se arreglo el heatmap de micro (M86).
    #
    # ⚠ Es EXACTAMENTE equivalente y no una aproximacion: las ventanas de `_meses_ventanas` son
    # meses calendario (`YYYY-MM-01` al 01 del siguiente), asi que agrupar por los 7 primeros
    # caracteres de la fecha da los mismos cubos que comparar `>= ini AND < fin`. La comparacion
    # de rango se conserva igual (misma comparacion de texto), sobre el rango COMPLETO de los 6
    # meses.
    _rango_ini, _rango_fin = meses[0][1], meses[-1][2]
    _memo_mes = {}

    def por_mes(tabla, cond, col_fecha, params=()):
        """{'YYYY-MM': n} con UNA consulta · el mes que no aparece es 0, no un dato faltante."""
        _k = (tabla, cond, col_fecha, tuple(params))
        if _k in _memo_mes:
            return _memo_mes[_k]
        _c = (cond + ' AND ') if cond else ''
        # GROUP BY por EXPRESION: en PG hay que proyectar la expresion, no un alias, y todo lo
        # demas tiene que ser agregado (M160). Aca el SELECT es la expresion + COUNT(*), asi que
        # es correcto en los dos motores.
        _sql = ("SELECT substr(%s,1,7), COUNT(*) FROM %s WHERE %s%s >= ? AND %s < ? "
                "GROUP BY substr(%s,1,7)"
                % (col_fecha, tabla, _c, col_fecha, col_fecha, col_fecha))
        _d = {}
        for _r in c.execute(_sql, tuple(params) + (_rango_ini, _rango_fin)).fetchall():
            if _r[0]:
                _d[_r[0]] = _r[1] or 0
        _memo_mes[_k] = _d
        return _d

    _CAM = "COALESCE(anulado,0)=0"
    _MIC_COL = "COALESCE(fecha_analisis,fecha_muestreo)"
    _MIC = "COALESCE(categoria,'producto')<>'ambiente'"
    _F01 = "COALESCE(anulado,0)=0 AND COALESCE(origen,'MP')='MP'"

    # Flujo ACTUAL = F02 (certificado_analisis_mp) · Sebastián 19-jul: los indicadores estaban
    # ciegos al pipeline F01/F02 (solo miraban el viejo cc-review). Ahora cuentan el F02 + el
    # histórico cc-review.
    _ap_f02 = por_mes('certificado_analisis_mp', "resultado='aprobado' AND " + _CAM, 'creado_en')
    _re_f02 = por_mes('certificado_analisis_mp', "resultado='no_aprobado' AND " + _CAM, 'creado_en')
    _ap_cc = por_mes('audit_log', "accion IN ('APROBAR_LOTE','CC_REVIEW_APROBADO')", 'fecha')
    _re_cc = por_mes('audit_log', "accion IN ('RECHAZAR_LOTE','CC_REVIEW_RECHAZADO')", 'fecha')
    _lib_ok = por_mes('liberaciones', "estado='Liberado'", 'fecha_liberacion')
    _lib_no = por_mes('liberaciones', "estado='Rechazado'", 'fecha_liberacion')
    # Solo producto/MP (el monitoreo ambiental se mide aparte y no debe hundir el KPI).
    _mic_tot = por_mes('calidad_micro_resultados', _MIC, _MIC_COL)
    _mic_fue = por_mes('calidad_micro_resultados', _MIC + " AND estado='fuera_industria'", _MIC_COL)
    _agua_tot = por_mes('calidad_sistema_agua', '', 'fecha')
    _agua_fue = por_mes('calidad_sistema_agua', "estado='fuera_spec'", 'fecha')
    _f01_tot = por_mes('recepcion_tecnica_doc', _F01, 'creado_en')
    _f01_conf = por_mes('recepcion_tecnica_doc', _F01 + " AND resultado='conforme'", 'creado_en')

    def rft_y_rechazo(mes):
        aprob = _ap_f02.get(mes, 0) + _ap_cc.get(mes, 0)
        rech = _re_f02.get(mes, 0) + _re_cc.get(mes, 0)
        tot = aprob + rech
        return _ratio_pct(aprob, tot), _ratio_pct(rech, tot)

    def liberacion_pt(mes):
        lib, rech = _lib_ok.get(mes, 0), _lib_no.get(mes, 0)
        return _ratio_pct(lib, lib + rech)

    def micro_ok(mes):
        tot, fuera = _mic_tot.get(mes, 0), _mic_fue.get(mes, 0)
        return _ratio_pct(tot - fuera, tot)

    def agua_conforme(mes):
        tot, fuera = _agua_tot.get(mes, 0), _agua_fue.get(mes, 0)
        return _ratio_pct(tot - fuera, tot)

    # ── Conteos del flujo de MP (F02 · Sebastián 19-jul) ──────────────────
    def mp_liberadas(mes):
        return _ap_f02.get(mes, 0) + _ap_cc.get(mes, 0)

    def mp_rechazadas(mes):
        return _re_f02.get(mes, 0) + _re_cc.get(mes, 0)

    def f01_documental(mes):
        # % de F01 (recepción técnica) que salieron CONFORMES
        return _ratio_pct(_f01_conf.get(mes, 0), _f01_tot.get(mes, 0))

    series = {'rft_mp': [], 'tasa_rechazo_mp': [], 'liberacion_pt': [], 'micro_ok': [], 'agua_conforme': [],
              'mp_liberadas_mes': [], 'mp_rechazadas_mes': [], 'rft_documental_f01': []}
    for label, ini, fin in meses:
        rft, rech = rft_y_rechazo(label)
        series['rft_mp'].append({'mes': label, 'valor': rft})
        series['tasa_rechazo_mp'].append({'mes': label, 'valor': rech})
        series['liberacion_pt'].append({'mes': label, 'valor': liberacion_pt(label)})
        series['micro_ok'].append({'mes': label, 'valor': micro_ok(label)})
        series['agua_conforme'].append({'mes': label, 'valor': agua_conforme(label)})
        series['mp_liberadas_mes'].append({'mes': label, 'valor': mp_liberadas(label)})
        series['mp_rechazadas_mes'].append({'mes': label, 'valor': mp_rechazadas(label)})
        series['rft_documental_f01'].append({'mes': label, 'valor': f01_documental(label)})

    # ── Valores actuales ──────────────────────────────────────────────────
    # El mes EN CURSO es el ultimo de la serie · antes se volvia a contar con las mismas
    # consultas (4 veces la misma), ahora se lee del mismo dict.
    _mes_label = meses[-1][0]
    rft_now, rech_now = rft_y_rechazo(_mes_label)
    valores = {
        'rft_mp': rft_now,
        'tasa_rechazo_mp': rech_now,
        'liberacion_pt': liberacion_pt(_mes_label),
        'micro_ok': micro_ok(_mes_label),
        'agua_conforme': agua_conforme(_mes_label),
        'mp_liberadas_mes': mp_liberadas(_mes_label),
        'mp_rechazadas_mes': mp_rechazadas(_mes_label),
        'rft_documental_f01': f01_documental(_mes_label),
        'nc_abiertas': cont("SELECT COUNT(*) FROM no_conformidades WHERE estado='Abierta'"),
        'oos_abiertos': cont("SELECT COUNT(*) FROM calidad_oos WHERE LOWER(COALESCE(estado,'')) NOT IN ('cerrado','rechazado','descartado')"),
        'capa_vencidas': cont("SELECT COUNT(*) FROM capa_acciones WHERE estado NOT IN ('Cerrada','Verificada') AND COALESCE(fecha_compromiso,'') <> '' AND fecha_compromiso < ?", (hoy,)),
    }
    # NC: tiempo promedio de cierre (últimos 90d) · en Python para ser cross-DB
    rows = c.execute(
        "SELECT fecha, fecha_cierre FROM no_conformidades WHERE estado='Cerrada' "
        "AND COALESCE(fecha_cierre,'') <> '' AND fecha_cierre >= date('now','-5 hours','-90 days')"
    ).fetchall()
    difs = []
    for r in rows:
        try:
            d0 = datetime.fromisoformat(str(r[0])[:10]); d1 = datetime.fromisoformat(str(r[1])[:10])
            difs.append((d1 - d0).days)
        except Exception:
            pass
    valores['nc_cierre_dias'] = round(sum(difs) / len(difs), 1) if difs else None
    # CAPA cerradas a tiempo (fecha_ejecucion <= fecha_compromiso)
    capa_cerr = cont("SELECT COUNT(*) FROM capa_acciones WHERE estado IN ('Cerrada','Verificada') AND COALESCE(fecha_compromiso,'')<>'' AND COALESCE(fecha_ejecucion,'')<>''")
    capa_ok = cont("SELECT COUNT(*) FROM capa_acciones WHERE estado IN ('Cerrada','Verificada') AND COALESCE(fecha_compromiso,'')<>'' AND COALESCE(fecha_ejecucion,'')<>'' AND fecha_ejecucion <= fecha_compromiso")
    valores['capa_a_tiempo'] = _ratio_pct(capa_ok, capa_cerr)
    # Calibraciones vigentes
    cal_tot = cont("SELECT COUNT(*) FROM calibraciones_instrumentos")
    cal_venc = cont("SELECT COUNT(*) FROM calibraciones_instrumentos WHERE fecha_proxima < ? OR estado='Vencida'", (hoy,))
    valores['calibraciones_vigentes'] = _ratio_pct(cal_tot - cal_venc, cal_tot)
    # ── KPIs nuevos (Sebastián 16-jul · "para presionar") ─────────────────
    # MP en cuarentena AHORA (lotes de MP esperando revisión de Calidad)
    valores['mp_cuarentena'] = cont(
        "SELECT COUNT(*) FROM movimientos m LEFT JOIN maestro_mps mp ON m.material_id=mp.codigo_mp "
        "WHERE UPPER(COALESCE(m.estado_lote,'')) IN ('CUARENTENA','CUARENTENA_EXTENDIDA') AND m.tipo='Entrada' "
        "AND TRIM(COALESCE(m.material_id,'')) <> '' AND UPPER(COALESCE(mp.tipo_material,'MP'))='MP'")
    # Liberaciones HOY (lotes de MP que Calidad aprobó en el día · F02 + histórico cc-review)
    valores['liberacion_dia'] = (
        cont("SELECT COUNT(*) FROM certificado_analisis_mp WHERE resultado='aprobado' AND COALESCE(anulado,0)=0 AND creado_en >= ?", (hoy,))
        + cont("SELECT COUNT(*) FROM audit_log WHERE accion IN ('CC_REVIEW_APROBADO','APROBAR_LOTE') AND fecha >= ?", (hoy,)))
    # Tiempo de liberación: días promedio entre la Entrada del lote y su aprobación (90d · en Python cross-DB).
    # Flujo actual = F02 (certificado_analisis_mp.creado_en vs movimientos.fecha) + histórico cc-review.
    _libs = c.execute(
        "SELECT ca.creado_en, m.fecha FROM certificado_analisis_mp ca JOIN movimientos m ON m.id=ca.mov_id "
        "WHERE ca.resultado='aprobado' AND COALESCE(ca.anulado,0)=0 AND COALESCE(ca.creado_en,'') <> '' "
        "AND ca.creado_en >= date('now','-5 hours','-90 days')").fetchall()
    _libs = list(_libs) + list(c.execute(
        "SELECT cr.fecha, m.fecha FROM cc_reviews cr JOIN movimientos m ON m.id=cr.mov_id "
        "WHERE cr.estado_final='APROBADO' AND COALESCE(cr.fecha,'') <> '' "
        "AND cr.fecha >= date('now','-5 hours','-90 days')").fetchall())
    _dl = []
    for _r in _libs:
        try:
            _d1 = datetime.fromisoformat(str(_r[0])[:10]); _d0 = datetime.fromisoformat(str(_r[1])[:10])
            _dl.append(max(0, (_d1 - _d0).days))
        except Exception:
            pass
    valores['tiempo_liberacion'] = round(sum(_dl) / len(_dl), 1) if _dl else None

    # ── Ensamblar con las metas ───────────────────────────────────────────
    metas = c.execute(
        "SELECT codigo,nombre,descripcion,unidad,direccion,meta,umbral_amarillo,categoria,orden "
        "FROM calidad_kpi_metas WHERE activo=1 ORDER BY orden, nombre"
    ).fetchall()
    indicadores = []
    for m in metas:
        cod = m[0]
        val = valores.get(cod)
        indicadores.append({
            'codigo': cod, 'nombre': m[1], 'descripcion': m[2], 'unidad': m[3],
            'direccion': m[4], 'meta': m[5], 'umbral_amarillo': m[6],
            'categoria': m[7], 'orden': m[8],
            'valor': val,
            'semaforo': _semaforo_kpi(val, m[5], m[6], m[4]),
            'serie': series.get(cod, []),
        })
    resumen = {
        'verde': sum(1 for i in indicadores if i['semaforo'] == 'verde'),
        'amarillo': sum(1 for i in indicadores if i['semaforo'] == 'amarillo'),
        'rojo': sum(1 for i in indicadores if i['semaforo'] == 'rojo'),
        'gris': sum(1 for i in indicadores if i['semaforo'] == 'gris'),
    }
    return jsonify({'indicadores': indicadores, 'resumen': resumen, 'mes_actual': meses[-1][0], 'hoy': hoy})


@bp.route('/api/calidad/indicadores/metas/<codigo>', methods=['PATCH'])
def calidad_indicador_meta_editar(codigo):
    """Edita la meta/umbral de un indicador (solo Calidad/Admin)."""
    err, code = _require_calidad()
    if err:
        return err, code
    body = request.get_json(silent=True) or {}
    conn = get_db(); c = conn.cursor()
    row = c.execute("SELECT meta, umbral_amarillo, activo FROM calidad_kpi_metas WHERE codigo=?", (codigo,)).fetchone()
    if not row:
        return jsonify({'error': f'indicador {codigo} no existe'}), 404
    campos, vals = [], []
    if 'meta' in body:
        campos.append('meta=?'); vals.append(float(body['meta']) if body['meta'] is not None else None)
    if 'umbral_amarillo' in body:
        campos.append('umbral_amarillo=?'); vals.append(float(body['umbral_amarillo']) if body['umbral_amarillo'] is not None else None)
    if 'activo' in body:
        campos.append('activo=?'); vals.append(1 if body['activo'] else 0)
    if not campos:
        return jsonify({'error': 'nada que actualizar'}), 400
    u = session.get('compras_user', '')
    campos.append('actualizado_por=?'); vals.append(u)
    campos.append("actualizado_at=datetime('now')")
    vals.append(codigo)
    audit_log(c, usuario=u, accion='EDITAR_KPI_META', tabla='calidad_kpi_metas',
              registro_id=codigo, antes={'meta': row[0], 'umbral': row[1]}, despues=body)
    c.execute(f"UPDATE calidad_kpi_metas SET {', '.join(campos)} WHERE codigo=?", vals)
    conn.commit()
    return jsonify({'ok': True})


@bp.route('/api/calidad/config/micro-gate', methods=['GET', 'POST'])
def calidad_micro_gate_config():
    """Lee/define el modo del gate de micro para liberar PT (off|strict), guardado en
    app_settings (toggle desde la UI · NO requiere variable de entorno en Render).
    'strict' = no se libera un EBR sin el análisis micro del lote registrado."""
    conn = get_db(); c = conn.cursor()
    try:
        c.execute("""CREATE TABLE IF NOT EXISTS app_settings (
            clave TEXT PRIMARY KEY, valor TEXT NOT NULL, descripcion TEXT,
            actualizado_at_utc TEXT, actualizado_por TEXT, tenant_id INTEGER DEFAULT 1)""")
    except Exception:
        pass
    if request.method == 'POST':
        err, code = _require_calidad()
        if err:
            return err, code
        body = request.get_json(silent=True) or {}
        modo = (body.get('modo') or '').strip().lower()
        if modo not in ('off', 'strict'):
            return jsonify({'error': "modo debe ser 'off' o 'strict'"}), 400
        u = session.get('compras_user', '')
        c.execute(
            "INSERT INTO app_settings (clave,valor,descripcion,actualizado_at_utc,actualizado_por) "
            "VALUES ('micro_gate_mode',?,?,datetime('now'),?) "
            "ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor, "
            "actualizado_at_utc=excluded.actualizado_at_utc, actualizado_por=excluded.actualizado_por",
            (modo, 'Gate de micro presente para liberar PT', u))
        audit_log(c, usuario=u, accion='SET_MICRO_GATE', tabla='app_settings',
                  registro_id='micro_gate_mode', despues={'modo': modo})
        conn.commit()
        return jsonify({'ok': True, 'modo': modo})
    # GET
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    row = c.execute("SELECT valor FROM app_settings WHERE clave='micro_gate_mode' LIMIT 1").fetchone()
    modo = (row[0] if row and row[0] else None)
    fuente = 'db'
    if not modo:
        import os as _os
        modo = _os.environ.get('BRD_MICRO_GATE', 'off').lower(); fuente = 'env'
    return jsonify({'modo': modo, 'fuente': fuente})


# ════════════════════════════════════════════════════════════════════════
# BANDEJA QC DEL DÍA · centro de mando de Calidad
# Sebastián 1-may-2026: "que le resuelva la vida al equipo de Calidad".
# Una sola pantalla con TODO lo pendiente: lotes a liberar, equipos a
# calibrar, NCs/OOS abiertas, cronograma muestreo, registro agua de hoy,
# auditorías próximas. Reemplaza Excel + WhatsApp + 124 docs sueltos.
# ════════════════════════════════════════════════════════════════════════

@bp.route('/api/calidad/bandeja', methods=['GET'])
def calidad_bandeja():
    """Retorna TODO lo pendiente del equipo Calidad en una sola response.

    Secciones:
      - lotes_cuarentena · MP/ME/MEM esperando liberación
      - ncs_abiertas · No Conformidades sin cerrar
      - oos_abiertas · Out of Specification activos
      - calibraciones · vencidas + próximas 7d
      - muestreo_micro_semana · cronograma COC-PRO-011
      - registro_agua_hoy · COC-PRO-008 (null si falta hoy)
      - cola_liberacion · PT esperando liberación QC
      - cola_revisar · cola_liberacion en estado listo_revisar
      - auditorias_proximas · 60 días
      - estabilidades_pendientes · próximas a fecha de análisis

    Auth: cualquier compras_user (lectura abierta).
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    fecha_hoy = datetime.now().date().isoformat()
    log = logging.getLogger('calidad')

    out = {'fecha_hoy': fecha_hoy, 'secciones': {}, 'kpis': {}}

    # ── 1. Lotes en cuarentena (MP/ME/MEM) ─────────────────────────────
    # Audit zero-error 2-may-2026: KPIs reales · COUNT separado del LIMIT.
    # Antes 'total' era len(items) capeado a LIMIT 100 → KPI incorrecto si >100.
    try:
        # Sebastian 5-may-2026 (audit zero-error Recepciones): UPPER() para
        # matchear 'Cuarentena' y 'CUARENTENA' que coexisten en DB.
        kpi_row = c.execute("""
            SELECT COUNT(*),
                   COUNT(CASE WHEN (julianday('now') - julianday(m.fecha)) > 5 THEN 1 END)
            FROM movimientos m
            LEFT JOIN maestro_mps mp ON mp.codigo_mp = m.material_id
            WHERE m.tipo = 'Entrada'
              AND UPPER(COALESCE(m.estado_lote, '')) IN ('CUARENTENA','CUARENTENA_EXTENDIDA')
              AND TRIM(COALESCE(m.material_id,'')) <> ''  -- Sebastián 9-jul: exigir código real · sin código no es MP (basura tipo 'factura junio')
              AND COALESCE(m.observaciones,'') NOT LIKE '%::ANULADA-mov#%'  -- Sebastián 9-jul: no mostrar recepciones YA anuladas (el ✕ crea Salida net-zero pero deja la Entrada)
              AND UPPER(COALESCE(mp.tipo_material,'MP'))='MP'  -- Sebastián 8-jul: MP-only (COC-PRO-001), igual que /api/lotes/cuarentena · los envases (ME/MEM) van por su flujo · antes la bandeja mostraba distinto que la vista CC-review
        """).fetchone()
        rows = c.execute("""
            SELECT m.material_id, m.material_nombre, m.lote, m.proveedor,
                   m.cantidad, m.fecha,
                   CAST((julianday('now') - julianday(m.fecha)) AS INTEGER) as dias_cuarentena,
                   COALESCE(mp.tipo_material, 'MP') as tipo
            FROM movimientos m
            LEFT JOIN maestro_mps mp ON mp.codigo_mp = m.material_id
            WHERE m.tipo = 'Entrada'
              AND UPPER(COALESCE(m.estado_lote, '')) IN ('CUARENTENA','CUARENTENA_EXTENDIDA')
              AND TRIM(COALESCE(m.material_id,'')) <> ''  -- Sebastián 9-jul: exigir código real · sin código no es MP (basura tipo 'factura junio')
              AND COALESCE(m.observaciones,'') NOT LIKE '%::ANULADA-mov#%'  -- Sebastián 9-jul: no mostrar recepciones YA anuladas (el ✕ crea Salida net-zero pero deja la Entrada)
              AND UPPER(COALESCE(mp.tipo_material,'MP'))='MP'  -- Sebastián 8-jul: MP-only (COC-PRO-001), igual que /api/lotes/cuarentena · los envases (ME/MEM) van por su flujo · antes la bandeja mostraba distinto que la vista CC-review
            ORDER BY m.fecha ASC
            LIMIT 20
        """).fetchall()
        items = [{
            'material_id': r[0], 'material_nombre': r[1],
            'lote': r[2], 'proveedor': r[3], 'cantidad': r[4],
            'fecha_recepcion': r[5], 'dias_cuarentena': r[6],
            'tipo': r[7], 'critico': (r[6] or 0) > 5,
        } for r in rows]
        out['secciones']['lotes_cuarentena'] = {
            'total': kpi_row[0] or 0,
            'criticos': kpi_row[1] or 0,
            'items': items,
        }
    except Exception as e:
        log.warning('bandeja lotes_cuarentena fallo: %s', e)
        out['secciones']['lotes_cuarentena'] = {'total': 0, 'criticos': 0, 'items': []}

    # ── 1b. MP/insumos VENCIDOS o por vencer (60d) · del kardex compartido con Planta ──
    # Calidad debe vigilar vencimientos para decisiones de uso/liberación. Mismo patrón
    # que Planta: agrupa por (material_id, lote) con stock>0 y mira fecha_vencimiento.
    try:
        _hoy = c.execute("SELECT date('now','-5 hours')").fetchone()[0]
        rows = c.execute("""
            SELECT m.material_id, MAX(m.material_nombre), m.lote,
                   MIN(m.fecha_vencimiento) AS venc,
                   SUM(CASE WHEN m.tipo IN ('Entrada','entrada','ENTRADA','Ajuste +','Ajuste') THEN m.cantidad
                            WHEN m.tipo IN ('Salida','salida','SALIDA','Ajuste -') THEN -m.cantidad ELSE 0 END) AS stock
            FROM movimientos m
            WHERE COALESCE(m.lote,'') <> '' AND COALESCE(m.fecha_vencimiento,'') <> ''
            GROUP BY m.material_id, m.lote
            HAVING stock > 0.01 AND MIN(m.fecha_vencimiento) <= date('now','-5 hours','+60 days')
            ORDER BY venc ASC LIMIT 60
        """).fetchall()
        items = []
        for r in rows:
            venc = (r[3] or '')[:10]
            try:
                dias = (datetime.fromisoformat(venc) - datetime.fromisoformat(_hoy[:10])).days
            except Exception:
                dias = None
            items.append({
                'material_id': r[0], 'material_nombre': r[1] or r[0], 'lote': r[2],
                'fecha_vencimiento': venc, 'stock_g': round(r[4] or 0, 1),
                'dias': dias, 'vencido': (dias is not None and dias < 0),
            })
        out['secciones']['por_vencer'] = {
            'total': len(items),
            'vencidos': sum(1 for x in items if x['vencido']),
            'items': items,
        }
    except Exception as e:
        log.info('bandeja por_vencer (julianday/fecha): %s', e)
        out['secciones']['por_vencer'] = {'total': 0, 'vencidos': 0, 'items': []}

    # ── 1c. EQUIPOS con calibración vencida / próxima (sistema equipos_planta) ──
    # Distinto de 'calibraciones' (tabla legacy): éste es el maestro de 104 equipos con
    # su último evento. Calidad ve en el centro de mando los instrumentos a calibrar.
    try:
        _hoy_eq = c.execute("SELECT date('now','-5 hours')").fetchone()[0]
        rows = c.execute("""
            SELECT ep.codigo, ep.nombre,
                   (SELECT MAX(ev.fecha_proxima) FROM equipos_eventos ev
                    WHERE ev.equipo_codigo = ep.codigo AND COALESCE(ev.fecha_proxima,'') <> '') AS prox
            FROM equipos_planta ep
            WHERE COALESCE(ep.activo,1) = 1
        """).fetchall()
        eq_items = []
        for r in rows:
            prox = (r[2] or '')[:10]
            if not prox:
                continue
            try:
                dias = (datetime.fromisoformat(prox) - datetime.fromisoformat(_hoy_eq[:10])).days
            except Exception:
                continue
            if dias <= 30:
                eq_items.append({'codigo': r[0], 'nombre': r[1] or r[0], 'fecha_proxima': prox,
                                 'dias': dias, 'vencido': dias < 0})
        eq_items.sort(key=lambda x: x['dias'])
        out['secciones']['equipos_calibracion'] = {
            'total': len(eq_items),
            'vencidos': sum(1 for x in eq_items if x['vencido']),
            'items': eq_items[:30],
        }
    except Exception as e:
        log.info('bandeja equipos_calibracion (tabla puede no existir): %s', e)
        out['secciones']['equipos_calibracion'] = {'total': 0, 'vencidos': 0, 'items': []}

    # ── 2. NCs abiertas ────────────────────────────────────────────────
    try:
        kpi_row = c.execute("""
            SELECT COUNT(*),
                   COUNT(CASE WHEN impacto IN ('Critico','Alto') THEN 1 END)
            FROM no_conformidades WHERE estado = 'Abierta'
        """).fetchone()
        rows = c.execute("""
            SELECT id, fecha, tipo, descripcion, area, responsable, impacto,
                   CAST((julianday('now') - julianday(fecha)) AS INTEGER) as dias_abierta
            FROM no_conformidades
            WHERE estado = 'Abierta'
            ORDER BY CASE impacto
                WHEN 'Critico' THEN 0 WHEN 'Alto' THEN 1
                WHEN 'Medio' THEN 2 ELSE 3 END,
                fecha ASC
            LIMIT 15
        """).fetchall()
        items = [{
            'id': r[0], 'fecha': r[1], 'tipo': r[2],
            'descripcion': (r[3] or '')[:120],
            'area': r[4], 'responsable': r[5], 'impacto': r[6],
            'dias_abierta': r[7], 'urgente': (r[7] or 0) > 30,
        } for r in rows]
        out['secciones']['ncs_abiertas'] = {
            'total': kpi_row[0] or 0,
            'criticas': kpi_row[1] or 0,
            'items': items,
        }
    except Exception as e:
        log.warning('bandeja ncs_abiertas fallo: %s', e)
        out['secciones']['ncs_abiertas'] = {'total': 0, 'criticas': 0, 'items': []}

    # ── 3. OOS abiertas (Out of Specification) ─────────────────────────
    try:
        kpi_oos = c.execute("""
            SELECT COUNT(*) FROM calidad_oos
            WHERE COALESCE(estado, 'abierto') NOT IN ('cerrado', 'descartado')
        """).fetchone()
        _hoy_oos = c.execute("SELECT date('now','-5 hours')").fetchone()[0]
        rows = c.execute("""
            SELECT id, fecha_deteccion, producto, lote, parametro, valor_obtenido,
                   COALESCE(valor_esperado_texto,'') AS especificacion,
                   CASE COALESCE(limite_violado,'') WHEN 'ambos' THEN 'critica'
                        WHEN 'limite_industria' THEN 'alta' ELSE 'media' END AS severidad, estado,
                   CAST((julianday('now') - julianday(fecha_deteccion)) AS INTEGER) as dias_abierta,
                   COALESCE(fecha_objetivo_cierre,'')
            FROM calidad_oos
            WHERE COALESCE(estado, 'abierto') NOT IN ('cerrado', 'descartado')
            ORDER BY fecha_deteccion ASC
            LIMIT 15
        """).fetchall()
        items = []
        sla_vencidos = 0
        for r in rows:
            obj = (r[10] or '')[:10]
            sla_vencido = False
            if obj:
                try:
                    sla_vencido = datetime.fromisoformat(obj) < datetime.fromisoformat(_hoy_oos[:10])
                except Exception:
                    sla_vencido = False
            if sla_vencido:
                sla_vencidos += 1
            items.append({
                'id': r[0], 'fecha': r[1], 'producto': r[2], 'lote': r[3],
                'parametro': r[4], 'valor': r[5], 'spec': r[6],
                'severidad': r[7], 'estado': r[8], 'dias_abierta': r[9],
                'fecha_objetivo_cierre': obj, 'sla_vencido': sla_vencido,
            })
        out['secciones']['oos_abiertas'] = {
            'total': kpi_oos[0] or 0,
            'sla_vencidos': sla_vencidos,
            'items': items,
        }
    except Exception as e:
        log.warning('bandeja oos_abiertas fallo: %s', e)
        try:  # M33 · en PG un error aborta la tx · rollback para no cascadear a las secciones siguientes
            conn.rollback()
        except Exception:
            pass
        out['secciones']['oos_abiertas'] = {'total': 0, 'items': []}

    # ── 4. Calibraciones vencidas + próximas 7d ─────────────────────────
    try:
        rows_venc = c.execute("""
            SELECT id, instrumento, codigo, ubicacion, fecha_proxima, responsable, estado,
                   CAST((julianday('now') - julianday(fecha_proxima)) AS INTEGER) as dias_vencida
            FROM calibraciones_instrumentos
            WHERE date(fecha_proxima) < date('now', '-5 hours')
            ORDER BY fecha_proxima ASC
            LIMIT 30
        """).fetchall()
        rows_prox = c.execute("""
            SELECT id, instrumento, codigo, ubicacion, fecha_proxima, responsable, estado,
                   CAST((julianday(fecha_proxima) - julianday('now')) AS INTEGER) as dias_restantes
            FROM calibraciones_instrumentos
            WHERE date(fecha_proxima) BETWEEN date('now', '-5 hours') AND date('now', '-5 hours', '+7 days')
            ORDER BY fecha_proxima ASC
            LIMIT 30
        """).fetchall()
        out['secciones']['calibraciones'] = {
            'vencidas': [{
                'id': r[0], 'instrumento': r[1], 'codigo': r[2],
                'ubicacion': r[3], 'fecha_proxima': r[4],
                'responsable': r[5], 'dias_vencida': r[7],
            } for r in rows_venc],
            'proximas_7d': [{
                'id': r[0], 'instrumento': r[1], 'codigo': r[2],
                'ubicacion': r[3], 'fecha_proxima': r[4],
                'responsable': r[5], 'dias_restantes': r[7],
            } for r in rows_prox],
            'total_vencidas': len(rows_venc),
            'total_proximas': len(rows_prox),
        }
    except Exception as e:
        log.warning('bandeja calibraciones fallo: %s', e)
        out['secciones']['calibraciones'] = {
            'vencidas': [], 'proximas_7d': [],
            'total_vencidas': 0, 'total_proximas': 0,
        }

    # ── 5. Cronograma muestreo microbiológico semana ────────────────────
    try:
        rows = c.execute("""
            SELECT fecha, area_codigo, area_nombre, tipo_muestra, frecuencia, estado, asignado_a
            FROM cronograma_muestreo_micro
            WHERE date(fecha) BETWEEN date('now', '-5 hours') AND date('now', '-5 hours', '+7 days')
              AND COALESCE(estado, 'pendiente') NOT IN ('completado', 'cancelado')
            ORDER BY fecha ASC, area_codigo
            LIMIT 50
        """).fetchall()
        items = [{
            'fecha': r[0], 'area_codigo': r[1], 'area_nombre': r[2],
            'tipo': r[3], 'frecuencia': r[4], 'estado': r[5],
            'asignado_a': r[6],
        } for r in rows]
        out['secciones']['muestreo_micro_semana'] = {
            'total': len(items), 'items': items,
        }
    except Exception as e:
        # La tabla `cronograma_muestreo_micro` NO EXISTE y nadie la crea: la sección nunca
        # mostró nada y nunca lo iba a hacer. Devolver `total: 0` en silencio hace que Calidad
        # lea "no hay muestreos pendientes esta semana" cuando lo que pasa es que el cronograma
        # no está construido -- un vacío mudo se lee como tranquilidad (M100/M154).
        #
        # Se DECLARA. La sección queda a la vista con su motivo, para que la intención (el
        # muestreo microbiológico ambiental es parte de BPM) no se pierda y se pueda construir
        # cuando se decida, en vez de borrarla y que nadie recuerde que faltaba.
        log.info('bandeja muestreo_micro (cronograma no implementado): %s', e)
        out['secciones']['muestreo_micro_semana'] = {
            'total': 0, 'items': [], 'no_configurado': True,
            'motivo': ('El cronograma de muestreo microbiológico ambiental todavía no está '
                       'construido en EOS · esto NO significa que no haya muestreos pendientes'),
        }

    # ── 6. Registro sistema agua hoy (COC-PRO-008) ──────────────────────
    # Sebastián 1-may-2026: tabla real es calidad_sistema_agua. Antes apuntaba
    # a agua_registros (no existía) · resultaba en alerta perpetua falsa.
    try:
        row = c.execute("""
            SELECT id, fecha, hora, punto_muestreo, tipo_agua, ph,
                   conductividad_us_cm, toc_ppb, microorganismos_ufc_ml,
                   estado, observaciones, operador
            FROM calidad_sistema_agua
            WHERE date(fecha) = date('now', '-5 hours')
            ORDER BY id DESC LIMIT 1
        """).fetchone()
        if row:
            out['secciones']['registro_agua_hoy'] = {
                'registrado': True,
                'id': row[0], 'fecha': row[1], 'hora': row[2],
                'punto_muestreo': row[3], 'tipo_agua': row[4],
                'ph': row[5], 'conductividad': row[6], 'toc': row[7],
                'micro': row[8], 'estado': row[9],
                'observaciones': row[10], 'registrado_por': row[11],
            }
        else:
            out['secciones']['registro_agua_hoy'] = {
                'registrado': False,
                'alerta': '⚠️ Falta registro del sistema de agua hoy',
            }
    except Exception as e:
        log.warning('bandeja calidad_sistema_agua read fallo: %s', e)
        out['secciones']['registro_agua_hoy'] = {
            'registrado': False, 'alerta': 'Error consultando registro de agua',
        }

    # ── 7. Cola liberación PT (esperando QC) ───────────────────────────
    try:
        rows = c.execute("""
            SELECT id, producto_nombre, lote, fecha_envasado, fecha_min_liberacion, estado,
                   CAST((julianday(fecha_min_liberacion) - julianday('now')) AS INTEGER) as dias_para
            FROM cola_liberacion
            WHERE COALESCE(estado, '') NOT IN ('liberado', 'rechazado')
            ORDER BY fecha_min_liberacion ASC
            LIMIT 30
        """).fetchall()
        listo_revisar = [r for r in rows if (r[6] or 0) <= 0]
        items_all = [{
            'id': r[0], 'producto': r[1], 'lote': r[2],
            'fecha_envasado': r[3], 'fecha_min_liberacion': r[4],
            'estado': r[5], 'dias_para': r[6],
            'listo_hoy': (r[6] or 0) <= 0,
        } for r in rows]
        out['secciones']['cola_liberacion'] = {
            'total': len(items_all),
            'listos_revisar_hoy': len(listo_revisar),
            'items': items_all[:20],
        }
    except Exception as e:
        log.info('bandeja cola_liberacion: %s', e)
        out['secciones']['cola_liberacion'] = {
            'total': 0, 'listos_revisar_hoy': 0, 'items': [],
        }

    # ── 8. Auditorías próximas 60d ─────────────────────────────────────
    try:
        # ⚠ Columnas REALES de `auditorias` · pedía `fecha, area, responsable, descripcion` y la
        # tabla tiene `fecha_planeada, ente_auditado, auditor, alcance`. La consulta reventaba
        # SIEMPRE, el `except` lo tragaba y la sección salía vacía -- o sea que Calidad leía
        # "no hay auditorías próximas" cuando nunca se habían consultado (M96/M12a). Lo encontró
        # el barrido de las 411 rutas del 17-ago, por el aviso en el log.
        rows = c.execute("""
            SELECT id, fecha_planeada, tipo, ente_auditado, auditor, alcance, estado
            FROM auditorias
            WHERE date(fecha_planeada) BETWEEN date('now', '-5 hours')
                                           AND date('now', '-5 hours', '+60 days')
              AND COALESCE(estado, 'programada') NOT IN ('completada', 'cancelada')
            ORDER BY fecha_planeada ASC
            LIMIT 20
        """).fetchall()
        items = [{
            'id': r[0], 'fecha': r[1], 'tipo': r[2],
            'area': r[3], 'responsable': r[4],
            'descripcion': (r[5] or '')[:80], 'estado': r[6],
        } for r in rows]
        out['secciones']['auditorias_proximas'] = {
            'total': len(items), 'items': items,
        }
    except Exception as e:
        log.info('bandeja auditorias: %s', e)
        out['secciones']['auditorias_proximas'] = {'total': 0, 'items': []}

    # ── 9. Estabilidades pendientes próximas 30d ───────────────────────
    try:
        rows = c.execute("""
            SELECT id, producto, lote_piloto AS lote, condicion, fecha_inicio,
                   fecha_evaluacion AS fecha_proxima_analisis, estado,
                   CAST((julianday(fecha_evaluacion) - julianday('now')) AS INTEGER) as dias
            FROM estabilidades
            WHERE date(fecha_evaluacion) BETWEEN date('now', '-5 hours') AND date('now', '-5 hours', '+30 days')
              AND UPPER(COALESCE(estado, '')) = 'EN CURSO'
            ORDER BY fecha_evaluacion ASC
            LIMIT 20
        """).fetchall()
        items = [{
            'id': r[0], 'producto': r[1], 'lote': r[2],
            'condicion': r[3], 'fecha_inicio': r[4],
            'fecha_proxima': r[5], 'estado': r[6], 'dias': r[7],
        } for r in rows]
        out['secciones']['estabilidades_pendientes'] = {
            'total': len(items), 'items': items,
        }
    except Exception as e:
        log.info('bandeja estabilidades: %s', e)
        try:  # M33 · rollback para no cascadear a las secciones siguientes en PG
            conn.rollback()
        except Exception:
            pass
        out['secciones']['estabilidades_pendientes'] = {'total': 0, 'items': []}

    # ── 10. EBR completados esperando liberación de PT (Fase 4 · 14-jun) ──
    # Consolida en el centro de mando de Calidad la decisión de liberar/rechazar
    # el Producto Terminado, que hoy vive sólo en /brd. La jefa ve acá los legajos
    # listos y entra a decidir con un clic. Deploy-safe (tabla ausente → vacío).
    try:
        rows = c.execute("""
            SELECT e.id, e.lote, COALESCE(mt.producto_nombre,'') AS producto,
                   e.estado, e.completado_at_utc
            FROM ebr_ejecuciones e
            LEFT JOIN mbr_templates mt ON mt.id = e.mbr_template_id
            WHERE e.estado IN ('completado','en_revision_qc')
            ORDER BY COALESCE(e.completado_at_utc,'') ASC, e.id ASC
            LIMIT 30
        """).fetchall()
        items = [{
            'ebr_id': r[0], 'lote': r[1], 'producto': r[2],
            'estado': r[3], 'completado_at': (r[4] or '')[:10],
            'link': f'/brd/timeline/{r[0]}',
        } for r in rows]
        out['secciones']['ebr_por_liberar'] = {'total': len(items), 'items': items}
    except Exception as e:
        log.info('bandeja ebr_por_liberar (tabla puede no existir): %s', e)
        out['secciones']['ebr_por_liberar'] = {'total': 0, 'items': []}

    # ── 11. CONTROLES EN PROCESO PENDIENTES · la cola propia de Calidad ──
    # Mirando MyBatch con el usuario de Laura (jefe de control de calidad, 15-ago-2026):
    # su tablero NO es el del planeador. Tiene una cola cruzada -"Controles en Proceso
    # de Fabricación Pendientes"- con los controles de TODOS los lotes abiertos en una
    # sola lista, cada uno con su especificación al lado.
    #
    # En EOS los controles viven dentro del legajo, así que para saber qué le falta
    # registrar había que abrir lote por lote: la información estaba, el TRABAJO de
    # Calidad no tenía pantalla (M121). Esta sección es esa pantalla.
    #
    # Va en UNA consulta para toda la cola (no una por lote · M43), y el catálogo de
    # controles depende de la FASE del legajo, igual que en el runner.
    try:
        from blueprints.brd import _ipc_estandar_de_fase
        rows = c.execute("""
            SELECT e.id, e.lote, COALESCE(mt.producto_nombre,''),
                   COALESCE(e.fase,'fabricacion'), COALESCE(e.estado,''),
                   COALESCE(e.iniciado_at_utc,'')
            FROM ebr_ejecuciones e
            LEFT JOIN mbr_templates mt ON mt.id = e.mbr_template_id
            WHERE e.estado IN ('iniciado','en_proceso','completado','en_revision_qc')
            ORDER BY COALESCE(e.iniciado_at_utc,'') ASC, e.id ASC
            LIMIT 300
        """).fetchall()
        _ids = [r[0] for r in rows]
        _reg = {}
        if _ids:
            _ph = ','.join('?' for _ in _ids)
            for rr in c.execute(
                "SELECT ebr_id, control_codigo, conforme FROM ipc_estandar_resultados "
                "WHERE ebr_id IN (%s)" % _ph, _ids).fetchall():
                _reg[(rr[0], rr[1])] = rr[2]
        items = []
        # La conexión va SIEMPRE: sin ella este resolvedor responde la lista de fábrica,
        # así que la cola de Calidad pediría controles distintos a los que el legajo
        # muestra si el director técnico configuró la fase. Dos pantallas contando
        # historias distintas del mismo hecho es lo que hace que se deje de creer en las
        # dos (M161). El catálogo por fase se resuelve una vez, no una por legajo (M43).
        _cat_fase = {}
        for r in rows:
            _f = r[3] or 'fabricacion'
            if _f not in _cat_fase:
                _cat_fase[_f] = _ipc_estandar_de_fase(_f, c)
            for cod, nom, uni in _cat_fase[_f]:
                # 'registrado' = adjudicado por Calidad (conforme 0/1) o marcado
                # 'No aplica' (2). Un valor anotado sin adjudicar sigue PENDIENTE:
                # falta la firma de quien decide.
                if _reg.get((r[0], cod)) in (0, 1, 2):
                    continue
                items.append({
                    'ebr_id': r[0], 'lote': r[1], 'producto': r[2], 'fase': r[3],
                    'estado_lote': r[4], 'control_codigo': cod, 'control': nom,
                    'unidad': uni, 'link': '/brd/timeline/%s' % r[0],
                })
        _lotes = len({i['ebr_id'] for i in items})
        # El TOTAL tiene que contar todos los legajos abiertos, no los que entraron en
        # la ventana: un total calculado sobre un recorte es un total falso, y este
        # número alimenta el KPI de Calidad (M155). El techo de 300 legajos está muy
        # por encima de lo real (hoy son decenas) y, si alguna vez se toca, se DICE.
        try:
            _abiertos = c.execute(
                "SELECT COUNT(*) FROM ebr_ejecuciones WHERE estado IN "
                "('iniciado','en_proceso','completado','en_revision_qc')").fetchone()[0]
        except Exception:
            _abiertos = len(rows)
        out['secciones']['controles_pendientes'] = {
            'total': len(items), 'lotes': _lotes, 'items': items[:60],
            # Si la LISTA se recorta, se dice: "60" leído como el total manda a cerrar
            # una cola que en realidad es más larga.
            'recortado': max(0, len(items) - 60),
            # Y si quedaron legajos sin mirar, el total tampoco es el total: se declara
            # en vez de dejar creer que se contó todo (M100).
            'lotes_abiertos': int(_abiertos or 0),
            'lotes_sin_mirar': max(0, int(_abiertos or 0) - len(rows)),
        }
    except Exception as e:
        log.info('bandeja controles_pendientes: %s', e)
        out['secciones']['controles_pendientes'] = {'total': 0, 'lotes': 0, 'items': [],
                                                    'recortado': 0, 'lotes_abiertos': 0,
                                                    'lotes_sin_mirar': 0}

    # ── KPIs unificados ─────────────────────────────────────────────────
    out['kpis'] = {
        'controles_pendientes': out['secciones']['controles_pendientes']['total'],
        'lotes_cuarentena': out['secciones']['lotes_cuarentena']['total'],
        'lotes_cuarentena_criticos': out['secciones']['lotes_cuarentena']['criticos'],
        'ncs_abiertas': out['secciones']['ncs_abiertas']['total'],
        'oos_abiertas': out['secciones']['oos_abiertas']['total'],
        'calibraciones_vencidas': out['secciones']['calibraciones']['total_vencidas'],
        'calibraciones_proximas': out['secciones']['calibraciones']['total_proximas'],
        'muestreo_pendiente_semana': out['secciones']['muestreo_micro_semana']['total'],
        'cola_liberacion_listos': out['secciones']['cola_liberacion']['listos_revisar_hoy'],
        'auditorias_proximas': out['secciones']['auditorias_proximas']['total'],
        'estabilidades_pendientes': out['secciones']['estabilidades_pendientes']['total'],
        'agua_registrada_hoy': out['secciones']['registro_agua_hoy'].get('registrado', False),
        'ebr_por_liberar': out['secciones']['ebr_por_liberar']['total'],
        'por_vencer': out['secciones'].get('por_vencer', {}).get('total', 0),
        'vencidos': out['secciones'].get('por_vencer', {}).get('vencidos', 0),
        'equipos_calibracion_vencidos': out['secciones'].get('equipos_calibracion', {}).get('vencidos', 0),
        'oos_sla_vencidos': out['secciones'].get('oos_abiertas', {}).get('sla_vencidos', 0),
    }
    # Total de "items que requieren acción del equipo Calidad"
    out['kpis']['total_pendientes'] = (
        out['kpis']['lotes_cuarentena']
        + out['kpis']['ncs_abiertas']
        + out['kpis']['oos_abiertas']
        + out['kpis']['calibraciones_vencidas']
        + out['kpis']['cola_liberacion_listos']
        + out['kpis']['ebr_por_liberar']
        + out['kpis']['vencidos']
    )
    return jsonify(out)


@bp.route('/api/calidad/no-conformidades', methods=['GET', 'POST'])
def handle_no_conformidades():
    # GET es libre para cualquier user logueado · POST requiere Calidad/Admin
    if request.method == 'POST':
        err, code = _require_calidad()
        if err: return err, code
    elif 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    if request.method == 'POST':
        d = request.get_json(silent=True) or {}
        desc = (d.get('descripcion') or '').strip()
        if not desc:
            return jsonify({'error': 'descripcion requerida'}), 400
        user = session.get('compras_user', '')
        c.execute("""INSERT INTO no_conformidades
                     (fecha,tipo,descripcion,area,responsable,lote,codigo_mp,
                      impacto,accion_correctiva,estado,creado_por)
                     VALUES (date('now', '-5 hours'),?,?,?,?,?,?,?,?,'Abierta',?)""",
                  (d.get('tipo','Proceso'), desc,
                   d.get('area',''), d.get('responsable',''),
                   d.get('lote',''), d.get('codigo_mp',''),
                   d.get('impacto','Bajo'), d.get('accion_correctiva',''),
                   user))
        new_id = c.lastrowid
        # Audit log INVIMA · creación de NC es evento regulado
        try:
            audit_log(c, usuario=user, accion='CREAR_NC', tabla='no_conformidades',
                      registro_id=new_id,
                      despues={'tipo': d.get('tipo','Proceso'),
                                'descripcion': desc[:300],
                                'lote': d.get('lote','')[:100],
                                'impacto': d.get('impacto','Bajo')})
        except Exception as e:
            log.warning('audit_log CREAR_NC fallo: %s', e)
        conn.commit()
        return jsonify({'id': new_id}), 201
    # GET
    c.execute("""SELECT id,fecha,tipo,descripcion,area,responsable,lote,codigo_mp,
                        impacto,accion_correctiva,estado,fecha_cierre,cerrado_por,creado_por
                 FROM no_conformidades ORDER BY id DESC LIMIT 200""")
    cols = ['id','fecha','tipo','descripcion','area','responsable','lote','codigo_mp',
            'impacto','accion_correctiva','estado','fecha_cierre','cerrado_por','creado_por']
    rows = [dict(zip(cols, r)) for r in c.fetchall()]
    return jsonify(rows)

@bp.route('/api/calidad/no-conformidades/<int:ncid>/cerrar', methods=['POST'])
def cerrar_no_conformidad(ncid):
    """Cierra una NC. Sebastián 1-may-2026 audit INVIMA:
    - Requiere motivo_cierre (≥10 chars) explícito
    - Requiere accion_correctiva o evidencia
    - RBAC: solo CALIDAD_USERS o ADMIN_USERS
    - Audit log obligatorio (regulación INVIMA)
    """
    user = session.get('compras_user', '')
    # RBAC: solo calidad o admin pueden cerrar NC
    try:
        from config import CALIDAD_USERS, ADMIN_USERS
        autorizados = set(CALIDAD_USERS) | set(ADMIN_USERS)
    except ImportError:
        from config import ADMIN_USERS
        autorizados = set(ADMIN_USERS)
    if user not in autorizados:
        return jsonify({'error': 'Solo Calidad o Admin pueden cerrar NCs (regulación INVIMA)'}), 403

    d = request.get_json(silent=True) or {}
    motivo = (d.get('motivo_cierre') or '').strip()
    accion = (d.get('accion_correctiva') or '').strip()
    if len(motivo) < 10:
        return jsonify({'error': 'motivo_cierre requerido (mín 10 chars)'}), 400
    if len(accion) < 5:
        return jsonify({'error': 'accion_correctiva requerida (mín 5 chars)'}), 400
    conn = get_db(); c = conn.cursor()
    # Verificar NC existe y NO ya cerrada
    row = c.execute(
        "SELECT estado FROM no_conformidades WHERE id=?", (ncid,)
    ).fetchone()
    if not row:
        return jsonify({'error': 'NC no encontrada'}), 404
    if row[0] == 'Cerrada':
        return jsonify({'error': 'NC ya está cerrada'}), 409
    # CAS (M27): el chequeo de arriba es check-then-act · con 3 workers, dos cierres
    # simultaneos pasan LOS DOS y dejan dos entradas de audit_log del mismo cierre. La condicion
    # en el WHERE no cambia el contrato -- el 409 de "ya esta cerrada" ya existia -- solo cierra
    # la ventana de concurrencia.
    c.execute("""UPDATE no_conformidades
                 SET estado='Cerrada', fecha_cierre=date('now', '-5 hours'), cerrado_por=?,
                     accion_correctiva=COALESCE(?, accion_correctiva)
                 WHERE id=? AND COALESCE(estado,'') <> 'Cerrada'""",
              (user, accion, ncid))
    if c.rowcount == 0:
        conn.rollback()
        return jsonify({'error': 'NC ya está cerrada', 'codigo': 'NC_YA_CERRADA'}), 409
    # Audit log INVIMA
    try:
        import json as _json
        c.execute("""
            INSERT INTO audit_log (usuario, accion, registro_id, antes, despues)
            VALUES (?, 'CERRAR_NC', ?, ?, ?)
        """, (user, str(ncid), _json.dumps({'estado_anterior': row[0]}),
              _json.dumps({'motivo': motivo[:300], 'accion': accion[:300]})))
    except Exception as _e:
        import logging
        logging.getLogger('calidad').warning('audit cerrar_NC fallo: %s', _e)
    conn.commit()
    return jsonify({'ok': True, 'cerrado_por': user, 'fecha_cierre': datetime.now().date().isoformat()})

@bp.route('/api/calidad/calibraciones')
def get_calibraciones():
    conn = get_db(); c = conn.cursor()
    hoy = datetime.now().strftime('%Y-%m-%d')
    # Auto-update estado based on fecha_proxima
    c.execute("""UPDATE calibraciones_instrumentos
                 SET estado='Vencida' WHERE fecha_proxima < ? AND estado='Vigente'""", (hoy,))
    conn.commit()
    c.execute("""SELECT id,instrumento,codigo,ubicacion,fecha_ultima,fecha_proxima,
                        responsable,empresa,estado,certificado,observaciones
                 FROM calibraciones_instrumentos
                 ORDER BY CASE estado WHEN 'Vencida' THEN 0 ELSE 1 END, fecha_proxima ASC""")
    cols = ['id','instrumento','codigo','ubicacion','fecha_ultima','fecha_proxima',
            'responsable','empresa','estado','certificado','observaciones']
    rows = [dict(zip(cols, r)) for r in c.fetchall()]
    return jsonify(rows)

# ── CRONOGRAMA DEL DÍA ─────────────────────────────────────────────────────

@bp.route('/api/calidad/cronograma')
def get_cronograma():
    fecha = request.args.get('fecha', datetime.now().strftime('%Y-%m-%d'))
    conn = get_db(); c = conn.cursor()
    c.execute("""SELECT id,nombre,categoria,hora_objetivo,hora_limite,responsable,
                        procedimiento,requiere_valor,unidad_valor,orden
                 FROM calidad_tareas WHERE activa=1 ORDER BY orden, id""")
    cols_t = ['id','nombre','categoria','hora_objetivo','hora_limite','responsable',
              'procedimiento','requiere_valor','unidad_valor','orden']
    tareas = [dict(zip(cols_t, r)) for r in c.fetchall()]
    c.execute("""SELECT tarea_id,usuario,estado,hora_inicio,hora_fin,
                        valor_registrado,observaciones
                 FROM calidad_registros WHERE fecha=?""", (fecha,))
    cols_r = ['tarea_id','usuario','estado','hora_inicio','hora_fin',
              'valor_registrado','observaciones']
    registros = {r[0]: dict(zip(cols_r, r)) for r in c.fetchall()}
    return jsonify({'tareas': tareas, 'registros': registros, 'fecha': fecha})

@bp.route('/api/calidad/cronograma/iniciar', methods=['POST'])
def iniciar_tarea_cron():
    err, code = _require_calidad()
    if err:
        return err, code
    d = request.get_json(silent=True) or {}
    tarea_id = d.get('tarea_id')
    fecha = d.get('fecha', datetime.now().strftime('%Y-%m-%d'))
    hora_ahora = datetime.now().strftime('%H:%M')
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT id FROM calidad_registros WHERE fecha=? AND tarea_id=?", (fecha, tarea_id))
    existing = c.fetchone()
    if existing:
        c.execute("UPDATE calidad_registros SET estado='En curso', hora_inicio=? WHERE id=?",
                  (hora_ahora, existing[0]))
    else:
        c.execute("""INSERT INTO calidad_registros
                     (fecha,tarea_id,usuario,estado,hora_inicio)
                     VALUES (?,?,?,?,?)""",
                  (fecha, tarea_id, session.get('compras_user',''), 'En curso', hora_ahora))
    conn.commit()
    return jsonify({'ok': True})

@bp.route('/api/calidad/cronograma/completar', methods=['POST'])
def completar_tarea_cron():
    err, code = _require_calidad()
    if err:
        return err, code
    d = request.get_json(silent=True) or {}
    tarea_id = d.get('tarea_id')
    fecha = d.get('fecha', datetime.now().strftime('%Y-%m-%d'))
    hora_ahora = datetime.now().strftime('%H:%M')
    estado = d.get('estado', 'Completada')
    if estado not in ('Completada', 'No aplica', 'OOS'):
        estado = 'Completada'
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT id, hora_inicio FROM calidad_registros WHERE fecha=? AND tarea_id=?",
              (fecha, tarea_id))
    existing = c.fetchone()
    if existing:
        c.execute("""UPDATE calidad_registros
                     SET estado=?, hora_fin=?, valor_registrado=?, observaciones=?,
                         usuario=?
                     WHERE id=?""",
                  (estado, hora_ahora, d.get('valor',''), d.get('observaciones',''),
                   session.get('compras_user',''), existing[0]))
    else:
        c.execute("""INSERT INTO calidad_registros
                     (fecha,tarea_id,usuario,estado,hora_fin,valor_registrado,observaciones)
                     VALUES (?,?,?,?,?,?,?)""",
                  (fecha, tarea_id, session.get('compras_user',''),
                   estado, hora_ahora, d.get('valor',''), d.get('observaciones','')))
    if estado == 'OOS':
        c.execute("SELECT nombre FROM calidad_tareas WHERE id=?", (tarea_id,))
        row = c.fetchone()
        nombre_tarea = row[0] if row else 'Tarea de cronograma'
        # Sebastián 25-may-2026 · audit zero-error INVIMA Res 2214/2021 ·
        # NC creada por OOS de cronograma debe tener audit_log + lote si
        # aplica (el cliente puede mandar lote en el body para vincular
        # · si no, queda NULL · monitoreos ambientales/calibración no
        # tienen lote asociado · es válido).
        _lote_oos = (d.get('lote') or '').strip() or None
        descripcion_nc = 'OOS detectado en cronograma: ' + nombre_tarea
        usuario = session.get('compras_user', '')
        c.execute("""INSERT INTO no_conformidades
                     (fecha,tipo,descripcion,lote,area,responsable,impacto,
                      accion_correctiva,estado,creado_por)
                     VALUES (date('now', '-5 hours'),'Proceso',?,?,
                     'Calidad','Jefe CC','Alto',
                     ?,'Abierta',?)""",
                  (descripcion_nc, _lote_oos,
                   d.get('observaciones', ''), usuario))
        try:
            from audit_helpers import audit_log
            nc_id = c.lastrowid
            audit_log(c, usuario=usuario, accion='CREAR_NC_OOS',
                      tabla='no_conformidades', registro_id=str(nc_id),
                      despues={'tipo': 'Proceso', 'descripcion': descripcion_nc[:200],
                                'lote': _lote_oos, 'tarea_id': tarea_id,
                                'tarea_nombre': nombre_tarea,
                                'observaciones': (d.get('observaciones') or '')[:200]},
                      detalle=f"NC auto creada por OOS en cronograma · tarea {tarea_id} ({nombre_tarea[:60]})")
        except Exception as _e_audit:
            import logging as _lg
            _lg.getLogger('calidad').warning(
                'audit_log CREAR_NC_OOS fallo: %s', _e_audit)
    conn.commit()
    return jsonify({'ok': True})

@bp.route('/api/calidad/cronograma/resumen')
def resumen_cronograma():
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM calidad_tareas WHERE activa=1")
    total_tareas = c.fetchone()[0] or 1
    dias = []
    for i in range(6, -1, -1):
        fecha = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        c.execute("""SELECT
                       COUNT(*) as total_reg,
                       SUM(CASE WHEN estado IN ('Completada','No aplica') THEN 1 ELSE 0 END) as comp,
                       SUM(CASE WHEN estado='OOS' THEN 1 ELSE 0 END) as oos
                     FROM calidad_registros WHERE fecha=?""", (fecha,))
        row = c.fetchone()
        dias.append({
            'fecha': fecha,
            'completadas': (row[1] or 0) + (row[2] or 0),
            'oos': row[2] or 0,
            'total_tareas': total_tareas
        })
    return jsonify({'dias': dias, 'total_tareas': total_tareas})


# ═════════════════════════════════════════════════════════════════════════
#   CALIDAD AVANZADA: CoA · Especificaciones MP · Estabilidades · CAPA
# ═════════════════════════════════════════════════════════════════════════

# ─── ESPECIFICACIONES MP ────────────────────────────────────────────────────

@bp.route('/api/calidad/especificaciones', methods=['GET','POST'])
def especificaciones_list():
    if request.method == 'POST':
        # Audit zero-error 2-may-2026: alterar specs farmacopea es decisión técnica
        err, code = _require_calidad()
        if err: return err, code
    elif 'compras_user' not in session:
        return jsonify({'error':'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        if not d.get('codigo_mp') or not d.get('parametro'):
            return jsonify({'error':'codigo_mp y parametro requeridos'}), 400
        user = session.get('compras_user','sistema')
        try:
            c.execute("""INSERT INTO especificaciones_mp
                (codigo_mp, parametro, unidad, valor_min, valor_max, metodo_ensayo,
                 obligatorio, tipo, farmacopea_ref, creado_por)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (d['codigo_mp'], d['parametro'], d.get('unidad',''),
                 d.get('valor_min'), d.get('valor_max'), d.get('metodo_ensayo',''),
                 1 if d.get('obligatorio', True) else 0,
                 d.get('tipo','fisicoquimico'), d.get('farmacopea_ref',''),
                 user))
            spec_id = c.lastrowid
            # Audit log INVIMA · alterar specs es regulatorio
            try:
                audit_log(c, usuario=user, accion='CREAR_SPEC_MP',
                          tabla='especificaciones_mp', registro_id=spec_id,
                          despues={'codigo_mp': d['codigo_mp'][:60],
                                    'parametro': d['parametro'][:80],
                                    'min': d.get('valor_min'),
                                    'max': d.get('valor_max')})
            except Exception as e:
                log.warning('audit_log CREAR_SPEC_MP fallo: %s', e)
            conn.commit()
            return jsonify({'ok':True, 'id':spec_id}), 201
        except sqlite3.IntegrityError:
            return jsonify({'error':'Ya existe especificacion para ese MP+parametro'}), 409
    # GET · filtro por codigo_mp opcional
    codigo = request.args.get('codigo_mp','').strip()
    if codigo:
        c.execute("""SELECT * FROM especificaciones_mp WHERE codigo_mp=?
                     ORDER BY parametro""", (codigo,))
    else:
        c.execute("""SELECT * FROM especificaciones_mp
                     ORDER BY codigo_mp, parametro LIMIT 500""")
    cols = [x[0] for x in c.description]
    return jsonify([dict(zip(cols,r)) for r in c.fetchall()])


@bp.route('/api/calidad/especificaciones/<int:eid>', methods=['PATCH','DELETE'])
def especificacion_update(eid):
    # RBAC · alterar/borrar specs de farmacopea cambia los rangos que
    # auto-validan los CoA · solo Calidad/Admin.
    err, code = _require_calidad()
    if err:
        return err, code
    user = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()
    if request.method == 'DELETE':
        c.execute("DELETE FROM especificaciones_mp WHERE id=?", (eid,))
        audit_log(c, usuario=user, accion='ELIMINAR_SPEC_MP',
                  tabla='especificaciones_mp', registro_id=eid)
        conn.commit()
        return jsonify({'ok':True})
    d = request.json or {}
    fields = ['unidad','valor_min','valor_max','metodo_ensayo','obligatorio',
              'tipo','farmacopea_ref']
    sets = ', '.join(f+'=?' for f in fields if f in d)
    vals = [d[f] for f in fields if f in d]
    if not sets: return jsonify({'error':'Nada que actualizar'}), 400
    vals.append(eid)
    c.execute(f"UPDATE especificaciones_mp SET {sets} WHERE id=?", vals)
    audit_log(c, usuario=user, accion='MODIFICAR_SPEC_MP',
              tabla='especificaciones_mp', registro_id=eid, despues=d)
    conn.commit()
    return jsonify({'ok':True})


# ─── CoA RESULTADOS ─────────────────────────────────────────────────────────

# ═══════════════════════════════════════════════════════════════════════════
# 🧪 RECEPCIÓN DE MP EN 3 ETAPAS (Laura 18-jul · mig 361 · formatos COC-PRO-002)
# 🅐 Recepción administrativa (Catalina · Compras) → CUARENTENA automático
# 🅑 F01 Recepción técnica y documental (COC-PRO-002-F01) → Conforme/No conforme
# 🅒 F02 Certificado de análisis de MP (COC-PRO-002-F02) → Aprobado libera el lote (VIGENTE)
# ═══════════════════════════════════════════════════════════════════════════
def _fecha_co():
    from datetime import datetime as _d, timezone as _t, timedelta as _td
    return (_d.now(_t.utc) - _td(hours=5)).isoformat()


def _crear_nc_rechazo(cur, user, *, lote, codigo, nombre, cantidad, proveedor, oc, motivo, es_envase):
    """Crea la No Conformidad de un lote RECHAZADO en recepción (devolución al proveedor · trazabilidad INVIMA).
    Se llama SOLO cuando el CAS acaba de mover el lote a RECHAZADO → no duplica (el 2º intento no transiciona).
    Reusa la tabla/pane canónico `no_conformidades` (M1). Devuelve el id o None."""
    _fecha = (datetime.utcnow() - timedelta(hours=5)).date().isoformat()  # M24 · fecha Colombia en Python, no date() en DML
    tipo = 'Envase rechazado' if es_envase else 'Materia prima rechazada'
    unidad = 'und' if es_envase else 'g'
    desc = ("Lote RECHAZADO en recepcion de calidad: " + str(nombre or codigo or '') + " (codigo " + str(codigo or 'N/D')
            + "), lote " + str(lote or 'N/D') + ", " + str(cantidad or '?') + " " + unidad
            + ", proveedor " + str(proveedor or 'N/D') + ", OC " + str(oc or 'N/D') + ". "
            + "Motivo: " + (str(motivo).strip() if motivo and str(motivo).strip() else 'no conforme en el control de recepcion') + ".")
    try:
        cur.execute("""INSERT INTO no_conformidades
                       (fecha,tipo,descripcion,area,responsable,lote,codigo_mp,
                        impacto,accion_correctiva,estado,creado_por)
                       VALUES (?,?,?,?,?,?,?,?,?,'Abierta',?)""",
                    (_fecha, tipo, desc, 'Recepcion / Calidad', user, str(lote or ''), str(codigo or ''),
                     'Alto', 'Devolucion al proveedor (pendiente de gestion por Compras)', user))
        nc_id = cur.lastrowid
        audit_log(cur, usuario=user, accion='CREAR_NC', tabla='no_conformidades', registro_id=(nc_id or 0),
                  despues={'origen': 'recepcion_rechazo', 'lote': str(lote or '')[:100],
                           'codigo': str(codigo or ''), 'impacto': 'Alto'})
        return nc_id
    except Exception as e:
        log.warning('crear NC de rechazo fallo: %s', e)
        return None


@bp.route('/api/calidad/recepcion-pipeline', methods=['GET'])
def calidad_recepcion_pipeline():
    """Lotes de MP y ENVASES (MEE) en cuarentena + estado de sus formatos F01/F02 (pipeline de Calidad · Laura).
    MP: 🅐 admin → 🅑 F01 → 🅒 F02 (aprobado libera). MEE: 🅐 admin → 🅑 F01 (conforme + firma libera · sin F02)."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    lotes = []
    try:
        for r in c.execute(
            """SELECT m.id, m.material_id, m.material_nombre, m.cantidad, m.lote,
                      m.fecha_vencimiento, m.proveedor, m.fecha, m.numero_oc, m.estado_lote
               FROM movimientos m
               LEFT JOIN maestro_mps mp ON m.material_id=mp.codigo_mp
               WHERE UPPER(COALESCE(m.estado_lote,'')) IN ('CUARENTENA','CUARENTENA_EXTENDIDA') AND m.tipo='Entrada'
                 AND TRIM(COALESCE(m.material_id,'')) <> ''
                 AND COALESCE(m.observaciones,'') NOT LIKE '%::ANULADA-mov#%'
                 AND UPPER(COALESCE(mp.tipo_material,'MP'))='MP'
               ORDER BY m.fecha DESC LIMIT 100""").fetchall():
            mid = r[0]
            f01 = c.execute("SELECT resultado FROM recepcion_tecnica_doc WHERE mov_id=? AND COALESCE(origen,'MP')='MP' "
                            "AND COALESCE(anulado,0)=0 ORDER BY id DESC LIMIT 1", (mid,)).fetchone()
            f02 = c.execute("SELECT resultado FROM certificado_analisis_mp WHERE mov_id=? AND COALESCE(anulado,0)=0 "
                            "ORDER BY id DESC LIMIT 1", (mid,)).fetchone()
            lotes.append({'mov_id': mid, 'tipo': 'MP', 'codigo_mp': r[1], 'nombre': r[2], 'cantidad': r[3], 'lote': r[4],
                          'fecha_vencimiento': r[5] or '', 'proveedor': r[6] or '', 'fecha': (r[7] or '')[:10],
                          'numero_oc': r[8] or '', 'estado_lote': r[9] or '',
                          'f01_resultado': (f01[0] if f01 else ''), 'f02_resultado': (f02[0] if f02 else '')})
    except Exception:
        lotes = []
    # ── ENVASES (MEE) en cuarentena · movimientos_mee (id colisiona con movimientos.id → origen='MEE') ──
    try:
        for r in c.execute(
            """SELECT mv.id, mv.mee_codigo, COALESCE(mm.descripcion, mv.mee_codigo), mv.cantidad,
                      COALESCE(mv.lote_ref,''), COALESCE(mv.fecha_vencimiento,''), COALESCE(mv.proveedor,''),
                      mv.fecha, COALESCE(mv.oc_numero,''), COALESCE(mv.estado,''),
                      COALESCE(mv.n_cajas,0), COALESCE(mv.observaciones,'')
               FROM movimientos_mee mv
               LEFT JOIN maestro_mee mm ON UPPER(TRIM(mm.codigo))=UPPER(TRIM(mv.mee_codigo))
               WHERE mv.tipo='Entrada' AND COALESCE(mv.anulado,0)=0
                 AND (
                      UPPER(COALESCE(mv.estado,'VIGENTE'))='CUARENTENA'
                      -- Sebastián 30-jul: los envases ya NO entran en cuarentena (entran
                      -- disponibles). Si esta bandeja siguiera mirando sólo la cuarentena, la
                      -- revisión de Calidad DESAPARECERÍA de la pantalla el mismo día que se
                      -- quitó el candado (M112: al cambiar el estado, la cola que se alimenta
                      -- de ese estado se muere en silencio). Ahora también lista lo que llegó
                      -- por cajas y todavía nadie revisó.
                      OR (COALESCE(mv.n_cajas,0) > 0
                          AND COALESCE(mv.observaciones,'') NOT LIKE '%[REVISADO]%'
                          AND UPPER(COALESCE(mv.estado,'VIGENTE')) <> 'RECHAZADO')
                 )
                 AND UPPER(COALESCE(mv.lote_ref,'')) NOT LIKE '%MARCACION%'
               ORDER BY mv.id DESC LIMIT 100""").fetchall():
            mid = r[0]
            f01 = c.execute("SELECT resultado FROM recepcion_tecnica_doc WHERE mov_id=? AND COALESCE(origen,'MP')='MEE' "
                            "AND COALESCE(anulado,0)=0 ORDER BY id DESC LIMIT 1", (mid,)).fetchone()
            lotes.append({'mov_id': mid, 'tipo': 'MEE', 'codigo_mp': r[1], 'nombre': r[2], 'cantidad': r[3], 'lote': r[4],
                          'fecha_vencimiento': r[5] or '', 'proveedor': r[6] or '', 'fecha': (r[7] or '')[:10],
                          'numero_oc': r[8] or '', 'estado_lote': r[9] or '',
                          # la pantalla decide con ESTO si ofrece "Revisar cajas", no con el
                          # estado del kardex (que desde el 30-jul ya es VIGENTE al recibir)
                          'n_cajas': int(r[10] or 0),
                          'cajas_por_revisar': bool(int(r[10] or 0) > 0
                                                    and '[REVISADO]' not in str(r[11] or '')),
                          'f01_resultado': (f01[0] if f01 else ''), 'f02_resultado': ''})
    except Exception:
        pass
    return jsonify({'ok': True, 'lotes': lotes})


def _urlq(s):
    """URL-encode para armar links de documentos del expediente (códigos/lotes)."""
    import urllib.parse
    return urllib.parse.quote(str(s if s is not None else ''), safe='')


_F01_COLS = ['mov_id', 'numero_oc', 'lote', 'tipo_insumo', 'codigo_insumo', 'nombre_insumo', 'lote_proveedor',
             'cantidad_recibida', 'proveedor', 'fecha_recepcion', 'numero_remision', 'area_almacenamiento',
             # Ubicación ESTRUCTURADA (mig 389). `area_almacenamiento` se conserva porque es lo
             # que se imprime en el F01 firmado, pero se DERIVA de estas tres: una sola fuente.
             'ubic_tipo', 'ubic_estanteria', 'ubic_posicion',
             'crit_rotulado', 'crit_empaque', 'crit_hoja_seguridad', 'crit_ficha_tecnica', 'crit_coa',
             'crit_doc_coincide', 'observaciones', 'resultado', 'fecha_vencimiento',
             'realiza_por', 'realiza_fecha', 'aprueba_por', 'aprueba_fecha']


@bp.route('/api/calidad/recepcion-tecnica', methods=['GET', 'POST'])
def calidad_recepcion_tecnica():
    """F01 · Recepción técnica y documental (COC-PRO-002-F01). GET ?mov_id=X&origen=MP|MEE → registro o prefill.
    Para ENVASES (origen='MEE') el F01 Conforme + firma del jefe LIBERA el lote (movimientos_mee CUARENTENA→VIGENTE);
    los envases no llevan F02 (sin análisis fisicoquímico)."""
    if request.method == 'GET':
        if 'compras_user' not in session:
            return jsonify({'error': 'No autorizado'}), 401
        mov_id = request.args.get('mov_id')
        origen = 'MEE' if (request.args.get('origen', 'MP').upper() == 'MEE') else 'MP'
        conn = get_db(); c = conn.cursor()
        row = c.execute("SELECT * FROM recepcion_tecnica_doc WHERE mov_id=? AND COALESCE(origen,'MP')=? "
                        "AND COALESCE(anulado,0)=0 ORDER BY id DESC LIMIT 1", (mov_id, origen)).fetchone()
        if row:
            cols = [d[0] for d in c.description]
            _f01 = dict(zip(cols, row))
            # Código REAL del insumo (trazabilidad · SIEMPRE desde el movimiento · no editable ·
            # Sebastián 24-jul: el código interno no se toca · el codigo_insumo guardado puede venir
            # vacío en registros viejos, por eso se resuelve del kardex).
            if origen == 'MEE':
                _m = c.execute("SELECT mee_codigo FROM movimientos_mee WHERE id=?", (mov_id,)).fetchone()
            else:
                _m = c.execute("SELECT material_id FROM movimientos WHERE id=?", (mov_id,)).fetchone()
            _cr = ((_m[0] if _m else '') or _f01.get('codigo_insumo') or '')
            return jsonify({'ok': True, 'f01': _f01, 'codigo_real': _cr, 'origen': origen})
        pre = {}
        if origen == 'MEE':
            m = c.execute("SELECT mv.mee_codigo, COALESCE(mm.descripcion, mv.mee_codigo), mv.cantidad, mv.lote_ref, "
                          "COALESCE(mv.proveedor,''), mv.fecha, COALESCE(mv.oc_numero,''), COALESCE(mv.fecha_vencimiento,'') "
                          "FROM movimientos_mee mv LEFT JOIN maestro_mee mm ON UPPER(TRIM(mm.codigo))=UPPER(TRIM(mv.mee_codigo)) "
                          "WHERE mv.id=?", (mov_id,)).fetchone()
            if m:
                pre = {'codigo_insumo': m[0], 'nombre_insumo': m[1], 'cantidad_recibida': str(m[2] or ''),
                       'lote': m[3] or '', 'proveedor': m[4] or '', 'fecha_recepcion': (m[5] or '')[:10],
                       'numero_oc': m[6] or '', 'fecha_vencimiento': m[7] or '', 'tipo_insumo': 'envase'}
        else:
            m = c.execute("SELECT material_id, material_nombre, cantidad, lote, proveedor, fecha, numero_oc, "
                          "fecha_vencimiento FROM movimientos WHERE id=?", (mov_id,)).fetchone()
            if m:
                pre = {'codigo_insumo': m[0], 'nombre_insumo': m[1], 'cantidad_recibida': str(m[2] or ''),
                       'lote': m[3], 'proveedor': m[4] or '', 'fecha_recepcion': (m[5] or '')[:10],
                       'numero_oc': m[6] or '', 'fecha_vencimiento': m[7] or '', 'tipo_insumo': 'materia_prima'}
        return jsonify({'ok': True, 'f01': None, 'prefill': pre, 'codigo_real': pre.get('codigo_insumo', ''), 'origen': origen})
    err, code = _require_calidad()
    if err:
        return err, code
    u = session.get('compras_user', '')
    b = request.get_json(silent=True) or {}
    mov_id = b.get('mov_id')
    if not mov_id:
        return jsonify({'error': 'Falta el lote (mov_id)'}), 400
    origen = 'MEE' if (str(b.get('origen') or 'MP').upper() == 'MEE') else 'MP'
    resultado = (str(b.get('resultado') or '')).strip().lower()  # conforme | no_conforme
    aprueba_por = (str(b.get('aprueba_por') or '')).strip()
    # Para envases (MEE) el F01 es la liberación → conforme exige firma del jefe
    if origen == 'MEE' and resultado == 'conforme' and not aprueba_por:
        return jsonify({'error': 'Para liberar el envase se requiere la firma del jefe de calidad (aprueba)'}), 400
    vals = {k: (str(b.get(k) or '')) for k in _F01_COLS}
    vals['mov_id'] = mov_id
    vals['resultado'] = resultado  # guardar NORMALIZADO (no crudo) · el conteo/dispo filtra exacto (M2/M23 · revisor 19-jul)

    # ── UBICACIÓN ────────────────────────────────────────────────────────────────────
    # Sebastián 28-jul: "la lógica del inventario es que hay estanterías y posiciones, y
    # nevera; debería pedir esos datos, y al guardar traducirse a trazabilidad y aparecer en
    # todo lado -- me dicen que no se refleja en inventario".
    #
    # Antes era UN texto libre que sólo alimentaba `movimientos.estanteria`; `posicion` quedaba
    # vacía aunque la vista de inventario, el rótulo y el conteo cíclico la leen. Y como era
    # libre, 'A3' / 'Estante 3' / 'estanteria A-3' eran tres estantes distintos para el sistema
    # (el conteo agrupa POR estantería, así que cada variante inventaba uno).
    #
    # `area_almacenamiento` se DERIVA de los campos estructurados: es el texto que se imprime
    # en el F01 firmado, y así no puede decir una cosa distinta de lo que fue al kardex (M5).
    _u_tipo = (vals.get('ubic_tipo') or '').strip().lower()
    _u_est = (vals.get('ubic_estanteria') or '').strip()
    _u_pos = (vals.get('ubic_posicion') or '').strip()
    if _u_tipo == 'nevera':
        # Una sola nevera por ahora y sin posiciones adentro (decisión de Sebastián 28-jul).
        # Si algún día hay más de una, el tipo ya está separado del nombre y sólo cambia acá.
        _u_est, _u_pos = 'NEVERA', ''
        vals['ubic_estanteria'], vals['ubic_posicion'] = _u_est, _u_pos
        vals['area_almacenamiento'] = 'Nevera (refrigerado)'
    elif _u_tipo == 'estanteria' and _u_est:
        vals['area_almacenamiento'] = (
            'Estantería %s · Posición %s' % (_u_est, _u_pos) if _u_pos else 'Estantería %s' % _u_est)
    # Si no vino nada estructurado (F01 viejo o edición de uno anterior) se respeta el texto
    # libre tal cual: es un registro regulado ya firmado, no se reescribe.
    conn = get_db(); cur = conn.cursor()
    # E-firma Part 11 para DISPONER el envase (conforme=libera / no_conforme=rechaza) · idéntico al F02 de MP
    # (Sebastián 19-jul). Solo MEE: para MP el F01 es documental (la disposición la hace el F02).
    signature_id = b.get('signature_id')
    if origen == 'MEE' and resultado in ('conforme', 'no_conforme'):
        _meaning = 'libera' if resultado == 'conforme' else 'rechaza'
        if not _validar_e_sign_cal(cur, signature_id, record_table='movimientos_mee',
                                   record_id=mov_id, meaning=_meaning, signer=u):
            return jsonify({'error': 'Se requiere firma electrónica (21 CFR Part 11) para disponer el envase. '
                            'Firmá con /api/sign (record_table=movimientos_mee, record_id=' + str(mov_id) +
                            ') y reenviá signature_id.',
                            'requiere_firma': True, 'record_id': str(mov_id), 'sign_meaning': _meaning}), 400
    try:
        cur.execute("UPDATE recepcion_tecnica_doc SET anulado=1 WHERE mov_id=? AND COALESCE(origen,'MP')=? "
                    "AND COALESCE(anulado,0)=0", (mov_id, origen))
        _f = _F01_COLS + ['origen', 'creado_por', 'creado_en']
        cur.execute(f"INSERT INTO recepcion_tecnica_doc ({','.join(_f)}) VALUES ({','.join(['?']*len(_f))})",
                    [vals[k] for k in _F01_COLS] + [origen, u, _fecha_co()])
        _f01_id = cur.lastrowid  # capturar YA · _crear_nc_rechazo mueve lastrowid (su audit_log) · M22

        # ── Lo que Calidad verifica contra el ENVASE entra al KARDEX acá (Sebastián 27-jul) ──
        # "Calidad allí hace la recepción, deben poder poner todos los datos de su F01 pero a la
        # vez editar el rótulo en todos los pasos."
        #
        # El F01 ya pedía lote real, cantidad pesada y vencimiento, pero los guardaba SOLO en el
        # documento: el kardex se quedaba con el lote provisional y la cantidad comprada, y el
        # RÓTULO se imprime leyendo el kardex → el envase se rotulaba con datos viejos. Las
        # correcciones sólo aterrizaban al aprobar el F02, que es el último paso, cuando el
        # envase ya lleva rato rotulado y guardado.
        #
        # Estos tres NO son un juicio de calidad, son hechos de lo que llegó, y quien los puede
        # leer es quien tiene el envase en la mano. Por eso se escriben en el F01.
        #
        # Sólo mientras el lote sigue en CUARENTENA (M86): corregir el lote o la cantidad de
        # material YA CONSUMIDO corrompería el kardex hacia atrás.
        _kardex_corr = []
        if origen == 'MP':
            _mrow = cur.execute(
                "SELECT COALESCE(lote,''), cantidad, COALESCE(fecha_vencimiento,''), "
                "       material_id, UPPER(COALESCE(estado_lote,'')) "
                "FROM movimientos WHERE id=?", (mov_id,)).fetchone()
            if _mrow and _mrow[4] in ('CUARENTENA', 'CUARENTENA_EXTENDIDA'):
                _k_lote, _k_cant, _k_fv, _k_mat = _mrow[0], _mrow[1], _mrow[2], _mrow[3]
                _lote_key = _k_lote

                # 1) LOTE real del envase. Reemplaza al provisional 'OC-...' que asigna la
                #    recepción administrativa cuando el remito no lo trae. Va sobre TODAS las
                #    filas de ese lote, no sólo la Entrada, o la ubicación y las salidas quedan
                #    colgando de una llave que ya no existe.
                _lp = (vals.get('lote_proveedor') or '').strip()
                if _lp and _lp != _k_lote:
                    cur.execute("UPDATE movimientos SET lote=? WHERE material_id=? AND lote=?",
                                (_lp[:120], _k_mat, _k_lote))
                    _kardex_corr.append('Lote:%s->%s' % (_k_lote, _lp))
                    _lote_key = _lp
                # el lote del proveedor queda además en su columna propia (trazabilidad CoA)
                if _lp:
                    try:
                        cur.execute("UPDATE movimientos SET lote_proveedor=? "
                                    "WHERE material_id=? AND lote=? AND tipo='Entrada'",
                                    (_lp[:120], _k_mat, _lote_key))
                    except Exception as _e_lp:
                        log.warning('F01 lote_proveedor no se pudo escribir (mov %s): %s', mov_id, _e_lp)

                # 2) CANTIDAD pesada en balanza. Es la que manda: lo que entra a bodega es lo que
                #    pesó, no lo que decía la factura. La diferencia contra lo que registró la
                #    recepción administrativa queda en el audit (y alimenta al proveedor).
                try:
                    _cant_f01 = float(str(vals.get('cantidad_recibida') or '').strip() or 0)
                except (TypeError, ValueError):
                    _cant_f01 = 0.0
                if _cant_f01 > 0 and abs(float(_k_cant or 0) - _cant_f01) > 0.001:
                    cur.execute("UPDATE movimientos SET cantidad=? WHERE id=?", (_cant_f01, mov_id))
                    _kardex_corr.append('Cant:%g->%g' % (float(_k_cant or 0), _cant_f01))

                # 3) VENCIMIENTO del envase. Sin esto el lote entra sin fecha y el cron de
                #    vencidos nunca lo puede marcar.
                _fv_f01 = (vals.get('fecha_vencimiento') or '').strip()
                if _fv_f01 and _fv_f01[:10] != str(_k_fv or '')[:10]:
                    cur.execute("UPDATE movimientos SET fecha_vencimiento=? "
                                "WHERE material_id=? AND lote=? AND tipo='Entrada'",
                                (_fv_f01, _k_mat, _lote_key))
                    _kardex_corr.append('FVenc:%s' % _fv_f01[:10])

                # 4) UBICACIÓN → al kardex, que es de donde la leen el inventario, el rótulo y
                #    el conteo cíclico. Se escriben las DOS columnas: antes sólo iba
                #    `estanteria` y `posicion` quedaba vacía para siempre, así que en inventario
                #    se veía media ubicación (era el "no se refleja" que reportó Laura).
                _ubic_est = (vals.get('ubic_estanteria') or '').strip()
                _ubic_pos = (vals.get('ubic_posicion') or '').strip()
                if not _ubic_est:
                    # F01 viejo (texto libre): se respeta lo que se escribió, en estantería.
                    _ubic_est = (vals.get('area_almacenamiento') or '').strip()
                if _ubic_est:
                    try:
                        cur.execute("UPDATE movimientos SET estanteria=?, posicion=? "
                                    "WHERE material_id=? AND lote=?",
                                    (_ubic_est[:50], _ubic_pos[:50], _k_mat, _lote_key))
                        _kardex_corr.append('Ubic:%s%s' % (_ubic_est, ('/' + _ubic_pos) if _ubic_pos else ''))
                    except Exception as _e_ar:
                        log.warning('F01 ubicación no se pudo escribir (mov %s): %s', mov_id, _e_ar)

                if _kardex_corr:
                    # Un cambio de lote/cantidad en un registro regulado NO puede quedar sin
                    # rastro: queda quién, cuándo y el valor anterior.
                    audit_log(cur, usuario=u, accion='F01_CORRIGE_KARDEX', tabla='movimientos',
                              registro_id=mov_id,
                              antes={'lote': _k_lote, 'cantidad': float(_k_cant or 0),
                                     'fecha_vencimiento': str(_k_fv or '')},
                              despues={'lote': _lote_key, 'cantidad': _cant_f01 or float(_k_cant or 0),
                                       'fecha_vencimiento': _fv_f01 or str(_k_fv or ''),
                                       'correcciones': _kardex_corr},
                              detalle='F01 · Calidad verificó contra el envase: ' + ' · '.join(_kardex_corr))

        _liberado = 0; _nc_id = None
        if origen == 'MEE' and resultado in ('conforme', 'no_conforme'):
            # el F01 del envase decide (no hay F02) · CAS: solo si sigue en cuarentena (M23/M27)
            _nuevo = 'VIGENTE' if resultado == 'conforme' else 'RECHAZADO'
            cur.execute("UPDATE movimientos_mee SET estado=? WHERE id=? AND tipo='Entrada' "
                        "AND UPPER(COALESCE(estado,'VIGENTE'))='CUARENTENA'", (_nuevo, mov_id))
            _liberado = cur.rowcount
            if resultado == 'no_conforme' and _liberado > 0:
                # envase rechazado → No Conformidad + devolución al proveedor (trazabilidad)
                mrow = cur.execute("SELECT mv.mee_codigo, COALESCE(mm.descripcion, mv.mee_codigo), mv.cantidad, "
                                   "COALESCE(mv.lote_ref,''), COALESCE(mv.proveedor,''), COALESCE(mv.oc_numero,'') "
                                   "FROM movimientos_mee mv LEFT JOIN maestro_mee mm ON UPPER(TRIM(mm.codigo))=UPPER(TRIM(mv.mee_codigo)) "
                                   "WHERE mv.id=?", (mov_id,)).fetchone()
                if mrow:
                    _nc_id = _crear_nc_rechazo(cur, u, lote=mrow[3], codigo=mrow[0], nombre=mrow[1],
                                               cantidad=mrow[2], proveedor=mrow[4], oc=mrow[5],
                                               motivo=vals.get('observaciones'), es_envase=True)
        # Expediente por lote (INVIMA · zero-paper): inscribir el F01 + su rótulo en el registro central
        _cod_f01 = vals.get('codigo_insumo') or ''
        _lote_f01 = vals.get('lote_proveedor') or vals.get('lote') or ''
        _prod_f01 = vals.get('nombre_insumo') or ''
        registrar_documento(cur, tipo_doc='F01', formato='COC-PRO-002-F01', titulo='Recepción técnica y documental',
                            url='/api/calidad/recepcion-tecnica/imprimible?mov_id=%s&origen=%s' % (mov_id, origen),
                            entidad=origen, codigo=_cod_f01, producto_nombre=_prod_f01, lote=_lote_f01,
                            ref_tabla='recepcion_tecnica_doc', ref_id=(_f01_id or 0), mov_id=mov_id, generado_por=u)
        if _cod_f01:
            _rurl = ('/rotulo-recepcion-mee/%s/%s' % (_urlq(_cod_f01), _urlq(vals.get('cantidad_recibida') or '1'))) if origen == 'MEE' \
                else ('/rotulo-recepcion/%s/%s/%s' % (_urlq(_cod_f01), _urlq(_lote_f01 or 'SL'), _urlq(vals.get('cantidad_recibida') or '1')))
            registrar_documento(cur, tipo_doc='ROTULO', formato='COC-PRO-002-F07', titulo='Rótulo de ingreso',
                                url=_rurl, entidad=origen, codigo=_cod_f01, producto_nombre=_prod_f01, lote=_lote_f01,
                                ref_tabla='recepcion_tecnica_doc', ref_id=('rot-%s' % (_f01_id or 0)), mov_id=mov_id, generado_por=u)
        audit_log(cur, usuario=u, accion='RECEPCION_TECNICA_F01', tabla='recepcion_tecnica_doc',
                  registro_id=(_f01_id or 0),
                  despues={'mov_id': mov_id, 'origen': origen, 'resultado': resultado, 'liberado': _liberado,
                           'nc_id': _nc_id, 'signature_id': signature_id})
        conn.commit()
    except Exception as e:
        conn.rollback(); return jsonify({'error': f'No se pudo guardar F01: {e}'}), 500
    return jsonify({'ok': True, 'resultado': resultado, 'origen': origen, 'liberado': _liberado, 'nc_id': _nc_id})


_F02_COLS = ['mov_id', 'lote', 'codigo_mp', 'nombre_mp', 'lote_proveedor', 'cantidad_recibida', 'proveedor',
             'fecha_recepcion', 'fecha_analisis',
             'aspecto_spec', 'aspecto_result', 'aspecto_cumple', 'aspecto_obs',
             'ph_spec', 'ph_result', 'ph_cumple', 'ph_obs',
             'densidad_spec', 'densidad_result', 'densidad_cumple', 'densidad_obs',
             'solubilidad_spec', 'solubilidad_result', 'solubilidad_cumple', 'solubilidad_obs',
             'viscosidad_spec', 'viscosidad_result', 'viscosidad_cumple', 'viscosidad_obs',
             'resultado', 'observaciones_generales', 'fecha_vencimiento',
             'responsable_analisis', 'realiza_fecha', 'aprobo_por', 'aprobo_fecha']


@bp.route('/api/calidad/certificado-analisis', methods=['GET', 'POST'])
def calidad_certificado_analisis():
    """F02 · Certificado de análisis de MP (COC-PRO-002-F02). resultado='aprobado' + aprobo_por (jefe) LIBERA
    el lote (CUARENTENA→VIGENTE · CAS · M23/M27). 'no_aprobado' → RECHAZADO. 'cuarentena' → se queda."""
    if request.method == 'GET':
        if 'compras_user' not in session:
            return jsonify({'error': 'No autorizado'}), 401
        mov_id = request.args.get('mov_id')
        conn = get_db(); c = conn.cursor()
        # Datos ACTUALES del lote + maestro (siempre, exista o no el F02) → la verificación final de
        # Laura (INCI/tipo/ubicación/código) se prefila aunque reabra un F02 ya guardado. Sebastián 19-jul.
        m = c.execute("SELECT mv.material_id, mv.material_nombre, mv.cantidad, mv.lote, mv.proveedor, mv.fecha, "
                      "mv.fecha_vencimiento, COALESCE(mv.estanteria,''), COALESCE(mv.posicion,''), "
                      "COALESCE(mp.nombre_inci,''), COALESCE(mp.tipo_material,'MP'), COALESCE(mp.nombre_comercial,'') "
                      "FROM movimientos mv LEFT JOIN maestro_mps mp ON mp.codigo_mp=mv.material_id WHERE mv.id=?",
                      (mov_id,)).fetchone()
        pre = {}
        if m:
            pre = {'codigo_mp': m[0], 'nombre_mp': (m[11] or m[1]), 'cantidad_recibida': str(m[2] or ''), 'lote': m[3],
                   'proveedor': m[4] or '', 'fecha_recepcion': (m[5] or '')[:10], 'fecha_vencimiento': m[6] or '',
                   'estanteria': m[7], 'posicion': m[8], 'nombre_inci': m[9], 'tipo_material': (m[10] or 'MP')}
            # prefill specs de aspecto/pH/etc desde especificaciones_mp si existen
            try:
                for sp in c.execute("SELECT parametro, valor_min, valor_max, unidad FROM especificaciones_mp "
                                    "WHERE UPPER(TRIM(codigo_mp))=UPPER(TRIM(?))", (m[0],)).fetchall():
                    _p = (sp[0] or '').lower()
                    if sp[1] is not None and sp[2] is not None:
                        _txt = str(sp[1]) + ' - ' + str(sp[2]) + ' ' + (sp[3] or '')
                    elif sp[1] is not None:
                        _txt = str(sp[1]) + ' ' + (sp[3] or '')
                    else:
                        _txt = ''
                    if 'aspecto' in _p or 'color' in _p or 'olor' in _p:
                        pre['aspecto_spec'] = _txt
                    elif _p.startswith('ph'):
                        pre['ph_spec'] = _txt
                    elif 'densidad' in _p:
                        pre['densidad_spec'] = _txt
                    elif 'solub' in _p:
                        pre['solubilidad_spec'] = _txt
                    elif 'viscos' in _p:
                        pre['viscosidad_spec'] = _txt
            except Exception:
                pass
        row = c.execute("SELECT * FROM certificado_analisis_mp WHERE mov_id=? AND COALESCE(anulado,0)=0 "
                        "ORDER BY id DESC LIMIT 1", (mov_id,)).fetchone()
        if row:
            cols = [d[0] for d in c.description]
            return jsonify({'ok': True, 'f02': dict(zip(cols, row)), 'prefill': pre})
        return jsonify({'ok': True, 'f02': None, 'prefill': pre})
    err, code = _require_calidad()
    if err:
        return err, code
    u = session.get('compras_user', '')
    b = request.get_json(silent=True) or {}
    mov_id = b.get('mov_id')
    if not mov_id:
        return jsonify({'error': 'Falta el lote (mov_id)'}), 400
    resultado = (str(b.get('resultado') or '')).strip().lower()  # aprobado | no_aprobado | cuarentena
    aprobo_por = (str(b.get('aprobo_por') or '')).strip()
    if resultado == 'aprobado' and not aprobo_por:
        return jsonify({'error': 'Para APROBAR y liberar el lote se requiere la firma del jefe de calidad (aprobó)'}), 400
    vals = {k: (str(b.get(k) or '')) for k in _F02_COLS}
    vals['mov_id'] = mov_id
    vals['resultado'] = resultado  # guardar NORMALIZADO (no crudo) · el conteo/dispo filtra exacto (M2/M23 · revisor 19-jul)
    conn = get_db(); cur = conn.cursor()
    # datos del lote para liberar
    lrow = cur.execute("SELECT lote, material_id, COALESCE(numero_oc,'') FROM movimientos WHERE id=?", (mov_id,)).fetchone()
    if not lrow:
        return jsonify({'error': 'El lote no existe'}), 404
    _lote, _matid, _oc = lrow[0], lrow[1], lrow[2]
    # E-firma Part 11 (§11.200) para DISPONER el lote (aprobar/rechazar) · unifica el flujo con el viejo
    # "Revisar CC" (Sebastián 18-jul): la disposición de un lote regulado exige firma electrónica, no solo nombre.
    signature_id = b.get('signature_id')
    if resultado in ('aprobado', 'no_aprobado'):
        _meaning = 'libera' if resultado == 'aprobado' else 'rechaza'
        if not _validar_e_sign_cal(cur, signature_id, record_table='movimientos',
                                   record_id=mov_id, meaning=_meaning, signer=u):
            return jsonify({'error': 'Se requiere firma electrónica (21 CFR Part 11) para disponer el lote. '
                            'Firmá con /api/sign (record_table=movimientos, record_id=' + str(mov_id) +
                            ') y reenviá signature_id.',
                            'requiere_firma': True, 'record_id': str(mov_id), 'sign_meaning': _meaning}), 400
    try:
        cur.execute("UPDATE certificado_analisis_mp SET anulado=1 WHERE mov_id=? AND COALESCE(anulado,0)=0", (mov_id,))
        _f = _F02_COLS + ['creado_por', 'creado_en']
        cur.execute(f"INSERT INTO certificado_analisis_mp ({','.join(_f)}) VALUES ({','.join(['?']*len(_f))})",
                    [vals[k] for k in _F02_COLS] + [u, _fecha_co()])
        _f02_id = cur.lastrowid  # capturar YA · _crear_nc_rechazo mueve lastrowid (su audit_log) · M22
        _liberado = 0
        if resultado in ('aprobado', 'no_aprobado'):
            # transición canónica del kardex (M23 VIGENTE/RECHAZADO · M27 CAS: solo si sigue en cuarentena)
            _nuevo = 'VIGENTE' if resultado == 'aprobado' else 'RECHAZADO'
            cur.execute("UPDATE movimientos SET estado_lote=? "
                        "WHERE UPPER(COALESCE(estado_lote,'')) IN ('CUARENTENA','CUARENTENA_EXTENDIDA') "
                        "AND lote=? AND material_id=? AND tipo='Entrada'",
                        (_nuevo, _lote, _matid))
            _liberado = cur.rowcount
        _nc_id = None
        if resultado == 'no_aprobado' and _liberado > 0:
            # MP rechazada → No Conformidad + devolución al proveedor (trazabilidad · va a Compras)
            _motivo = vals.get('observaciones_generales') or ''
            _nc_id = _crear_nc_rechazo(cur, u, lote=_lote, codigo=_matid, nombre=vals.get('nombre_mp'),
                                       cantidad=vals.get('cantidad_recibida'), proveedor=vals.get('proveedor'),
                                       oc=_oc, motivo=_motivo, es_envase=False)
        # ── VERIFICACIÓN FINAL (Laura · Sebastián 19-jul): el F02 es el rótulo final de verificación. Calidad
        # corrige lo que llegó mal ANTES de liberar (INCI/tipo/nombre al maestro · cantidad/fecha/venc/lote al
        # kardex) y fija la UBICACIÓN definitiva al aprobar. Portado del viejo cc-review (probado). Auditado.
        _corr = []
        _ubic_msg = ''
        _lote_key = _lote  # llave de lote para la ubicación (se actualiza si se corrige el lote)
        # Las correcciones (maestro + kardex + ubicación) SOLO se aplican al APROBAR (liberación · ya exige
        # e-firma Part 11). Revisor adversarial 19-jul (H1): antes corrían también en cuarentena/rechazo (sin
        # firma) y editaban el maestro GLOBAL desde un form por-lote. La verificación final es la liberación.
        if resultado == 'aprobado':
            _inci_new = (str(b.get('inci_corregido') or '')).strip()
            if _inci_new:
                _ci = cur.execute("SELECT COALESCE(nombre_inci,'') FROM maestro_mps WHERE codigo_mp=?", (_matid,)).fetchone()
                if _ci is not None and (_ci[0] or '') != _inci_new:
                    cur.execute("UPDATE maestro_mps SET nombre_inci=? WHERE codigo_mp=?", (_inci_new[:200], _matid))
                    _corr.append('INCI:' + (_ci[0] or '(vacio)') + '->' + _inci_new)
            _tipo_new = (str(b.get('tipo_material') or '')).strip().upper()
            if _tipo_new in ('MP', 'ME', 'MEMP'):
                _ct = cur.execute("SELECT COALESCE(tipo_material,'MP') FROM maestro_mps WHERE codigo_mp=?", (_matid,)).fetchone()
                if _ct is not None and (_ct[0] or 'MP') != _tipo_new:
                    cur.execute("UPDATE maestro_mps SET tipo_material=? WHERE codigo_mp=?", (_tipo_new, _matid))
                    _corr.append('Tipo:' + (_ct[0] or 'MP') + '->' + _tipo_new)
            _nom_new = (str(b.get('nombre_comercial_final') or '')).strip()
            if _nom_new:
                _cn = cur.execute("SELECT COALESCE(nombre_comercial,'') FROM maestro_mps WHERE codigo_mp=?", (_matid,)).fetchone()
                if _cn is not None and (_cn[0] or '') != _nom_new:
                    cur.execute("UPDATE maestro_mps SET nombre_comercial=? WHERE codigo_mp=?", (_nom_new[:200], _matid))
                    _corr.append('Nombre->' + _nom_new)
            try:
                _cant_new = float(b.get('cantidad_final')) if str(b.get('cantidad_final') or '').strip() != '' else None
            except Exception:
                _cant_new = None
            if _cant_new is not None and _cant_new > 0:
                _cc = cur.execute("SELECT cantidad FROM movimientos WHERE id=?", (mov_id,)).fetchone()
                if _cc is not None and abs(float(_cc[0] or 0) - _cant_new) > 0.001:
                    cur.execute("UPDATE movimientos SET cantidad=? WHERE id=?", (_cant_new, mov_id))
                    _corr.append('Cant:' + str(_cc[0]) + '->' + ('%g' % _cant_new))
            _frec_new = (str(b.get('fecha_recepcion_final') or '')).strip()
            if _frec_new:
                _cf = cur.execute("SELECT COALESCE(fecha,'') FROM movimientos WHERE id=?", (mov_id,)).fetchone()
                if _cf is not None and str(_cf[0] or '')[:10] != _frec_new[:10]:
                    cur.execute("UPDATE movimientos SET fecha=? WHERE id=?", (_frec_new, mov_id))
                    _corr.append('FRecep:' + _frec_new)
            _fv_new = (str(b.get('fecha_vencimiento_final') or '')).strip()
            if _fv_new:
                _cv = cur.execute("SELECT COALESCE(fecha_vencimiento,'') FROM movimientos WHERE id=?", (mov_id,)).fetchone()
                if _cv is not None and str(_cv[0] or '')[:10] != _fv_new[:10]:
                    cur.execute("UPDATE movimientos SET fecha_vencimiento=? WHERE material_id=? AND lote=? AND tipo='Entrada'",
                                (_fv_new, _matid, _lote_key))
                    _corr.append('FVenc:' + _fv_new)
            _lote_new = (str(b.get('lote_final') or '')).strip()
            if _lote_new and _lote_new != _lote:
                cur.execute("UPDATE movimientos SET lote=? WHERE material_id=? AND lote=?", (_lote_new, _matid, _lote))
                _corr.append('Lote:' + _lote + '->' + _lote_new)
                _lote_key = _lote_new
            _est_f = (str(b.get('estanteria_final') or '')).strip()
            _pos_f = (str(b.get('posicion_final') or '')).strip()
            if _est_f or _pos_f:
                _sets, _ps = [], []
                if _est_f:
                    _sets.append('estanteria=?'); _ps.append(_est_f[:50])
                if _pos_f:
                    _sets.append('posicion=?'); _ps.append(_pos_f[:50])
                cur.execute("UPDATE movimientos SET " + ', '.join(_sets) + " WHERE material_id=? AND lote=?",
                            _ps + [_matid, _lote_key])
                _ubic_msg = (_est_f or '-') + (('/' + _pos_f) if _pos_f else '')
        # Expediente por lote (INVIMA · zero-paper): inscribir el F02 en el registro central
        registrar_documento(cur, tipo_doc='F02', formato='COC-PRO-002-F02', titulo='Certificado de análisis de MP',
                            url='/api/calidad/certificado-analisis/imprimible?mov_id=%s' % mov_id,
                            entidad='MP', codigo=(_matid or ''), producto_nombre=(vals.get('nombre_mp') or ''),
                            lote=(vals.get('lote_proveedor') or _lote_key or ''),
                            ref_tabla='certificado_analisis_mp', ref_id=(_f02_id or 0), mov_id=mov_id,
                            firma_id=(int(signature_id) if signature_id else None), generado_por=u)
        audit_log(cur, usuario=u, accion='CERTIFICADO_ANALISIS_F02', tabla='certificado_analisis_mp',
                  registro_id=(_f02_id or 0),
                  despues={'mov_id': mov_id, 'lote': _lote_key, 'resultado': resultado, 'aprobo': aprobo_por,
                           'lotes_afectados': _liberado, 'nc_id': _nc_id, 'signature_id': signature_id,
                           'correcciones': _corr, 'ubicacion': _ubic_msg})
        conn.commit()
    except Exception as e:
        conn.rollback(); return jsonify({'error': f'No se pudo guardar F02: {e}'}), 500
    return jsonify({'ok': True, 'resultado': resultado, 'liberado': _liberado, 'nc_id': _nc_id,
                    'correcciones': _corr, 'ubicacion': _ubic_msg})


# ── F01 / F02 imprimibles (documento auditable · calca el formato en papel · imprimir→PDF) ──
def _e(v):
    import html as _h
    return _h.escape(str(v if v is not None else ''))


def _rc_doc_css():
    return ("<style>@page{size:letter;margin:15mm}*{box-sizing:border-box}"
            "body{font-family:'Inter','Segoe UI',Arial,sans-serif;color:#1e1b2e;font-size:12px;margin:0;padding:10px;"
            "-webkit-print-color-adjust:exact;print-color-adjust:exact}"
            ".hd{display:flex;justify-content:space-between;align-items:center;padding:14px 18px;margin-bottom:16px;"
            "background:linear-gradient(120deg,#f5f3ff 0%,#faf5ff 55%,#fff 100%);border:1px solid #ece9f6;border-radius:14px;"
            "border-left:5px solid var(--cx-primary, #6d28d9)}"
            ".hd .lg{display:flex;align-items:center;gap:13px}"
            ".hd .ic{width:42px;height:42px;border-radius:12px;background:linear-gradient(135deg,#a78bfa,#6d28d9);color:#fff;"
            "display:flex;align-items:center;justify-content:center;font-size:20px;font-weight:800}"
            ".hd .t{font-size:16px;font-weight:800;color:#1e1b2e;letter-spacing:-.01em}"
            ".hd .s{font-size:10px;color:#8b8b9e;margin-top:2px;letter-spacing:.02em}"
            ".hd .cod{text-align:right;font-size:10px;color:var(--cx-primary-text, #6d28d9);font-weight:700;letter-spacing:.03em}"
            ".hd .cod small{display:block;color:#a1a1b0;font-weight:500;margin-top:2px}"
            ".grid{display:grid;grid-template-columns:1fr 1fr;gap:0 22px;margin:10px 0}"
            ".fld{border-bottom:1px solid #f1f0f7;padding:7px 2px;display:flex;gap:8px;align-items:baseline}"
            ".fld .k{color:#8b8b9e;min-width:130px;font-size:9.5px;text-transform:uppercase;letter-spacing:.04em;font-weight:600}"
            ".fld .v{font-weight:600;color:#1e1b2e}"
            "table{width:100%;border-collapse:separate;border-spacing:0;margin:10px 0;font-size:11px;border:1px solid #e4e2ee;border-radius:10px;overflow:hidden}"
            "th,td{padding:8px 10px;text-align:left;border-bottom:1px solid #f1f0f7}"
            "th{background:#f7f6fb;font-size:9.5px;text-transform:uppercase;letter-spacing:.04em;color:#78788a;font-weight:700}"
            "tbody tr:last-child td{border-bottom:none}tbody tr:nth-child(even){background:#fbfbfd}"
            ".res{margin:14px 0;padding:11px 16px;border-radius:11px;font-size:13.5px;font-weight:800;letter-spacing:.01em;"
            "color:var(--cx-warn-text, #b45309);background:var(--cx-warn-pale, #fffbeb);border:1.5px solid #fde68a}"
            ".res.ok{color:var(--cx-success-text, #15803d);background:var(--cx-success-pale, #f0fdf4);border-color:#bbf7d0}"
            ".res.no{color:var(--cx-danger-text, #b91c1c);background:var(--cx-danger-pale, #fef2f2);border-color:#fecaca}"
            ".firmas{display:grid;grid-template-columns:1fr 1fr;gap:30px;margin-top:34px}"
            ".firma{border-top:1.5px solid #1e1b2e;padding-top:6px;font-size:10px;color:#78788a}"
            ".firma b{display:block;color:#1e1b2e;font-size:12.5px;margin-bottom:1px}"
            ".noimp{margin:18px 0;text-align:center}.noimp button{padding:10px 22px;font-size:13px;font-weight:700;cursor:pointer;"
            "border:none;background:linear-gradient(135deg,#a78bfa,#6d28d9);color:#fff;border-radius:11px;"
            "box-shadow:0 8px 20px -6px rgba(109,40,217,.5)}"
            "@media print{.noimp{display:none}body{padding:0}}</style>")


def _rc_head(titulo, codigo, extra=''):
    ic = '\U0001F9EA'
    return (f"<div class='hd'><div class='lg'><div class='ic'>{ic}</div>"
            f"<div><div class='t'>{_e(titulo)}</div>"
            f"<div class='s'>Espagiria Laboratorio · Control de Calidad{(' · ' + _e(extra)) if extra else ''}</div></div></div>"
            f"<div class='cod'>{_e(codigo)}<small>Versión 01</small></div></div>")


def _rc_fld(k, v):
    return f"<div class='fld'><span class='k'>{_e(k)}</span><span class='v'>{_e(v)}</span></div>"


def _rc_estado(v):
    m = {'cumple': 'Cumple', 'no_cumple': 'No cumple', 'no_aplica': 'No aplica',
         'si': 'Sí', 'no': 'No', 'na': 'N/A', '': '-'}
    return m.get((v or '').lower(), v)


def _rc_firma(c, valor):
    """Rúbrica manuscrita del firmante lista para estampar en el documento (Part 11 §11.50).

    UN solo punto de estampa para TODOS los imprimibles de Calidad (F01/F02/CoA-PT): resuelve
    por username O por nombre completo (los formatos guardan el NOMBRE del responsable) y
    devuelve '' si esa persona no tiene firma cargada. Defensivo: nunca lanza (un documento
    regulado no puede caerse porque falte una imagen).
    """
    try:
        from blueprints.firmas import firma_estampa_html as _f
    except Exception:
        try:
            from api.blueprints.firmas import firma_estampa_html as _f
        except Exception:
            return ''
    try:
        return _f(c, valor)
    except Exception:
        return ''


def _rc_fecha_firma(v):
    """Línea de fecha bajo la rúbrica (GMP: toda firma va fechada). '' si no hay fecha."""
    v = (str(v or '')).strip()
    return f"<span style='display:block;color:#a1a1b0;font-size:9px;margin-top:2px'>Fecha: {_e(v[:19])}</span>" if v else ''


@bp.route('/api/calidad/recepcion-tecnica/imprimible', methods=['GET'])
def calidad_f01_imprimible():
    """F01 imprimible (COC-PRO-002-F01) · documento auditable para PDF (imprimir desde el navegador)."""
    if 'compras_user' not in session:
        return Response('No autorizado', status=401)
    mov_id = request.args.get('mov_id')
    origen = 'MEE' if (request.args.get('origen', 'MP').upper() == 'MEE') else 'MP'
    conn = get_db(); c = conn.cursor()
    row = c.execute("SELECT * FROM recepcion_tecnica_doc WHERE mov_id=? AND COALESCE(origen,'MP')=? "
                    "AND COALESCE(anulado,0)=0 ORDER BY id DESC LIMIT 1", (mov_id, origen)).fetchone()
    if not row:
        return Response("<p style='font-family:sans-serif;padding:40px'>No hay F01 guardado para este lote.</p>",
                        mimetype='text/html')
    d = dict(zip([x[0] for x in c.description], row))
    tipo_lbl = {'materia_prima': 'Materia prima', 'envase': 'Envase', 'empaque': 'Empaque'}.get(d.get('tipo_insumo'), 'Insumo')
    crits = [('crit_rotulado', 'Rotulado completo (nombre, lote, fecha vencimiento)'),
             ('crit_empaque', 'Empaque/envase limpio e íntegro'),
             ('crit_hoja_seguridad', 'Hoja de seguridad vigente (si aplica)'),
             ('crit_ficha_tecnica', 'Ficha técnica vigente (si aplica)'),
             ('crit_coa', 'Certificado de análisis del proveedor (COA)'),
             ('crit_doc_coincide', 'Documentación coincide con el producto entregado')]
    filas = ''.join(f"<tr><td>{_e(lbl)}</td><td>{_e(_rc_estado(d.get(k)))}</td></tr>" for k, lbl in crits)
    _ok = (d.get('resultado') or '').lower() == 'conforme'
    res_cls = 'ok' if _ok else ('no' if d.get('resultado') else '')
    res_txt = 'CONFORME' if _ok else ('NO CONFORME' if d.get('resultado') else '-')
    body = (_rc_doc_css() + _rc_head('Recepción técnica y documental de insumos', 'COC-PRO-002-F01', tipo_lbl)
            + "<div class='grid'>"
            + _rc_fld('Insumo', d.get('nombre_insumo')) + _rc_fld('Código', d.get('codigo_insumo'))
            + _rc_fld('Lote proveedor', d.get('lote_proveedor')) + _rc_fld('Cantidad recibida', d.get('cantidad_recibida'))
            + _rc_fld('Proveedor', d.get('proveedor')) + _rc_fld('Fecha recepción', d.get('fecha_recepcion'))
            + _rc_fld('N° remisión/factura', d.get('numero_remision')) + _rc_fld('N° orden de compra', d.get('numero_oc'))
            + _rc_fld('Área almacenamiento', d.get('area_almacenamiento')) + _rc_fld('Fecha vencimiento', d.get('fecha_vencimiento'))
            + "</div>"
            + "<table><thead><tr><th>Verificación técnica y documental</th><th style='width:120px'>Resultado</th></tr></thead><tbody>"
            + filas + "</tbody></table>"
            + (f"<div class='fld'><span class='k'>Observaciones</span><span class='v'>{_e(d.get('observaciones'))}</span></div>" if d.get('observaciones') else '')
            + f"<div class='res {res_cls}'>Resultado de la recepción: {res_txt}</div>"
            + "<div class='firmas'>"
            + (f"<div class='firma'>{_rc_firma(c, d.get('realiza_por'))}"
               f"<b>{_e(d.get('realiza_por') or '-')}</b>Realiza la recepción{_rc_fecha_firma(d.get('realiza_fecha'))}</div>")
            + (f"<div class='firma'>{_rc_firma(c, d.get('aprueba_por'))}"
               f"<b>{_e(d.get('aprueba_por') or '-')}</b>Aprueba la recepción{_rc_fecha_firma(d.get('aprueba_fecha'))}</div>")
            + "</div>"
            + f"<p style='margin-top:18px;font-size:9px;color:var(--cx-text-faint, #94a3b8)'>Registrado por {_e(d.get('creado_por'))} · {_e((d.get('creado_en') or '')[:19])}</p>"
            + "<div class='noimp'><button onclick='window.print()'>🖨️ Imprimir / Guardar PDF</button></div>")
    return Response(body, mimetype='text/html')


@bp.route('/api/calidad/certificado-analisis/imprimible', methods=['GET'])
def calidad_f02_imprimible():
    """F02 imprimible (COC-PRO-002-F02) · certificado de análisis de MP auditable para PDF."""
    if 'compras_user' not in session:
        return Response('No autorizado', status=401)
    mov_id = request.args.get('mov_id')
    conn = get_db(); c = conn.cursor()
    row = c.execute("SELECT * FROM certificado_analisis_mp WHERE mov_id=? AND COALESCE(anulado,0)=0 "
                    "ORDER BY id DESC LIMIT 1", (mov_id,)).fetchone()
    if not row:
        return Response("<p style='font-family:sans-serif;padding:40px'>No hay F02 guardado para este lote.</p>",
                        mimetype='text/html')
    d = dict(zip([x[0] for x in c.description], row))
    params = [('aspecto', 'Aspecto / Color / Olor'), ('ph', 'pH (a 25°C)'), ('densidad', 'Densidad (g/mL)'),
              ('solubilidad', 'Solubilidad'), ('viscosidad', 'Viscosidad (cP)')]
    filas = ''.join(
        f"<tr><td>{_e(lbl)}</td><td>{_e(d.get(k + '_spec'))}</td><td>{_e(d.get(k + '_result'))}</td>"
        f"<td>{_e(_rc_estado(d.get(k + '_cumple')))}</td></tr>" for k, lbl in params)
    _r = (d.get('resultado') or '').lower()
    res_cls = 'ok' if _r == 'aprobado' else ('no' if _r == 'no_aprobado' else '')
    res_txt = {'aprobado': 'APROBADO', 'no_aprobado': 'NO APROBADO', 'cuarentena': 'PERMANECE EN CUARENTENA'}.get(_r, '-')
    body = (_rc_doc_css() + _rc_head('Certificado de análisis de materia prima', 'COC-PRO-002-F02')
            + "<div class='grid'>"
            + _rc_fld('Materia prima', d.get('nombre_mp')) + _rc_fld('Código', d.get('codigo_mp'))
            + _rc_fld('Lote proveedor', d.get('lote_proveedor')) + _rc_fld('Cantidad recibida', d.get('cantidad_recibida'))
            + _rc_fld('Proveedor', d.get('proveedor')) + _rc_fld('Fecha recepción', d.get('fecha_recepcion'))
            + _rc_fld('Fecha de análisis', d.get('fecha_analisis')) + _rc_fld('Fecha vencimiento', d.get('fecha_vencimiento'))
            + "</div>"
            + "<table><thead><tr><th>Parámetro</th><th>Especificación</th><th>Resultado</th><th style='width:90px'>Cumple</th></tr></thead><tbody>"
            + filas + "</tbody></table>"
            + (f"<div class='fld'><span class='k'>Observaciones generales</span><span class='v'>{_e(d.get('observaciones_generales'))}</span></div>" if d.get('observaciones_generales') else '')
            + f"<div class='res {res_cls}'>Concepto de calidad: {res_txt}</div>"
            + "<div class='firmas'>"
            + (f"<div class='firma'>{_rc_firma(c, d.get('responsable_analisis'))}"
               f"<b>{_e(d.get('responsable_analisis') or '-')}</b>Realiza el análisis{_rc_fecha_firma(d.get('realiza_fecha'))}</div>")
            + (f"<div class='firma'>{_rc_firma(c, d.get('aprobo_por'))}"
               f"<b>{_e(d.get('aprobo_por') or '-')}</b>Aprueba · Jefe de Control de Calidad{_rc_fecha_firma(d.get('aprobo_fecha'))}</div>")
            + "</div>"
            + f"<p style='margin-top:18px;font-size:9px;color:var(--cx-text-faint, #94a3b8)'>Registrado por {_e(d.get('creado_por'))} · {_e((d.get('creado_en') or '')[:19])}</p>"
            + "<div class='noimp'><button onclick='window.print()'>🖨️ Imprimir / Guardar PDF</button></div>")
    return Response(body, mimetype='text/html')


@bp.route('/api/calidad/coa-pt/<path:lote>/imprimible', methods=['GET'])
def calidad_coa_pt_imprimible(lote):
    """Certificado de Análisis del PRODUCTO TERMINADO por lote (micro + fisicoquímico) · imprimible/PDF.
    Agrega calidad_micro_resultados + calidad_fisicoquimica_resultados del lote en UN certificado (Fase 2)."""
    if 'compras_user' not in session:
        return Response('No autorizado', status=401)
    return coa_pt_imprimible(lote)


def coa_pt_imprimible(lote):
    """El COA de PT SIN el gate de sesión interna · lo comparten Calidad y el portal.

    Extraído 14-ago-2026: el cliente B2B necesita el certificado de SU lote y ese documento ya
    existía acá. El portal lo sirve validando PROPIEDAD del lote (que salga de un pedido suyo)
    en vez de `compras_user`; el documento es el MISMO, así que no se reimplementa (M3).
    """
    lote = (lote or '').strip()
    conn = get_db(); c = conn.cursor()
    try:
        micro = c.execute(
            "SELECT microorganismo, COALESCE(valor_texto, CAST(valor AS TEXT), ''), COALESCE(unidad,''), "
            "COALESCE(estado,''), COALESCE(metodo,''), COALESCE(producto_nombre,''), "
            "COALESCE(analista,''), COALESCE(creado_por,''), COALESCE(fecha_analisis,'') "
            "FROM calidad_micro_resultados WHERE lote=? ORDER BY id", (lote,)).fetchall()
    except Exception:
        micro = []
    try:
        fq = c.execute(
            "SELECT parametro, COALESCE(resultado,''), COALESCE(unidad,''), COALESCE(valor_referencia,''), "
            "COALESCE(estado,''), COALESCE(producto_nombre,''), "
            "COALESCE(analista,''), COALESCE(creado_por,''), COALESCE(fecha_analisis,'') "
            "FROM calidad_fisicoquimica_resultados WHERE lote=? ORDER BY id", (lote,)).fetchall()
    except Exception:
        fq = []
    if not micro and not fq:
        return Response("<p style='font-family:sans-serif;padding:40px'>No hay resultados de análisis registrados para el lote %s.</p>" % _e(lote),
                        mimetype='text/html')
    producto = ''
    for r in micro:
        if r[5]:
            producto = r[5]; break
    if not producto:
        for r in fq:
            if r[5]:
                producto = r[5]; break
    _mal = lambda s: (s or '').lower() in ('fuera_meta', 'fuera_industria', 'no_conforme', 'no_informado')
    hay_fuera = any(_mal(r[3]) for r in micro) or any(_mal(r[4]) for r in fq)
    _map = {'ok': 'Conforme', 'fuera_meta': 'Fuera de meta', 'fuera_industria': 'Fuera de límite',
            'observacion': 'Observación', 'informado': 'Informado', 'conforme': 'Conforme', 'no_conforme': 'No conforme'}
    _estl = lambda s: _map.get((s or '').lower(), s or '-')
    filas_m = ''.join("<tr><td>%s</td><td>%s %s</td><td>%s</td><td>%s</td></tr>"
                      % (_e(r[0]), _e(r[1]), _e(r[2]), _e(r[4]), _e(_estl(r[3]))) for r in micro)
    filas_f = ''.join("<tr><td>%s</td><td>%s %s</td><td>%s</td><td>%s</td></tr>"
                      % (_e(r[0]), _e(r[1]), _e(r[2]), _e(r[3]), _e(_estl(r[4]))) for r in fq)
    # Firmante del CoA-PT: el ANALISTA que registró los resultados (analista, o quien lo cargó).
    # No se inventa un aprobador: si nadie firmó la aprobación, la línea queda en blanco (GMP).
    analista = ''
    for r in list(micro) + list(fq):
        if (r[6] or '').strip():
            analista = r[6].strip(); break
    if not analista:
        for r in list(micro) + list(fq):
            if (r[7] or '').strip():
                analista = r[7].strip(); break
    fecha_an = ''
    for r in list(micro) + list(fq):
        if (r[8] or '').strip():
            fecha_an = r[8].strip(); break
    body = (_rc_doc_css() + _rc_head('Certificado de análisis de producto terminado', 'COC-PRO-002 · CoA PT')
            + "<div class='grid'>" + _rc_fld('Producto', producto) + _rc_fld('Lote', lote)
            + (_rc_fld('Fecha de análisis', fecha_an) if fecha_an else '') + "</div>"
            + (("<table><thead><tr><th>Microorganismo</th><th>Resultado</th><th>Método</th><th style='width:110px'>Concepto</th></tr></thead><tbody>"
                + filas_m + "</tbody></table>") if micro else '')
            + (("<table><thead><tr><th>Parámetro fisicoquímico</th><th>Resultado</th><th>Referencia</th><th style='width:110px'>Concepto</th></tr></thead><tbody>"
                + filas_f + "</tbody></table>") if fq else '')
            + ("<div class='res %s'>Concepto de calidad: %s</div>"
               % (('no' if hay_fuera else 'ok'), ('CON OBSERVACIONES' if hay_fuera else 'CONFORME')))
            + "<div class='firmas'>"
            + ("<div class='firma'>%s<b>%s</b>Realiza el análisis%s</div>"
               % (_rc_firma(c, analista), _e(analista or '-'), _rc_fecha_firma(fecha_an)))
            + "<div class='firma'><b>-</b>Aprueba · Jefe de Control de Calidad</div></div>"
            + "<div class='noimp'><button onclick='window.print()'>🖨️ Imprimir / Guardar PDF</button></div>")
    return Response(body, mimetype='text/html')


# ══════════════════════════════════════════════════════════════════════════════
# EXPEDIENTE POR LOTE · zero-paper INVIMA · Sebastián 24-jul
# Registro central `documentos_regulados` (mig 371): reconstruir (backfill) + buscar + página.
# REGLA (cerebro): todo documento regulado nuevo se inscribe con registrar_documento().
# ══════════════════════════════════════════════════════════════════════════════
# Sólo POST (8-ago): aceptaba GET, así que cualquier precarga del navegador o un barrido de
# rutas disparaba el backfill entero (52 documentos en la base de pruebas). Es idempotente,
# así que no duplicaba, pero una acción que ESCRIBE no se ejecuta por mirar una URL (M113).
# La pantalla ya lo llama por POST con su token CSRF: nadie pierde nada.
@bp.route('/api/calidad/reconstruir-expediente', methods=['POST'])
def calidad_reconstruir_expediente():
    """Backfill del registro central desde las tablas origen (F01, F02, EBR + rótulo derivado).
    Re-ejecutable (idempotente vía registrar_documento · dedup por tipo+mov/ref). Admin/Calidad."""
    err, code = _require_calidad()
    if err:
        return err, code
    conn = get_db(); c = conn.cursor()
    n_f01 = n_f02 = n_ebr = 0
    try:
        for r in c.execute(
                "SELECT rt.id, rt.mov_id, COALESCE(rt.origen,'MP'), "
                "COALESCE(NULLIF(TRIM(rt.codigo_insumo),''), COALESCE(mv.material_id,'')), "
                "COALESCE(NULLIF(TRIM(rt.nombre_insumo),''), COALESCE(mv.material_nombre,'')), "
                "COALESCE(NULLIF(TRIM(rt.lote_proveedor),''), NULLIF(TRIM(rt.lote),''), COALESCE(mv.lote,'')), "
                "COALESCE(rt.creado_por,''), COALESCE(rt.creado_en,'') "
                "FROM recepcion_tecnica_doc rt LEFT JOIN movimientos mv ON mv.id=rt.mov_id "
                "WHERE COALESCE(rt.anulado,0)=0").fetchall():
            registrar_documento(c, tipo_doc='F01', formato='COC-PRO-002-F01', titulo='Recepción técnica y documental',
                                url='/api/calidad/recepcion-tecnica/imprimible?mov_id=%s&origen=%s' % (r[1], r[2]),
                                entidad=r[2], codigo=r[3] or '', producto_nombre=r[4] or '', lote=r[5] or '',
                                ref_tabla='recepcion_tecnica_doc', ref_id=r[0], mov_id=r[1], generado_por=r[6], generado_at=(r[7] or None))
            if (r[3] or ''):
                _ru = ('/rotulo-recepcion-mee/%s/1' % _urlq(r[3])) if r[2] == 'MEE' else ('/rotulo-recepcion/%s/%s/1' % (_urlq(r[3]), _urlq(r[5] or 'SL')))
                registrar_documento(c, tipo_doc='ROTULO', formato='COC-PRO-002-F07', titulo='Rótulo de ingreso',
                                    url=_ru, entidad=r[2], codigo=r[3] or '', producto_nombre=r[4] or '', lote=r[5] or '',
                                    ref_tabla='recepcion_tecnica_doc', ref_id='rot-%s' % r[0], mov_id=r[1], generado_por=r[6], generado_at=(r[7] or None))
            n_f01 += 1
        for r in c.execute(
                "SELECT ca.id, ca.mov_id, COALESCE(mv.material_id,''), COALESCE(ca.nombre_mp, mv.material_nombre,''), "
                "COALESCE(NULLIF(TRIM(ca.lote_proveedor),''), COALESCE(mv.lote,'')), COALESCE(ca.creado_por,''), COALESCE(ca.creado_en,'') "
                "FROM certificado_analisis_mp ca LEFT JOIN movimientos mv ON mv.id=ca.mov_id "
                "WHERE COALESCE(ca.anulado,0)=0").fetchall():
            registrar_documento(c, tipo_doc='F02', formato='COC-PRO-002-F02', titulo='Certificado de análisis de MP',
                                url='/api/calidad/certificado-analisis/imprimible?mov_id=%s' % r[1],
                                entidad='MP', codigo=r[2] or '', producto_nombre=r[3] or '', lote=r[4] or '',
                                ref_tabla='certificado_analisis_mp', ref_id=r[0], mov_id=r[1], generado_por=r[5], generado_at=(r[6] or None))
            n_f02 += 1
        for r in c.execute(
                "SELECT e.id, COALESCE(e.numero_op,''), COALESCE(m.producto_nombre,''), "
                "COALESCE(e.lote_codigo, e.lote, ''), COALESCE(e.liberado_por, e.iniciado_por,''), "
                "COALESCE(e.liberado_at_utc, e.iniciado_at_utc,'') FROM ebr_ejecuciones e "
                "LEFT JOIN mbr_templates m ON m.id=e.mbr_template_id").fetchall():
            registrar_documento(c, tipo_doc='EBR', formato='Batch Record', titulo='Registro de lote (batch record)',
                                url='/api/brd/ebr/%s/vista-completa' % r[0], entidad='PT',
                                codigo=r[1] or '', producto_nombre=r[2] or '', lote=r[3] or '',
                                ref_tabla='ebr_ejecuciones', ref_id=r[0], generado_por=r[4], generado_at=(r[5] or None))
            n_ebr += 1
        # Rótulos de limpieza F02 (Fase 2 · solo los que tienen lote de producción · URL por-registro estable)
        n_rot = 0
        try:
            for r in c.execute(
                    "SELECT id, COALESCE(area_codigo,''), COALESCE(producto_elaborar,''), COALESCE(lote_elaborar,''), "
                    "COALESCE(realizado_por, verificado_por,''), COALESCE(realizado_at, creado_en,'') "
                    "FROM rotulos_limpieza WHERE COALESCE(TRIM(lote_elaborar),'')<>''").fetchall():
                registrar_documento(c, tipo_doc='ROTULO_LIMPIEZA', formato='PRD-PRO-002-F02',
                                    titulo='Rótulo de limpieza de área/equipos',
                                    url='/planta/rotulo-limpieza/registro/%s/pdf' % r[0], entidad='PT',
                                    codigo=r[1] or '', producto_nombre=r[2] or '', lote=r[3] or '',
                                    ref_tabla='rotulos_limpieza', ref_id=r[0], generado_por=r[4], generado_at=(r[5] or None))
                n_rot += 1
        except Exception:
            n_rot = 0
        # CoA de PT (micro + fisicoquímico) · UN documento por lote (agrega los resultados) · imprimible propio
        n_coa = 0
        try:
            _lotes_coa = {}
            for tabla in ('calidad_micro_resultados', 'calidad_fisicoquimica_resultados'):
                try:
                    for r in c.execute("SELECT DISTINCT COALESCE(TRIM(lote),''), COALESCE(producto_nombre,''), "
                                       "MAX(COALESCE(creado_en,'')) FROM %s WHERE COALESCE(TRIM(lote),'')<>'' "
                                       "GROUP BY COALESCE(TRIM(lote),''), COALESCE(producto_nombre,'')" % tabla).fetchall():
                        if r[0]:
                            _lotes_coa[r[0]] = (r[1] or _lotes_coa.get(r[0], ('', ''))[0], r[2] or '')
                except Exception:
                    pass
            for _lt, (_prod, _at) in _lotes_coa.items():
                registrar_documento(c, tipo_doc='COA_PT', formato='CoA producto terminado',
                                    titulo='Certificado de análisis del producto terminado',
                                    url='/api/calidad/coa-pt/%s/imprimible' % _urlq(_lt), entidad='PT',
                                    producto_nombre=_prod, lote=_lt,
                                    ref_tabla='coa_pt', ref_id=_lt, generado_at=(_at or None))
                n_coa += 1
        except Exception:
            n_coa = 0
        conn.commit()
    except Exception as e:
        conn.rollback()
        return jsonify({'error': 'falló el backfill: %s' % e}), 500
    return jsonify({'ok': True, 'f01': n_f01, 'f02': n_f02, 'ebr': n_ebr, 'rotulo_limpieza': n_rot,
                    'coa_pt': n_coa, 'total': n_f01 + n_f02 + n_ebr + n_rot + n_coa})


@bp.route('/api/calidad/archivar-r2', methods=['GET', 'POST'])
def calidad_archivar_r2():
    """Fase 2b · sube a Cloudflare R2 (archivo inmutable off-site) los documentos regulados que aún
    no tienen snapshot. GET = solo estado (archivados/pendientes); POST = archiva un lote (hasta 200).
    Best-effort · idempotente (solo toma pendientes) · admin/Calidad."""
    err, code = _require_calidad()
    if err:
        return err, code
    try:
        from r2_storage import r2_configurado, r2_stats_expediente, archivar_pendientes_r2
    except Exception:
        from api.r2_storage import r2_configurado, r2_stats_expediente, archivar_pendientes_r2  # pragma: no cover
    from flask import current_app
    if request.method == 'GET':
        return jsonify({'ok': True, 'estado': r2_stats_expediente(get_db())})
    if not r2_configurado():
        return jsonify({'ok': False, 'error': 'R2 no está configurado en el servidor (faltan variables R2_*)'}), 400
    # Lote MODESTO + presupuesto de reloj corto (M89/M91): el request nunca retiene el worker cerca del
    # --timeout 120 · el JS del modal reinvoca en bucle mientras queden 'pendientes' (drena el backlog).
    res = archivar_pendientes_r2(current_app._get_current_object(), limite=25, presupuesto_seg=35)
    return jsonify(res)


@bp.route('/api/calidad/expediente-lote', methods=['GET'])
def calidad_expediente_lote():
    """Expediente de un lote: todos sus documentos regulados. ?q=<lote, código o producto>."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    q = (request.args.get('q') or '').strip()
    if not q:
        return jsonify({'ok': True, 'grupos': [], 'n': 0})
    conn = get_db(); c = conn.cursor()
    like = '%' + q.upper() + '%'
    rows = c.execute(
        "SELECT entidad, codigo, producto_nombre, lote, tipo_doc, formato, titulo, url, generado_por, generado_at "
        "FROM documentos_regulados WHERE COALESCE(anulado,0)=0 AND ("
        "UPPER(COALESCE(lote,'')) LIKE ? OR UPPER(COALESCE(codigo,'')) LIKE ? OR UPPER(COALESCE(producto_nombre,'')) LIKE ?) "
        "ORDER BY lote, tipo_doc LIMIT 400", (like, like, like)).fetchall()
    grupos = {}
    for r in rows:
        d = {'entidad': r[0], 'codigo': r[1], 'producto': r[2], 'lote': r[3], 'tipo': r[4], 'formato': r[5],
             'titulo': r[6], 'url': r[7], 'por': r[8], 'fecha': r[9]}
        k = (d['lote'] or '(sin lote)') + '|' + (d['codigo'] or '')
        grupos.setdefault(k, {'lote': d['lote'], 'codigo': d['codigo'], 'producto': d['producto'],
                              'entidad': d['entidad'], 'docs': []})
        grupos[k]['docs'].append(d)
    return jsonify({'ok': True, 'n': len(rows), 'grupos': list(grupos.values())})


def _equipo_calibracion(c, equipo_codigo):
    """Estado de calibración de un equipo (para la genealogía · INVIMA): {ultima, proxima, vigente}.
    Lee equipos_eventos (tipo_evento='calibracion') · fallback a la tabla legacy `calibraciones`. Read-only."""
    if not equipo_codigo:
        return None
    r = None
    try:
        r = c.execute("SELECT COALESCE(fecha,''), COALESCE(fecha_proxima,'') FROM equipos_eventos "
                      "WHERE equipo_codigo=? AND tipo_evento='calibracion' AND COALESCE(estado,'')<>'cancelado' "
                      "ORDER BY fecha DESC LIMIT 1", (equipo_codigo,)).fetchone()
    except Exception:
        r = None
    if not r or not ((r[0] or '') or (r[1] or '')):
        try:
            r = c.execute("SELECT COALESCE(fecha_ultima,''), COALESCE(fecha_proxima,'') FROM calibraciones "
                          "WHERE codigo=? ORDER BY id DESC LIMIT 1", (equipo_codigo,)).fetchone()
        except Exception:
            r = None
    if not r or not ((r[0] or '') or (r[1] or '')):
        return None
    ultima, proxima = (r[0] or '')[:10], (r[1] or '')[:10]
    vigente = None
    if proxima:
        try:
            hoy = (datetime.utcnow() - timedelta(hours=5)).date().isoformat()  # Colombia (M24)
            vigente = (proxima >= hoy)
        except Exception:
            vigente = None
    return {'ultima': ultima, 'proxima': proxima, 'vigente': vigente}


def _equipos_con_calibracion(c, area_codigo):
    """Equipos del área con su estado de calibración (genealogía · INVIMA).

    OJO: `_equipos_de_area` devuelve DICTS ({'codigo','nombre','tipo'}), no tuplas. Indexarlos
    como tuplas (e[0]) lanza KeyError y, envuelto en un `except` mudo, dejaba la lista de
    equipos SIEMPRE vacía sin que nadie se enterara (cazado con el E2E del flujo real 24-jul).
    El try se conserva (una vista read-only regulada no debe caerse) pero AHORA LOGUEA.
    """
    try:
        try:
            from blueprints.programacion import _equipos_de_area
        except Exception:
            from api.blueprints.programacion import _equipos_de_area
        return [{'codigo': e['codigo'], 'nombre': e.get('nombre') or '', 'tipo': e.get('tipo') or '',
                 'calibracion': _equipo_calibracion(c, e['codigo'])}
                for e in (_equipos_de_area(c, area_codigo) or [])]
    except Exception as _e:
        __import__('logging').getLogger('calidad').warning(
            'genealogia · equipos del area %s no resolvieron: %s', area_codigo, _e)
        return []


@bp.route('/api/calidad/genealogia-pt/<path:lote>', methods=['GET'])
def calidad_genealogia_pt(lote):
    """GENEALOGÍA hacia atrás de un lote de PRODUCTO TERMINADO (INVIMA · trazabilidad Fase 1).
    Dado el lote de PT devuelve el árbol: batch record (EBR OP/OF/OA) + liberación, materias primas
    consumidas con SU lote de proveedor + documentos (F01/F02/ROTULO/COA), área+equipos de fabricación
    y de envasado, y envases (MEE) consumidos. Ancla en produccion_id (mig 201) · fallback tag FEFO para
    Fabricación directa · read-only (no muta nada)."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    lote = (lote or '').strip()
    if not lote:
        return jsonify({'ok': False, 'error': 'lote vacío'}), 400
    conn = get_db(); c = conn.cursor()
    out = {'ok': True, 'lote': lote, 'encontrado': False, 'producto': '', 'pt_estado': '', 'pt_fecha': '',
           'fases': [], 'liberacion': None, 'materias_primas': [], 'envases': [], 'areas': {}, 'docs_pt': [],
           'fuente_mp': ''}
    _FASE_LBL = {'fabricacion': 'Fabricación', 'envasado': 'Envasado', 'acondicionamiento': 'Acondicionamiento'}
    # 1) EBRs del lote físico (todas las fases OP/OF/OA)
    try:
        ebrs = c.execute(
            "SELECT e.id, COALESCE(e.lote_codigo,e.lote), COALESCE(e.fase,'fabricacion'), e.produccion_id, "
            "COALESCE(m.producto_nombre,''), COALESCE(e.numero_op,''), COALESCE(e.estado,''), "
            "COALESCE(e.liberado_por,''), COALESCE(e.liberado_at_utc,''), e.liberado_signature_id, "
            "e.cantidad_real_g, e.cantidad_objetivo_g, COALESCE(e.area_codigo,'') "
            "FROM ebr_ejecuciones e LEFT JOIN mbr_templates m ON m.id=e.mbr_template_id "
            "WHERE COALESCE(e.lote_codigo,e.lote)=? "
            "ORDER BY CASE COALESCE(e.fase,'fabricacion') WHEN 'fabricacion' THEN 0 WHEN 'envasado' THEN 1 "
            "WHEN 'acondicionamiento' THEN 2 ELSE 3 END", (lote,)).fetchall()
    except Exception:
        ebrs = []
    prod_ids = []
    for r in ebrs:
        out['encontrado'] = True
        if r[4] and not out['producto']:
            out['producto'] = r[4]
        if r[3] and r[3] not in prod_ids:
            prod_ids.append(r[3])
        out['fases'].append({
            'ebr_id': r[0], 'fase': r[2], 'fase_label': _FASE_LBL.get(r[2], r[2]),
            'numero_op': r[5], 'estado': r[6], 'liberado_por': r[7], 'liberado_at': (r[8] or '')[:19],
            'cantidad_real_g': r[10], 'cantidad_objetivo_g': r[11], 'area_codigo': r[12],
            'url': '/api/brd/ebr/%s/vista-completa' % r[0]})
        if r[7] and not out['liberacion']:
            out['liberacion'] = {'por': r[7], 'at': (r[8] or '')[:19], 'fase': r[2], 'firma_id': r[9]}
    # 2) MP consumidas · canónico por produccion_id, fallback FEFO tag (Fabricación directa)
    mp_rows = []
    if prod_ids:
        ph = ','.join('?' for _ in prod_ids)
        try:
            mp_rows = c.execute(
                "SELECT material_id, material_nombre, COALESCE(lote,''), SUM(cantidad) FROM movimientos "
                "WHERE tipo='Salida' AND produccion_id IN (%s) "
                "GROUP BY material_id, material_nombre, COALESCE(lote,'')" % ph, tuple(prod_ids)).fetchall()
            out['fuente_mp'] = 'produccion_id'
        except Exception:
            mp_rows = []
    if not mp_rows:
        try:
            mp_rows = c.execute(
                "SELECT material_id, material_nombre, COALESCE(lote,''), SUM(cantidad) FROM movimientos "
                "WHERE tipo='Salida' AND observaciones LIKE ? "
                "GROUP BY material_id, material_nombre, COALESCE(lote,'')", ('FEFO:' + lote + ':%',)).fetchall()
            if mp_rows:
                out['fuente_mp'] = 'fefo_tag'
        except Exception:
            mp_rows = []
    for r in mp_rows:
        mid, mnombre, mlote, gtot = r[0], r[1], r[2], r[3]
        if not mid or (mid or '').upper().startswith('PT'):
            continue  # no listar el PT como si fuera MP
        mp = {'material_id': mid, 'material_nombre': mnombre or '', 'lote_mp': mlote,
              'gramos': round(gtot or 0, 2), 'proveedor': '', 'numero_oc': '', 'numero_factura': '',
              'fecha_vencimiento': '', 'estado_lote': '', 'docs': []}
        if mlote:
            det = c.execute(
                "SELECT COALESCE(proveedor,''), COALESCE(numero_oc,''), COALESCE(numero_factura,''), "
                "COALESCE(fecha_vencimiento,''), COALESCE(estado_lote,'') FROM movimientos "
                "WHERE lote=? AND material_id=? AND tipo='Entrada' ORDER BY id DESC LIMIT 1", (mlote, mid)).fetchone()
            if det:
                mp['proveedor'], mp['numero_oc'], mp['numero_factura'], mp['fecha_vencimiento'], mp['estado_lote'] = det
            for d in c.execute(
                    "SELECT tipo_doc, formato, titulo, url, COALESCE(r2_key,'') FROM documentos_regulados "
                    "WHERE COALESCE(anulado,0)=0 AND lote=? ORDER BY tipo_doc", (mlote,)).fetchall():
                mp['docs'].append({'tipo': d[0], 'formato': d[1], 'titulo': d[2], 'url': d[3], 'en_r2': bool(d[4])})
        out['materias_primas'].append(mp)
    out['materias_primas'].sort(key=lambda x: (x['material_nombre'] or x['material_id']))
    # 3) Áreas de fabricación + envasado (via produccion_programada) + equipos del área
    if prod_ids:
        ph = ','.join('?' for _ in prod_ids)
        try:
            arow = c.execute("SELECT MAX(area_id), MAX(area_envasado_id) FROM produccion_programada WHERE id IN (%s)" % ph,
                             tuple(prod_ids)).fetchone()
        except Exception:
            arow = None
        for _slot, _aid in (('fabricacion', arow[0] if arow else None), ('envasado', arow[1] if arow else None)):
            if _aid:
                ar = c.execute("SELECT codigo, nombre FROM areas_planta WHERE id=?", (_aid,)).fetchone()
                if ar:
                    out['areas'][_slot] = {'codigo': ar[0], 'nombre': ar[1],
                                           'equipos': _equipos_con_calibracion(c, ar[0])}
    # Fallback (Fabricación directa · sin produccion_id → sin área por produccion_programada): tomar el
    # área del `area_codigo` del EBR (que se elige al fabricar). Read-only · así el flujo real ve su área.
    if not out['areas']:
        for _f in out['fases']:
            _ac = (_f.get('area_codigo') or '').strip()
            if not _ac:
                continue
            _slot = 'envasado' if _f.get('fase') == 'envasado' else 'fabricacion'
            if _slot in out['areas']:
                continue
            _ar = c.execute("SELECT codigo, nombre FROM areas_planta WHERE codigo=?", (_ac,)).fetchone()
            if _ar:
                out['areas'][_slot] = {'codigo': _ar[0], 'nombre': _ar[1],
                                       'equipos': _equipos_con_calibracion(c, _ar[0])}
    # 4) Envases (MEE) consumidos · por lote en observaciones/batch_ref
    try:
        for r in c.execute(
                "SELECT mee_codigo, SUM(cantidad) FROM movimientos_mee WHERE tipo='Salida' AND COALESCE(anulado,0)=0 "
                "AND (observaciones LIKE ? OR batch_ref=?) GROUP BY mee_codigo", ('%' + lote + '%', lote)).fetchall():
            if r[0]:
                nombre = ''
                try:
                    mr = c.execute("SELECT COALESCE(descripcion,'') FROM maestro_mee WHERE codigo=?", (r[0],)).fetchone()
                    nombre = mr[0] if mr else ''
                except Exception:
                    nombre = ''
                out['envases'].append({'mee_codigo': r[0], 'nombre': nombre, 'cantidad': round(r[1] or 0, 2)})
    except Exception:
        pass
    # 5) Documentos a nivel PT (batch record, rótulo del PT) + estado del lote en el kardex
    for d in c.execute(
            "SELECT tipo_doc, formato, titulo, url, COALESCE(r2_key,'') FROM documentos_regulados "
            "WHERE COALESCE(anulado,0)=0 AND lote=? ORDER BY tipo_doc", (lote,)).fetchall():
        out['docs_pt'].append({'tipo': d[0], 'formato': d[1], 'titulo': d[2], 'url': d[3], 'en_r2': bool(d[4])})
    try:
        pt = c.execute("SELECT COALESCE(estado_lote,''), COALESCE(fecha,'') FROM movimientos "
                       "WHERE lote=? AND tipo='Entrada' AND material_id LIKE 'PT_%' ORDER BY id DESC LIMIT 1",
                       (lote,)).fetchone()
        if pt:
            out['encontrado'] = True
            out['pt_estado'] = pt[0]
            out['pt_fecha'] = (pt[1] or '')[:19]
    except Exception:
        pass
    # 6) Análisis del PT (micro + fisicoquímico) por lote · read-only desde su tabla (Fase 2 · aún NO
    # inscritos como documento_regulado · se muestran directo para que la genealogía quede completa).
    out['analisis'] = {'micro': [], 'fisicoquimico': []}
    try:
        for r in c.execute(
                "SELECT microorganismo, COALESCE(valor_texto, CAST(valor AS TEXT), ''), COALESCE(unidad,''), "
                "COALESCE(estado,''), COALESCE(fecha_analisis,''), COALESCE(laboratorio,'') "
                "FROM calidad_micro_resultados WHERE lote=? ORDER BY id", (lote,)).fetchall():
            out['analisis']['micro'].append({'param': r[0], 'valor': r[1], 'unidad': r[2],
                                             'estado': r[3], 'fecha': (r[4] or '')[:10], 'lab': r[5]})
    except Exception:
        pass
    try:
        for r in c.execute(
                "SELECT parametro, COALESCE(resultado,''), COALESCE(unidad,''), COALESCE(valor_referencia,''), "
                "COALESCE(estado,''), COALESCE(fecha_analisis,''), COALESCE(laboratorio,'') "
                "FROM calidad_fisicoquimica_resultados WHERE lote=? ORDER BY id", (lote,)).fetchall():
            out['analisis']['fisicoquimico'].append({'param': r[0], 'resultado': r[1], 'unidad': r[2],
                                                     'referencia': r[3], 'estado': r[4], 'fecha': (r[5] or '')[:10], 'lab': r[6]})
    except Exception:
        pass
    # 7) Limpieza de área/equipos por lote (rótulos F02) · por produccion_id
    out['limpieza'] = []
    if prod_ids:
        _ph = ','.join('?' for _ in prod_ids)
        try:
            for r in c.execute(
                    "SELECT r.area_codigo, COALESCE(a.nombre,''), COALESCE(r.estado,''), COALESCE(r.realizado_por,''), "
                    "COALESCE(r.realizado_at,''), COALESCE(r.verificado_por,''), COALESCE(r.verificado_at,'') "
                    "FROM rotulos_limpieza r LEFT JOIN areas_planta a ON a.id=r.area_id "
                    "WHERE r.produccion_id IN (%s) ORDER BY r.id" % _ph, tuple(prod_ids)).fetchall():
                out['limpieza'].append({'area_codigo': r[0], 'area_nombre': r[1], 'estado': r[2],
                                        'realizado_por': r[3], 'realizado_at': (r[4] or '')[:19],
                                        'verificado_por': r[5], 'verificado_at': (r[6] or '')[:19]})
        except Exception:
            pass
    # 8) Liberación final (acondicionamiento → stock PT) por lote
    out['liberacion_final'] = None
    try:
        lf = c.execute(
            "SELECT COALESCE(producto,''), COALESCE(unidades,0), COALESCE(presentacion,''), "
            "COALESCE(fecha_produccion,''), COALESCE(destino,'') FROM liberaciones WHERE lote=? ORDER BY id DESC LIMIT 1",
            (lote,)).fetchone()
        if lf:
            out['liberacion_final'] = {'producto': lf[0], 'unidades': lf[1], 'presentacion': lf[2],
                                       'fecha': (lf[3] or '')[:19], 'destino': lf[4]}
    except Exception:
        pass
    return jsonify(out)


@bp.route('/calidad/genealogia', methods=['GET'])
def calidad_genealogia_page():
    """Página · Genealogía de lote de PT (INVIMA · trazabilidad hacia atrás): buscá un lote de producto
    terminado y ves el árbol completo (MP con lotes + docs, área/equipos, envasado, liberación)."""
    if 'compras_user' not in session:
        return redirect('/login?next=/calidad/genealogia')
    return Response(_GENEALOGIA_HTML, mimetype='text/html')


_GENEALOGIA_HTML = r"""<!DOCTYPE html><html lang="es" translate="no"><head><meta charset="UTF-8">
<meta name="google" content="notranslate">
<meta name="viewport" content="width=device-width,initial-scale=1.0,viewport-fit=cover"><title>Genealogía de lote · Calidad · EOS</title>
<link rel="stylesheet" href="/static/cortex.css?v=eos15">
<script>(function(){try{var t=localStorage.getItem("cx-theme");if(t==="dark")document.documentElement.setAttribute("data-theme","dark");}catch(e){}})();</script>
<style>
body{background:var(--cx-bg);color:var(--cx-text);margin:0;font-family:'Inter',system-ui,-apple-system,sans-serif;}
*{box-sizing:border-box}
.wrap{max-width:1160px;margin:0 auto;padding:22px 22px 70px;}
.intro{color:var(--cx-text-mute);font-size:13.5px;line-height:1.55;max-width:860px;margin:0 0 16px;}
.card{background:var(--cx-card);border:1px solid var(--cx-hairline);border-radius:18px;box-shadow:0 1px 3px rgba(15,23,42,.04),0 10px 30px rgba(15,23,42,.05);padding:20px 22px;margin-bottom:16px;}
.searchbar{display:flex;gap:10px;flex-wrap:wrap;align-items:center;}
#q{flex:1;min-width:280px;font-size:15px;}
#msg{font-size:12.5px;font-weight:700;}
/* árbol */
.pt-hd{display:flex;align-items:center;gap:14px;flex-wrap:wrap;}
.pt-hd .em{font-size:34px;line-height:1}
.pt-hd h2{font-size:22px;margin:0;letter-spacing:-.02em;color:var(--cx-text);}
.pt-hd .lote{font-family:ui-monospace,monospace;font-size:13px;color:var(--cx-primary-text);font-weight:800;}
.chips{display:flex;gap:7px;flex-wrap:wrap;margin-top:8px;}
.chip{display:inline-flex;align-items:center;gap:5px;font-size:11.5px;font-weight:700;padding:4px 11px;border-radius:999px;border:1px solid var(--cx-hairline);color:var(--cx-text-soft);}
.chip.ok{color:var(--cx-success-text, #15803d);background:rgba(21,128,61,.10);border-color:rgba(21,128,61,.3)}
.chip.q{color:var(--cx-warn-text, #b45309);background:rgba(180,83,9,.10);border-color:rgba(180,83,9,.3)}
.chip.r{color:var(--cx-danger-text, #b91c1c);background:rgba(185,28,28,.10);border-color:rgba(185,28,28,.3)}
.sec{margin-top:20px;}
.sec-h{display:flex;align-items:center;gap:8px;font-size:13px;font-weight:800;color:var(--cx-text);text-transform:uppercase;letter-spacing:.05em;margin:0 0 10px;}
.sec-h .n{font-size:11px;color:var(--cx-text-mute);font-weight:700;}
.branch{border-left:2px solid var(--cx-hairline);padding-left:16px;margin-left:6px;}
.mp{background:var(--cx-bg-alt);border:1px solid var(--cx-hairline);border-radius:13px;padding:13px 15px;margin-bottom:10px;}
.mp .top{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;align-items:baseline;}
.mp .nm{font-size:14px;font-weight:800;color:var(--cx-text);}
.mp .cod{font-family:ui-monospace,monospace;font-size:11px;color:var(--cx-text-mute);}
.mp .meta{font-size:11.5px;color:var(--cx-text-mute);margin-top:5px;line-height:1.5;}
.mp .meta b{color:var(--cx-text-soft);font-weight:700;}
.mp .lotebadge{font-family:ui-monospace,monospace;font-size:11.5px;font-weight:800;color:var(--cx-primary-text);background:var(--cx-primary-soft);border-radius:6px;padding:2px 8px;}
.docs{display:flex;gap:7px;flex-wrap:wrap;margin-top:9px;}
.doc{display:inline-flex;align-items:center;gap:5px;font-size:11px;font-weight:800;border-radius:8px;padding:5px 10px;text-decoration:none;border:1px solid var(--cx-hairline);cursor:pointer;}
.doc.F01{background:rgba(37,99,235,.13);color:var(--cx-info-text, #2563eb);border-color:rgba(37,99,235,.25)}
.doc.F02{background:rgba(21,128,61,.13);color:var(--cx-success-text, #15803d);border-color:rgba(21,128,61,.25)}
.doc.COA_PROVEEDOR{background:var(--cx-primary-soft);color:var(--cx-primary-text);border-color:rgba(109,40,217,.25)}
.doc.ROTULO{background:var(--cx-hairline);color:var(--cx-text-soft)}
.doc.COA_PT{background:rgba(13,148,136,.16);color:#0d9488;border-color:rgba(13,148,136,.28)}
.doc.ROTULO_LIMPIEZA{background:rgba(2,132,199,.14);color:#0284c7;border-color:rgba(2,132,199,.28)}
.doc.EBR{background:rgba(180,83,9,.14);color:var(--cx-warn-text, #b45309);border-color:rgba(180,83,9,.28)}
.doc .r2{font-size:9px;opacity:.75}
.nodoc{font-size:11px;color:var(--cx-warn-text, #b45309);font-weight:700;}
.eqs{display:flex;gap:6px;flex-wrap:wrap;margin-top:6px}
.eq{font-size:11px;font-weight:700;color:var(--cx-text-soft);background:var(--cx-bg-alt);border:1px solid var(--cx-hairline);border-radius:7px;padding:3px 9px;display:inline-flex;align-items:center;gap:6px}
.cal{font-size:9.5px;font-weight:800;border-radius:5px;padding:1px 6px}
.cal.ok{background:rgba(21,128,61,.16);color:var(--cx-success-text, #15803d)} .cal.no{background:rgba(185,28,28,.16);color:var(--cx-danger-text, #b91c1c)} .cal.q{background:rgba(180,83,9,.16);color:var(--cx-warn-text, #b45309)} .cal.g{background:var(--cx-hairline);color:var(--cx-text-mute)}
.fase-row{display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding:9px 0;border-bottom:1px solid var(--cx-hairline)}
.fase-row:last-child{border-bottom:none}
.fase-b{font-size:11px;font-weight:800;border-radius:7px;padding:3px 10px;background:var(--cx-primary-soft);color:var(--cx-primary-text)}
.empty{color:var(--cx-text-mute);font-size:14px;padding:34px 0;text-align:center;}
.warn{font-size:12px;color:var(--cx-warn-text, #b45309);background:rgba(180,83,9,.08);border:1px solid rgba(180,83,9,.25);border-radius:10px;padding:9px 13px;margin-top:8px}
.modal{display:none;position:fixed;inset:0;background:rgba(15,15,20,.6);z-index:9999;align-items:center;justify-content:center;padding:24px;}
.modal-card{background:var(--cx-card);border:1px solid var(--cx-hairline);border-radius:16px;width:min(960px,96vw);height:min(88vh,920px);display:flex;flex-direction:column;overflow:hidden;box-shadow:0 24px 70px rgba(0,0,0,.4);}
.modal-head{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:13px 16px;border-bottom:1px solid var(--cx-hairline);}
.modal-head b{font-size:14px;color:var(--cx-text)}
.mx{background:var(--cx-bg-alt);color:var(--cx-text-soft);border:1px solid var(--cx-hairline);border-radius:9px;width:32px;height:32px;font-size:18px;line-height:1;cursor:pointer;padding:0}
#mdFrame{flex:1;width:100%;border:none;background:var(--cx-card, #fff)}
</style></head><body>
<header class="cx-mod-header cx-fade-in">
  <span class="cx-mod-header__logo" style="display:inline-flex;align-items:center;color:var(--cx-primary-text);"><svg viewBox="0 0 24 24" width="34" height="34" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v6m0 0 4-2m-4 2L8 6M4 10l4 2m0 0v6l4 2 4-2v-6m0 0 4-2m-4 2-4 2"/></svg></span>
  <div><div class="cx-mod-header__title">Genealogía de lote</div>
  <div class="cx-mod-header__sub"><strong>Calidad</strong> &middot; trazabilidad hacia atrás &middot; INVIMA</div></div>
  <div class="cx-mod-header__nav">
    <a href="/calidad/expediente" class="cx-btn cx-btn-ghost cx-btn-sm">&#128193; Expediente</a>
    <a href="/calidad/maestro-lotes" class="cx-btn cx-btn-ghost cx-btn-sm" title="Unidades por lote y presentacion: cuantas debian salir, cuantas se envasaron y cuantas se liberaron">&#128202; Maestro de lotes</a>
    <a href="/calidad" class="cx-btn cx-btn-ghost cx-btn-sm">&larr; Calidad</a>
    <button class="cx-theme-toggle" onclick="cxToggleTheme()" title="Modo claro/oscuro"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4 12H2M22 12h-2M5.6 5.6 4.2 4.2M19.8 19.8l-1.4-1.4M5.6 18.4l-1.4 1.4M19.8 4.2l-1.4 1.4"/></svg></button>
  </div>
</header>
<script>function cxToggleTheme(){var h=document.documentElement;var n=h.getAttribute('data-theme')==='dark'?'light':'dark';if(n==='dark')h.setAttribute('data-theme','dark');else h.removeAttribute('data-theme');try{localStorage.setItem('cx-theme',n);}catch(e){}}</script>
<div class="wrap">
<div class="card">
<div class="intro">Buscá un <b>lote de producto terminado</b> y se despliega su <b>árbol de trazabilidad hacia atrás</b>: las materias primas que consumió (cada una con su lote de proveedor y documentos F01/F02/COA), el área y equipos donde se fabricó y envasó, el batch record y la liberación. Esto es lo que responde "de qué está hecho este lote" en una auditoría INVIMA.</div>
<div class="searchbar">
<input id="q" class="cx-input" placeholder="Lote de PT (ej: 34345, SUEROTRI-1234)&hellip;" autocomplete="off">
<button class="cx-btn cx-btn-grad" onclick="buscar()">Ver genealog&iacute;a</button>
<span id="msg"></span>
</div>
</div>
<div id="res"></div>
</div>
<div id="modal" class="modal" onclick="if(event.target===this)cerrarDoc()">
  <div class="modal-card"><div class="modal-head"><b id="mdTit">Documento</b>
    <button class="mx" onclick="cerrarDoc()" title="Cerrar (Esc)">&times;</button></div>
    <iframe id="mdFrame" title="Documento"></iframe></div>
</div>
<script>
function esc(s){ if(s==null) return ''; return String(s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];}); }
function abrirDoc(el){ var u=el.getAttribute('data-u'), t=el.getAttribute('data-t')||'Documento'; document.getElementById('mdTit').textContent=t; document.getElementById('mdFrame').src=u; document.getElementById('modal').style.display='flex'; return false; }
function cerrarDoc(){ document.getElementById('modal').style.display='none'; document.getElementById('mdFrame').src='about:blank'; }
document.addEventListener('keydown',function(e){ if(e.key==='Escape') cerrarDoc(); });
function estadoChip(s){ s=(s||'').toUpperCase(); if(s==='VIGENTE') return '<span class="chip ok">&#9679; '+esc(s)+'</span>'; if(s.indexOf('CUARENT')>=0) return '<span class="chip q">&#9679; '+esc(s)+'</span>'; if(s.indexOf('RECHAZ')>=0) return '<span class="chip r">&#9679; '+esc(s)+'</span>'; return s?('<span class="chip">'+esc(s)+'</span>'):''; }
function docChip(d){ return '<a class="doc '+esc(d.tipo)+'" data-u="'+esc(d.url)+'" data-t="'+esc(d.titulo||d.tipo)+'" onclick="return abrirDoc(this)">'+esc(d.tipo)+(d.en_r2?' <span class="r2">&#128190;R2</span>':'')+'</a>'; }
function mpCard(mp){
  var docs = (mp.docs&&mp.docs.length) ? '<div class="docs">'+mp.docs.map(docChip).join('')+'</div>' : '<div class="nodoc">&#9888; sin documentos indexados para este lote de MP</div>';
  var meta=[]; if(mp.proveedor) meta.push('<b>Proveedor:</b> '+esc(mp.proveedor)); if(mp.numero_oc) meta.push('<b>OC:</b> '+esc(mp.numero_oc)); if(mp.fecha_vencimiento) meta.push('<b>Vence:</b> '+esc(mp.fecha_vencimiento)); if(mp.gramos) meta.push('<b>Consumo:</b> '+mp.gramos+' g');
  return '<div class="mp"><div class="top"><div><span class="nm">'+esc(mp.material_nombre||mp.material_id)+'</span> <span class="cod">'+esc(mp.material_id)+'</span></div>'
    +(mp.lote_mp?'<span class="lotebadge">lote '+esc(mp.lote_mp)+'</span>':'<span class="nodoc">sin lote</span>')+'</div>'
    +(meta.length?'<div class="meta">'+meta.join(' &middot; ')+' '+estadoChip(mp.estado_lote)+'</div>':'')
    +docs+'</div>';
}
function areaBlock(slot,a){
  if(!a) return '';
  var eqs = (a.equipos&&a.equipos.length) ? '<div class="eqs">'+a.equipos.map(function(e){
    var cal='<span class="cal g">sin calibración</span>';
    if(e.calibracion){ var v=e.calibracion.vigente; if(v===true) cal='<span class="cal ok" title="Calibrado · vence '+esc(e.calibracion.proxima)+'">&#10003; cal '+esc(e.calibracion.proxima)+'</span>'; else if(v===false) cal='<span class="cal no" title="Calibración VENCIDA ('+esc(e.calibracion.proxima)+')">&#10007; cal vencida</span>'; else cal='<span class="cal q" title="Calibración registrada sin fecha próxima">cal s/f</span>'; }
    return '<span class="eq">'+esc(e.codigo)+(e.nombre?(' &middot; '+esc(e.nombre)):'')+cal+'</span>';
  }).join('')+'</div>' : '<div class="nodoc">sin equipos catalogados en el área</div>';
  return '<div class="mp"><div class="top"><span class="nm">'+(slot==='fabricacion'?'&#127981; Fabricación':'&#128230; Envasado')+'</span><span class="lotebadge">'+esc(a.codigo)+' &middot; '+esc(a.nombre)+'</span></div>'
    +'<div class="meta">Equipos del área <span class="nodoc" style="font-weight:600">(inferidos por área)</span></div>'+eqs+'</div>';
}
async function buscar(){
  var q=document.getElementById('q').value.trim(); var res=document.getElementById('res');
  if(!q){ res.innerHTML='<div class="card"><div class="empty">Escribí un lote de producto terminado.</div></div>'; return; }
  res.innerHTML='<div class="card"><div class="empty">Rastreando la genealog&iacute;a&hellip;</div></div>';
  try{
    var d=await (await fetch('/api/calidad/genealogia-pt/'+encodeURIComponent(q))).json();
    if(!d.encontrado){ res.innerHTML='<div class="card"><div class="empty">No encontré un lote de PT <b>'+esc(q)+'</b>. Probá con el lote físico exacto (el del batch record).</div></div>'; return; }
    var h='<div class="card">';
    // cabecera PT
    h+='<div class="pt-hd"><span class="em">&#129514;</span><div><h2>'+esc(d.producto||'Producto')+'</h2><span class="lote">lote '+esc(d.lote)+'</span></div></div>';
    h+='<div class="chips">'+estadoChip(d.pt_estado);
    if(d.liberacion){ h+='<span class="chip ok">&#10003; Liberado por '+esc(d.liberacion.por)+(d.liberacion.at?(' &middot; '+esc(d.liberacion.at)):'')+'</span>'; }
    if(d.pt_fecha){ h+='<span class="chip">Fabricado '+esc(d.pt_fecha)+'</span>'; }
    h+='</div>';
    if(d.fuente_mp==='fefo_tag'){ h+='<div class="warn">&#8505; Lote de <b>Fabricación directa</b> &middot; las materias primas se rastrean por el registro de consumo del lote (tag FEFO) y el área por el EBR. Trazabilidad completa.</div>'; }
    // fases / batch record
    if(d.fases&&d.fases.length){
      h+='<div class="sec"><div class="sec-h">&#128203; Batch record <span class="n">'+d.fases.length+' fase(s)</span></div><div class="branch">';
      h+=d.fases.map(function(f){ return '<div class="fase-row"><span class="fase-b">'+esc(f.fase_label)+'</span>'
        +(f.numero_op?'<span class="cod">'+esc(f.numero_op)+'</span>':'')
        +(f.area_codigo?'<span class="eq">'+esc(f.area_codigo)+'</span>':'')
        +estadoChip(f.estado)
        +'<a class="doc EBR" data-u="'+esc(f.url)+'" data-t="Batch record '+esc(f.fase_label)+'" onclick="return abrirDoc(this)" style="margin-left:auto">Ver legajo</a></div>'; }).join('');
      h+='</div></div>';
    }
    // materias primas
    h+='<div class="sec"><div class="sec-h">&#129514; Materias primas consumidas <span class="n">'+d.materias_primas.length+'</span></div><div class="branch">';
    h+= d.materias_primas.length ? d.materias_primas.map(mpCard).join('') : '<div class="empty" style="padding:14px 0">No se hallaron materias primas encadenadas a este lote.</div>';
    h+='</div></div>';
    // áreas + equipos
    if(d.areas&&(d.areas.fabricacion||d.areas.envasado)){
      h+='<div class="sec"><div class="sec-h">&#127981; Áreas y equipos</div><div class="branch">'+areaBlock('fabricacion',d.areas.fabricacion)+areaBlock('envasado',d.areas.envasado)+'</div></div>';
    }
    // envases
    if(d.envases&&d.envases.length){
      h+='<div class="sec"><div class="sec-h">&#128230; Envases consumidos <span class="n">'+d.envases.length+'</span></div><div class="branch">';
      h+=d.envases.map(function(e){ return '<div class="mp"><div class="top"><div><span class="nm">'+esc(e.nombre||e.mee_codigo)+'</span> <span class="cod">'+esc(e.mee_codigo)+'</span></div><span class="lotebadge">'+(e.cantidad||0)+' u</span></div></div>'; }).join('');
      h+='</div></div>';
    }
    // control de calidad del PT (micro + fisicoquímico)
    var anM=(d.analisis&&d.analisis.micro)||[], anF=(d.analisis&&d.analisis.fisicoquimico)||[];
    var anEst=function(s){ s=(s||'').toLowerCase(); if(s==='ok'||s==='conforme'||s==='informado') return '<span class="chip ok">'+esc(s)+'</span>'; if(s.indexOf('fuera')>=0) return '<span class="chip r">'+esc(s)+'</span>'; if(s.indexOf('observ')>=0) return '<span class="chip q">'+esc(s)+'</span>'; return s?('<span class="chip">'+esc(s)+'</span>'):''; };
    if(anM.length||anF.length){
      h+='<div class="sec"><div class="sec-h">&#128300; Control de calidad del lote <span class="n">'+(anM.length+anF.length)+' resultado(s)</span></div><div class="branch">';
      if(anM.length){ h+='<div class="mp"><div class="top"><span class="nm">Microbiolog&iacute;a</span><span class="cod">'+anM.length+' microorganismo(s)</span></div>'+anM.map(function(x){return '<div class="meta"><b>'+esc(x.param)+':</b> '+esc(x.valor)+' '+esc(x.unidad)+' '+anEst(x.estado)+(x.fecha?(' &middot; '+esc(x.fecha)):'')+'</div>';}).join('')+'</div>'; }
      if(anF.length){ h+='<div class="mp"><div class="top"><span class="nm">Fisicoqu&iacute;mico</span><span class="cod">'+anF.length+' par&aacute;metro(s)</span></div>'+anF.map(function(x){return '<div class="meta"><b>'+esc(x.param)+':</b> '+esc(x.resultado)+' '+esc(x.unidad)+(x.referencia?(' (ref '+esc(x.referencia)+')'):'')+' '+anEst(x.estado)+(x.fecha?(' &middot; '+esc(x.fecha)):'')+'</div>';}).join('')+'</div>'; }
      h+='</div></div>';
    }
    // limpieza de área/equipos (F02)
    if(d.limpieza&&d.limpieza.length){
      h+='<div class="sec"><div class="sec-h">&#129529; Limpieza de &aacute;rea/equipos (F02) <span class="n">'+d.limpieza.length+'</span></div><div class="branch">';
      h+=d.limpieza.map(function(x){return '<div class="mp"><div class="top"><span class="nm">'+esc(x.area_nombre||x.area_codigo)+'</span>'+estadoChip(x.estado)+'</div><div class="meta">'+(x.realizado_por?('<b>Limpi&oacute;:</b> '+esc(x.realizado_por)+(x.realizado_at?(' &middot; '+esc(x.realizado_at)):'')):'')+(x.verificado_por?(' &middot; <b>Verific&oacute;:</b> '+esc(x.verificado_por)):'')+'</div></div>';}).join('');
      h+='</div></div>';
    }
    // liberación final (acondicionamiento → stock PT)
    if(d.liberacion_final){
      var lf=d.liberacion_final;
      h+='<div class="sec"><div class="sec-h">&#10003; Liberaci&oacute;n final</div><div class="branch"><div class="mp"><div class="meta"><b>'+(lf.unidades||0)+' unidades</b>'+(lf.presentacion?(' &middot; '+esc(lf.presentacion)):'')+(lf.destino?(' &middot; destino '+esc(lf.destino)):'')+(lf.fecha?(' &middot; '+esc(lf.fecha)):'')+'</div></div></div></div>';
    }
    // docs a nivel PT
    if(d.docs_pt&&d.docs_pt.length){
      h+='<div class="sec"><div class="sec-h">&#128196; Documentos del lote</div><div class="docs">'+d.docs_pt.map(docChip).join('')+'</div></div>';
    }
    h+='</div>';
    res.innerHTML=h;
  }catch(e){ res.innerHTML='<div class="card"><div class="empty">Error: '+esc(e.message)+'</div></div>'; }
}
document.getElementById('q').addEventListener('keydown',function(e){ if(e.key==='Enter') buscar(); });
</script></body></html>"""


@bp.route('/calidad/expediente', methods=['GET'])
def calidad_expediente_page():
    """Página · Expediente por lote (INVIMA · zero-paper): buscá un lote y ves TODOS sus documentos."""
    if 'compras_user' not in session:
        return redirect('/login?next=/calidad/expediente')
    return Response(_EXPEDIENTE_HTML, mimetype='text/html')


_EXPEDIENTE_HTML = r"""<!DOCTYPE html><html lang="es" translate="no"><head><meta charset="UTF-8">
<meta name="google" content="notranslate">
<meta name="viewport" content="width=device-width,initial-scale=1.0,viewport-fit=cover"><title>Expediente por lote · Calidad · EOS</title>
<link rel="stylesheet" href="/static/cortex.css?v=eos15">
<script>(function(){try{var t=localStorage.getItem("cx-theme");if(t==="dark")document.documentElement.setAttribute("data-theme","dark");}catch(e){}})();</script>
<style>
body{background:var(--cx-bg);color:var(--cx-text);margin:0;font-family:'Inter',system-ui,-apple-system,sans-serif;}
*{box-sizing:border-box}
.exp-wrap{max-width:1280px;margin:0 auto;padding:22px 22px 64px;}
.exp-intro{color:var(--cx-text-mute);font-size:13.5px;line-height:1.55;max-width:840px;margin:0 0 16px;}
.card{background:var(--cx-card);border:1px solid var(--cx-hairline);border-radius:18px;box-shadow:0 1px 3px rgba(15,23,42,.04),0 10px 30px rgba(15,23,42,.05);padding:22px 24px;margin-bottom:18px;}
.searchbar{display:flex;gap:10px;flex-wrap:wrap;align-items:center;}
#q{flex:1;min-width:280px;font-size:15px;}
.r2estado{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:16px;}
.pill{display:inline-flex;align-items:center;gap:5px;font-size:12px;font-weight:700;padding:5px 12px;border-radius:999px;border:1px solid var(--cx-hairline);color:var(--cx-text-soft);}
.pill.ok{color:var(--cx-success-text, #15803d);border-color:rgba(21,128,61,.35);background:rgba(21,128,61,.09);}
.pill.pend{color:var(--cx-warn-text, #b45309);border-color:rgba(180,83,9,.35);background:rgba(180,83,9,.10);}
.pill.off{color:var(--cx-text-mute);}
.r2estado .hint{color:var(--cx-text-faint);font-size:11px;}
.r2fallos{font-size:11.5px;color:var(--cx-warn-text, #b45309);margin:8px 0 0;line-height:1.5;}
#msg{font-size:12.5px;font-weight:700;}
.grp{background:var(--cx-card);border:1px solid var(--cx-hairline);border-radius:16px;box-shadow:0 2px 14px rgba(15,23,42,.05);padding:18px 20px;margin-bottom:16px;}
.grp h2{font-size:16px;margin:0 0 2px;letter-spacing:-.01em;color:var(--cx-text);}
.grp .meta{font-size:12px;color:var(--cx-text-mute);margin-bottom:12px;}
.ent{display:inline-block;border-radius:999px;padding:2px 10px;font-size:10.5px;font-weight:800;margin-right:8px;vertical-align:middle;}
.ent.MP{background:var(--cx-primary-soft);color:var(--cx-primary-text);} .ent.MEE{background:rgba(37,99,235,.16);color:var(--cx-info-text, #2563eb);} .ent.PT{background:rgba(21,128,61,.16);color:var(--cx-success-text, #15803d);}
.docs{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:12px;}
.doc{border:1px solid var(--cx-hairline);border-radius:12px;padding:13px 15px;background:var(--cx-bg-alt);text-decoration:none;color:var(--cx-text);display:block;transition:.12s;}
.doc:hover{border-color:var(--cx-primary-light);box-shadow:0 4px 16px rgba(109,40,217,.13);transform:translateY(-1px);}
.doc .t{font-size:13.5px;font-weight:800;margin-bottom:2px;}
.doc .f{font-size:11px;color:var(--cx-text-mute);font-family:ui-monospace,monospace;}
.doc .b{display:inline-block;font-size:10px;font-weight:800;border-radius:6px;padding:2px 7px;margin-bottom:7px;}
.b.F01{background:rgba(37,99,235,.16);color:var(--cx-info-text, #2563eb);} .b.F02{background:rgba(21,128,61,.16);color:var(--cx-success-text, #15803d);} .b.EBR{background:rgba(180,83,9,.18);color:var(--cx-warn-text, #b45309);}
.b.COA_PROVEEDOR{background:var(--cx-primary-soft);color:var(--cx-primary-text);} .b.ROTULO{background:var(--cx-hairline);color:var(--cx-text-soft);}
.b.COA_PT{background:rgba(13,148,136,.16);color:#0d9488;} .b.ROTULO_LIMPIEZA{background:rgba(2,132,199,.14);color:#0284c7;}
.empty{color:var(--cx-text-mute);font-size:14px;padding:32px 0;text-align:center;}
.modal{display:none;position:fixed;inset:0;background:rgba(15,15,20,.6);z-index:9999;align-items:center;justify-content:center;padding:24px;}
.modal-card{background:var(--cx-card);border:1px solid var(--cx-hairline);border-radius:16px;width:min(960px,96vw);height:min(88vh,920px);display:flex;flex-direction:column;overflow:hidden;box-shadow:0 24px 70px rgba(0,0,0,.4);}
.modal-head{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:13px 16px;border-bottom:1px solid var(--cx-hairline);}
.modal-head b{font-size:14px;color:var(--cx-text);}
.modal-actions{display:flex;align-items:center;gap:12px;}
.mlink{color:var(--cx-primary-text);text-decoration:none;font-size:12px;font-weight:700;}
.mx{background:var(--cx-bg-alt);color:var(--cx-text-soft);border:1px solid var(--cx-hairline);border-radius:9px;width:32px;height:32px;font-size:18px;line-height:1;cursor:pointer;padding:0;}
#mdFrame{flex:1;width:100%;border:none;background:var(--cx-card, #fff);}
</style></head><body>
<header class="cx-mod-header cx-fade-in">
  <span class="cx-mod-header__logo" style="display:inline-flex;align-items:center;color:var(--cx-primary-text);"><svg viewBox="0 0 24 24" width="34" height="34" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M4 7a2 2 0 0 1 2-2h4l2 2h6a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z"/><path d="M9 13h6"/></svg></span>
  <div>
    <div class="cx-mod-header__title">Expediente por lote</div>
    <div class="cx-mod-header__sub"><strong>Calidad</strong> &middot; Espagiria &middot; trazabilidad INVIMA zero-paper</div>
  </div>
  <div class="cx-mod-header__nav">
    <a href="/calidad/genealogia" class="cx-btn cx-btn-ghost cx-btn-sm" title="Genealog&iacute;a: de qu&eacute; est&aacute; hecho un lote de producto terminado (MP, área, equipos, envasado)">&#129514; Genealog&iacute;a de PT</a>
    <a href="/calidad/maestro-lotes" class="cx-btn cx-btn-ghost cx-btn-sm" title="Unidades por lote y presentacion: cuantas debian salir, cuantas se envasaron y cuantas se liberaron">&#128202; Maestro de lotes</a>
    <a href="/calidad" class="cx-btn cx-btn-ghost cx-btn-sm" title="Volver a Calidad">&larr; Calidad</a>
    <a href="/modulos" class="cx-btn cx-btn-ghost cx-btn-sm" title="Todos los m&oacute;dulos">M&oacute;dulos</a>
    <button class="cx-theme-toggle" onclick="cxToggleTheme()" title="Modo claro/oscuro"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4 12H2M22 12h-2M5.6 5.6 4.2 4.2M19.8 19.8l-1.4-1.4M5.6 18.4l-1.4 1.4M19.8 4.2l-1.4 1.4"/></svg></button>
  </div>
</header>
<script>function cxToggleTheme(){var h=document.documentElement;var n=h.getAttribute('data-theme')==='dark'?'light':'dark';if(n==='dark')h.setAttribute('data-theme','dark');else h.removeAttribute('data-theme');try{localStorage.setItem('cx-theme',n);}catch(e){}}</script>
<div class="exp-wrap">
<div class="card">
<div class="exp-intro">Buscá un <b>lote</b> (de materia prima o producto terminado), un <b>c&oacute;digo</b> o un <b>producto</b> y te aparecen TODOS sus documentos regulados en un solo lugar: F01, F02, COA del proveedor, r&oacute;tulo y batch record. Esto es lo que se le muestra a una auditor&iacute;a INVIMA.</div>
<div class="searchbar">
<input id="q" class="cx-input" placeholder="Ej: LYPH260123, MP00172, Suero Triactive, lote de PT&hellip;" autocomplete="off">
<button class="cx-btn cx-btn-grad" onclick="buscar()">Buscar</button>
<button class="cx-btn cx-btn-ghost" onclick="reconstruir()" title="Reindexar los documentos existentes (F01/F02/batch records) en el expediente">Reindexar</button>
<button class="cx-btn cx-btn-ghost" onclick="archivarR2()" title="Sube una copia inmutable de cada documento a Cloudflare R2 (respaldo off-site para INVIMA)">Archivar en R2</button>
<span id="msg"></span>
</div>
<div id="r2estado" class="r2estado"></div>
<div id="r2fallos" class="r2fallos"></div>
</div>
<div id="res"></div>
</div>
<div id="modal" class="modal" onclick="if(event.target===this)cerrarDoc()">
  <div class="modal-card">
    <div class="modal-head">
      <b id="mdTit">Documento</b>
      <span class="modal-actions">
        <a id="mdNueva" href="#" target="_blank" class="mlink" title="Abrir en pestaña nueva">Abrir aparte &#8599;</a>
        <button class="mx" onclick="cerrarDoc()" title="Cerrar (Esc)">&times;</button>
      </span>
    </div>
    <iframe id="mdFrame" title="Documento del expediente"></iframe>
  </div>
</div>
<script>
function esc(s){ if(s==null) return ''; return String(s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];}); }
var _csrf=null;
async function csrf(){ if(_csrf) return _csrf; try{ var r=await fetch('/api/csrf-token',{credentials:'same-origin'}); var j=await r.json(); _csrf=j.csrf_token; }catch(e){} return _csrf; }
async function buscar(){
  var q=document.getElementById('q').value.trim();
  var res=document.getElementById('res');
  if(!q){ res.innerHTML='<div class="empty">Escribí un lote, código o producto para buscar su expediente.</div>'; return; }
  res.innerHTML='<div class="empty">Buscando…</div>';
  try{
    var d=await (await fetch('/api/calidad/expediente-lote?q='+encodeURIComponent(q))).json();
    var g=(d&&d.grupos)||[];
    if(!g.length){ res.innerHTML='<div class="empty">No hay documentos para <b>'+esc(q)+'</b>. (Si es un lote viejo, probá "Reindexar" una vez.)</div>'; return; }
    res.innerHTML=g.map(function(grp){
      var docs=(grp.docs||[]).map(function(x){
        return '<a class="doc" href="'+esc(x.url)+'" data-t="'+esc(x.titulo||x.tipo)+'" onclick="return abrirDoc(this)"><span class="b '+esc(x.tipo)+'">'+esc(x.tipo)+'</span>'
          +'<div class="t">'+esc(x.titulo||x.tipo)+'</div><div class="f">'+esc(x.formato||'')+(x.por?(' · '+esc(x.por)):'')+'</div></a>';
      }).join('');
      return '<div class="grp"><h2><span class="ent '+esc(grp.entidad||'MP')+'">'+esc(grp.entidad||'MP')+'</span>'+esc(grp.producto||grp.codigo||'')+'</h2>'
        +'<div class="meta">Lote <b>'+esc(grp.lote||'-')+'</b> &middot; código '+esc(grp.codigo||'-')+' &middot; '+(grp.docs||[]).length+' documento(s)</div>'
        +'<div class="docs">'+docs+'</div></div>';
    }).join('');
  }catch(e){ res.innerHTML='<div class="empty">Error: '+esc(e.message)+'</div>'; }
}
async function reconstruir(){
  var m=document.getElementById('msg'); m.style.color='#78716c'; m.textContent='Reindexando…';
  try{
    var t=await csrf();
    var r=await fetch('/api/calidad/reconstruir-expediente',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':t||''},body:'{}'});
    var d=await r.json();
    if(r.ok&&d.ok){ m.style.color='#15803d'; m.textContent='OK: '+d.total+' documentos indexados (F01 '+d.f01+', F02 '+d.f02+', batch '+d.ebr+').'; }
    else { m.style.color='#b91c1c'; m.textContent='Error: '+((d&&d.error)||r.status); }
  }catch(e){ m.style.color='#b91c1c'; m.textContent='Error de red'; }
}
async function cargarEstadoR2(){
  var e=document.getElementById('r2estado');
  try{
    var d=await (await fetch('/api/calidad/archivar-r2',{credentials:'same-origin'})).json();
    var s=(d&&d.estado)||{};
    if(!s.configurado){ e.innerHTML='<span class="pill off">Archivo R2 no configurado</span>'; return; }
    var tot=(s.archivados||0)+(s.pendientes||0);
    if(tot===0){ e.innerHTML='<span class="pill off">Sin documentos indexados aún &middot; dale <b>Reindexar</b> y luego <b>Archivar en R2</b></span>'; return; }
    e.innerHTML='<span class="pill ok">&#9679; '+(s.archivados||0)+' archivados en R2</span>'
      +(s.pendientes>0?'<span class="pill pend">'+s.pendientes+' pendientes de subir</span>':'<span class="pill ok">todo respaldado</span>')
      +'<span class="hint">Copia inmutable off-site (Cloudflare R2) &middot; respaldo para auditoría INVIMA</span>';
  }catch(err){ e.innerHTML=''; }
}
async function archivarR2(){
  var m=document.getElementById('msg'); var fb=document.getElementById('r2fallos');
  var totArch=0, totFall=0, fallosDet=[], vueltas=0;
  m.style.color='#78716c'; m.textContent='Subiendo a R2…';
  try{
    var t=await csrf();
    // Bucle: cada request es corto (lote acotado en el server) · seguimos mientras queden pendientes.
    while(vueltas<40){
      vueltas++;
      var r=await fetch('/api/calidad/archivar-r2',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':t||''},body:'{}'});
      var d=await r.json();
      if(!(r.ok&&d.ok)){ m.style.color='#b91c1c'; m.textContent='Error: '+((d&&d.error)||r.status); break; }
      totArch+=(d.archivados||0); totFall=(d.fallidos||0);
      if(d.detalle_fallos&&d.detalle_fallos.length){ fallosDet=d.detalle_fallos; }
      m.style.color='#78716c'; m.textContent='Subiendo a R2… '+totArch+' archivados'+(d.pendientes?(' · quedan '+d.pendientes):'')+'.';
      // Si no avanzó (0 archivados) o no quedan pendientes o R2 se cayó, cortamos.
      if(!d.pendientes || (d.archivados||0)===0 || d.corte_por_r2_caido){
        if(d.corte_por_r2_caido){ m.style.color='#b91c1c'; m.textContent='R2 no responde ahora · reintentá en un rato ('+totArch+' subidos).'; }
        else { m.style.color='#15803d'; m.textContent='OK: '+totArch+' documentos archivados en R2'+(totFall?(' · '+totFall+' fallidos (fuente no disponible)'):'')+(d.pendientes?(' · quedan '+d.pendientes):' · todo respaldado')+'.'; }
        break;
      }
    }
    if(fallosDet.length){
      fb.innerHTML='<b>Fallidos:</b> '+fallosDet.map(function(f){return esc(f.tipo||'')+' #'+esc(f.id)+' ('+esc(f.motivo||'')+')';}).join(' · ');
    } else { fb.innerHTML=''; }
  }catch(e){ m.style.color='#b91c1c'; m.textContent='Error de red'; }
  cargarEstadoR2();
}
function abrirDoc(a){
  var url=a.getAttribute('href'), t=a.getAttribute('data-t')||'Documento';
  document.getElementById('mdTit').textContent=t;
  document.getElementById('mdNueva').href=url;
  document.getElementById('mdFrame').src=url;
  document.getElementById('modal').style.display='flex';
  return false;
}
function cerrarDoc(){
  document.getElementById('modal').style.display='none';
  document.getElementById('mdFrame').src='about:blank';
}
document.getElementById('q').addEventListener('keydown',function(e){ if(e.key==='Enter') buscar(); });
document.addEventListener('keydown',function(e){ if(e.key==='Escape') cerrarDoc(); });
cargarEstadoR2();
</script></body></html>"""


@bp.route('/api/calidad/coa', methods=['GET','POST'])
def coa_list():
    """Registra resultados de analisis CoA por lote.
    Auto-valida contra especificaciones_mp si existen y marca conforme=0
    si esta fuera de spec.
    """
    # Audit zero-error 2-may-2026: POST de CoA es evidencia regulatoria INVIMA
    if request.method == 'POST':
        err, code = _require_calidad()
        if err: return err, code
    elif 'compras_user' not in session:
        return jsonify({'error':'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()

    if request.method == 'POST':
        d = request.json or {}
        for k in ('lote','codigo_mp','parametro','valor_obtenido'):
            if not d.get(k):
                return jsonify({'error':f'{k} requerido'}), 400

        # Audit zero-error: bloquear CoA si equipo tiene calibración vencida.
        # Antes un instrumento descalibrado podía registrar análisis "válidos".
        equipo_id = d.get('equipo_id')
        if equipo_id:
            try:
                eq = c.execute("""
                    SELECT equipo_codigo, fecha_proxima FROM equipos_eventos
                    WHERE equipo_codigo=(SELECT equipo_codigo FROM equipos_eventos WHERE id=? LIMIT 1)
                       OR id=?
                    ORDER BY fecha DESC LIMIT 1
                """, (equipo_id, equipo_id)).fetchone()
                if eq and eq[1]:
                    try:
                        # TZ Colombia (M24): "hoy" = date('now','-5 hours'), no UTC.
                        _hoy_cal = c.execute("SELECT date('now','-5 hours')").fetchone()[0]
                        if str(eq[1])[:10] < _hoy_cal:
                            return jsonify({
                                'error': f"Equipo {eq[0]} con calibración vencida ({eq[1]}). No se puede registrar CoA.",
                                'codigo': 'EQUIPO_VENCIDO',
                                'equipo': eq[0],
                                'fecha_vencimiento': eq[1],
                            }), 409
                    except (ValueError, TypeError):
                        pass  # fecha mal formada · no bloquear
            except Exception as e:
                log.warning('check equipo vencido fallo: %s', e)

        # Buscar especificacion para auto-validacion
        spec = c.execute("""SELECT valor_min, valor_max, unidad, metodo_ensayo
                            FROM especificaciones_mp
                            WHERE codigo_mp=? AND parametro=?""",
                         (d['codigo_mp'], d['parametro'])).fetchone()
        valor_min_spec = spec[0] if spec else d.get('valor_min_spec')
        valor_max_spec = spec[1] if spec else d.get('valor_max_spec')
        unidad = (spec[2] if spec else d.get('unidad','')) or d.get('unidad','')
        metodo = (spec[3] if spec else d.get('metodo_ensayo','')) or d.get('metodo_ensayo','')

        # Auto-validar conformidad: si valor_obtenido es numerico y hay specs
        conforme = 1
        try:
            val_num = float(str(d['valor_obtenido']).replace(',','.').strip())
            if valor_min_spec is not None and val_num < float(valor_min_spec):
                conforme = 0
            if valor_max_spec is not None and val_num > float(valor_max_spec):
                conforme = 0
        except (ValueError, TypeError):
            # Valor no-numerico (ej: "Conforme", "Cumple") · no auto-validar
            if d.get('conforme') is not None:
                conforme = 1 if d.get('conforme') else 0

        # INVIMA-FIX · 21-may-2026 · analista FORZADO al user · decision derivada
        # Antes: payload podía falsificar analista=otro + override decision='Aprobado'
        # aún con conforme=0 · violación 21 CFR Part 11 §11.10(b)(g)
        decision = 'Aprobado' if conforme else 'Rechazado'
        # Solo permitir override de decision cuando es CONFORME (downgrade es legal)
        if d.get('decision') and conforme:
            _allowed = ('Aprobado', 'Condicional', 'Pendiente revisión')
            if d['decision'] in _allowed:
                decision = d['decision']
        user = session.get('compras_user','sistema')
        analista_forzado = user  # FORZADO · no aceptar d.get('analista')
        c.execute("""INSERT INTO coa_resultados
            (lote, codigo_mp, material_nombre, parametro, unidad,
             valor_obtenido, valor_min_spec, valor_max_spec, conforme,
             metodo_ensayo, analista, fecha_analisis, equipo_id,
             observaciones, decision)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (d['lote'], d['codigo_mp'], d.get('material_nombre',''),
             d['parametro'], unidad, d['valor_obtenido'],
             valor_min_spec, valor_max_spec, conforme, metodo,
             analista_forzado,
             # FIX 17-jun (M24): fecha Colombia explícita si no viene (antes None →
             # NULL/DEFAULT UTC → el CoA del día no salía en lecturas ancladas a -5h · INVIMA).
             (d.get('fecha_analisis')
              or (__import__('datetime').datetime.now(__import__('datetime').timezone.utc)
                  - __import__('datetime').timedelta(hours=5)).strftime('%Y-%m-%d')),
             d.get('equipo_id'), d.get('observaciones',''), decision))
        coa_id = c.lastrowid
        # Audit log INVIMA · CoA es evidencia primaria de calidad de MP
        try:
            audit_log(c, usuario=user, accion='CREAR_COA',
                      tabla='coa_resultados', registro_id=coa_id,
                      despues={'lote': d['lote'], 'codigo_mp': d['codigo_mp'],
                                'parametro': d['parametro'][:80],
                                'valor': str(d['valor_obtenido'])[:100],
                                'conforme': bool(conforme),
                                'decision': decision})
        except Exception as e:
            log.warning('audit_log CREAR_COA fallo: %s', e)
        conn.commit()

        # Si NO conforme y no hay NC abierta para este lote+parametro, crear auto.
        # Fix 28-may · antes insertaba SIEMPRE (sin el check que el comentario
        # prometía) → cada CoA no conforme duplicaba la NC.
        if not conforme:
            try:
                ya_nc = c.execute(
                    """SELECT 1 FROM no_conformidades
                       WHERE lote=? AND codigo_mp=? AND estado='Abierta'
                         AND descripcion LIKE ?""",
                    (d['lote'], d['codigo_mp'], f'%{d["parametro"]}%')
                ).fetchone()
                if not ya_nc:
                    c.execute("""INSERT INTO no_conformidades
                                 (fecha,tipo,descripcion,area,responsable,lote,
                                  codigo_mp,impacto,accion_correctiva,estado,creado_por)
                                 VALUES (date('now', '-5 hours'),'Insumo',?,?,?,?,?,?,?,'Abierta',?)""",
                              (f'CoA fuera de spec: {d["parametro"]}={d["valor_obtenido"]} '
                               f'(spec {valor_min_spec}-{valor_max_spec})',
                               'Calidad', 'Jefe CC', d['lote'], d['codigo_mp'],
                               'Alto', 'Cuarentena lote, evaluar disposicion',
                               session.get('compras_user','sistema')))
                    conn.commit()
            except Exception:
                pass

        # Fix 28-may · devolver el id del CoA, no c.lastrowid (que tras crear
        # la NC apuntaba a la NC).
        return jsonify({'ok':True, 'id':coa_id, 'conforme':conforme,
                        'decision':decision}), 201

    # GET · filtros
    lote = request.args.get('lote','').strip()
    codigo_mp = request.args.get('codigo_mp','').strip()
    where, params = [], []
    if lote: where.append('lote=?'); params.append(lote)
    if codigo_mp: where.append('codigo_mp=?'); params.append(codigo_mp)
    sql = "SELECT * FROM coa_resultados"
    if where: sql += ' WHERE ' + ' AND '.join(where)
    sql += ' ORDER BY fecha_analisis DESC, id DESC LIMIT 500'
    c.execute(sql, params)
    cols = [x[0] for x in c.description]
    return jsonify([dict(zip(cols,r)) for r in c.fetchall()])


@bp.route('/api/calidad/coa/lote/<path:lote>')
def coa_por_lote(lote):
    """Devuelve CoA completo de un lote agrupado por parametro con verdict global."""
    if 'compras_user' not in session:
        return jsonify({'error':'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    rows = c.execute("""SELECT parametro, unidad, valor_obtenido, valor_min_spec,
                               valor_max_spec, conforme, metodo_ensayo, analista,
                               fecha_analisis, decision
                        FROM coa_resultados
                        WHERE lote=? ORDER BY fecha_analisis DESC""",
                     (lote,)).fetchall()
    cols = [x[0] for x in c.description]
    parametros = [dict(zip(cols,r)) for r in rows]
    n_total = len(parametros)
    n_conformes = sum(1 for p in parametros if p['conforme'])
    verdict = 'Aprobado' if n_total > 0 and n_conformes == n_total else \
              ('Rechazado' if n_total > 0 else 'Sin analizar')
    return jsonify({
        'lote': lote,
        'parametros': parametros,
        'n_parametros': n_total,
        'n_conformes': n_conformes,
        'verdict': verdict,
    })


# ─── ESTABILIDADES ──────────────────────────────────────────────────────────

@bp.route('/api/calidad/estabilidades', methods=['GET','POST'])
def estabilidades_list():
    # POST requiere RBAC Calidad/Admin · GET libre
    if request.method == 'POST':
        err, code = _require_calidad()
        if err: return err, code
    elif 'compras_user' not in session:
        return jsonify({'error':'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        for k in ('producto','lote_piloto','condicion','tiempo_dias','fecha_inicio'):
            if not d.get(k):
                return jsonify({'error':f'{k} requerido'}), 400
        user = session.get('compras_user','sistema')
        c.execute("""INSERT INTO estabilidades
            (producto, lote_piloto, condicion, tiempo_dias, tiempo_etiqueta,
             fecha_inicio, fecha_evaluacion, parametros_json, conforme,
             observaciones, analista, estado)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (d['producto'], d['lote_piloto'], d['condicion'],
             int(d['tiempo_dias']), d.get('tiempo_etiqueta',''),
             d['fecha_inicio'], d.get('fecha_evaluacion'),
             d.get('parametros_json','{}'), 1 if d.get('conforme', True) else 0,
             d.get('observaciones',''),
             d.get('analista', user),
             d.get('estado','Programado')))
        est_id = c.lastrowid
        try:
            audit_log(c, usuario=user, accion='CREAR_ESTABILIDAD',
                      tabla='estabilidades', registro_id=est_id,
                      despues={'producto': d['producto'][:80],
                                'lote_piloto': d['lote_piloto'][:80],
                                'condicion': d['condicion'][:80],
                                'tiempo_dias': int(d['tiempo_dias'])})
        except Exception as e:
            log.warning('audit_log CREAR_ESTABILIDAD fallo: %s', e)
        conn.commit()
        return jsonify({'ok':True, 'id':est_id}), 201
    producto = request.args.get('producto','').strip()
    lote = request.args.get('lote','').strip()
    where, params = [], []
    if producto: where.append('producto=?'); params.append(producto)
    if lote: where.append('lote_piloto=?'); params.append(lote)
    sql = 'SELECT * FROM estabilidades'
    if where: sql += ' WHERE ' + ' AND '.join(where)
    sql += ' ORDER BY fecha_inicio DESC, tiempo_dias ASC LIMIT 300'
    c.execute(sql, params)
    cols = [x[0] for x in c.description]
    return jsonify([dict(zip(cols,r)) for r in c.fetchall()])


# ─── CAPA acciones (workflow real para no_conformidades) ────────────────────

@bp.route('/api/calidad/capa', methods=['GET','POST'])
def capa_list():
    # POST requiere RBAC Calidad/Admin · GET es libre
    if request.method == 'POST':
        err, code = _require_calidad()
        if err: return err, code
    elif 'compras_user' not in session:
        return jsonify({'error':'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        # INVIMA-FIX · 21-may-2026 · fecha_compromiso obligatoria (PDCA)
        # Antes: aceptaba null · CAPA sin plazo nunca aparecía vencida
        # · auditor INVIMA detecta CAPA sin ciclo cerrable
        for k in ('nc_id','tipo','descripcion','fecha_compromiso'):
            if not d.get(k):
                return jsonify({'error':f'{k} requerido'}), 400
        if d['tipo'] not in ('correctiva','preventiva','contencion'):
            return jsonify({'error':'tipo debe ser correctiva/preventiva/contencion'}), 400
        # Validar fecha_compromiso ≥ hoy (no aceptar fechas pasadas)
        try:
            from datetime import date as _date, datetime as _dt
            fc_str = str(d['fecha_compromiso'])[:10]
            fc_date = _dt.strptime(fc_str, '%Y-%m-%d').date()
            if fc_date < _date.today():
                return jsonify({
                    'error': 'fecha_compromiso debe ser hoy o futuro',
                    'codigo': 'FECHA_PASADA',
                }), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'fecha_compromiso formato YYYY-MM-DD'}), 400
        user = session.get('compras_user','sistema')
        c.execute("""INSERT INTO capa_acciones
            (nc_id, tipo, descripcion, responsable, fecha_compromiso, estado)
            VALUES (?,?,?,?,?,?)""",
            (int(d['nc_id']), d['tipo'], d['descripcion'],
             d.get('responsable',''), d.get('fecha_compromiso'),
             d.get('estado','Pendiente')))
        capa_id = c.lastrowid
        try:
            audit_log(c, usuario=user, accion='CREAR_CAPA',
                      tabla='capa_acciones', registro_id=capa_id,
                      despues={'nc_id': d['nc_id'], 'tipo': d['tipo'],
                                'descripcion': d['descripcion'][:200]})
        except Exception as e:
            log.warning('audit_log CREAR_CAPA fallo: %s', e)
        conn.commit()
        return jsonify({'ok':True, 'id':capa_id}), 201
    nc_id = request.args.get('nc_id','').strip()
    if nc_id:
        c.execute("SELECT * FROM capa_acciones WHERE nc_id=? ORDER BY id ASC", (nc_id,))
    else:
        c.execute("SELECT * FROM capa_acciones ORDER BY creado_en DESC LIMIT 200")
    cols = [x[0] for x in c.description]
    return jsonify([dict(zip(cols,r)) for r in c.fetchall()])


@bp.route('/api/calidad/capa/<int:cid>', methods=['PATCH'])
def capa_update(cid):
    err, code = _require_calidad()
    if err: return err, code
    d = request.json or {}
    user = session.get('compras_user','sistema')
    conn = get_db(); c = conn.cursor()
    fields = ['descripcion','responsable','fecha_compromiso','fecha_ejecucion',
              'evidencia_url','efectiva','verificada_por','fecha_verificacion','estado']
    # INVIMA-FIX · 21-may-2026 · validar transiciones + evidencia para Verificada/Cerrada
    if d.get('estado') in ('Verificada', 'Cerrada'):
        # Leer estado actual + fecha_ejecucion + evidencia_url
        row_act = c.execute(
            "SELECT estado, fecha_ejecucion, evidencia_url FROM capa_acciones WHERE id=?",
            (cid,),
        ).fetchone()
        if not row_act:
            return jsonify({'error': 'CAPA no existe'}), 404
        # Si pasa a Verificada · debe tener fecha_ejecucion previa
        fej_actual = row_act[1] or d.get('fecha_ejecucion', '')
        evid_actual = row_act[2] or d.get('evidencia_url', '')
        if not fej_actual:
            return jsonify({
                'error': 'fecha_ejecucion requerida antes de Verificar/Cerrar',
                'codigo': 'FECHA_EJECUCION_REQUERIDA',
            }), 400
        # evidencia_url debe ser http(s) · no javascript: ni data:
        if evid_actual and not str(evid_actual).startswith(('http://', 'https://')):
            return jsonify({
                'error': 'evidencia_url debe ser http(s)://',
                'codigo': 'EVIDENCIA_URL_INVALIDA',
            }), 400
        if not evid_actual:
            return jsonify({
                'error': 'evidencia_url requerida para Verificada/Cerrada',
                'codigo': 'EVIDENCIA_REQUERIDA',
            }), 400
    sets = ', '.join(f+'=?' for f in fields if f in d)
    vals = [d[f] for f in fields if f in d]
    if not sets: return jsonify({'error':'Nada que actualizar'}), 400
    if d.get('estado') == 'Verificada' and 'fecha_verificacion' not in d:
        sets += ', fecha_verificacion=date(\'now\')'
    vals.append(cid)
    c.execute(f"UPDATE capa_acciones SET {sets} WHERE id=?", vals)
    try:
        audit_log(c, usuario=user, accion='ACTUALIZAR_CAPA',
                  tabla='capa_acciones', registro_id=cid,
                  despues={k: d[k] for k in fields if k in d})
    except Exception as e:
        log.warning('audit_log ACTUALIZAR_CAPA fallo: %s', e)
    conn.commit()
    return jsonify({'ok':True})


# ─── AUDITORIAS ─────────────────────────────────────────────────────────────

@bp.route('/api/calidad/auditorias', methods=['GET','POST'])
def auditorias_list():
    # POST requiere RBAC Calidad/Admin · GET libre
    if request.method == 'POST':
        err, code = _require_calidad()
        if err: return err, code
    elif 'compras_user' not in session:
        return jsonify({'error':'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    if request.method == 'POST':
        d = request.json or {}
        if not d.get('tipo') or not d.get('ente_auditado'):
            return jsonify({'error':'tipo y ente_auditado requeridos'}), 400
        user = session.get('compras_user','sistema')
        c.execute("""INSERT INTO auditorias
            (tipo, ente_auditado, fecha_planeada, auditor, alcance, estado)
            VALUES (?,?,?,?,?,?)""",
            (d['tipo'], d['ente_auditado'], d.get('fecha_planeada'),
             d.get('auditor', user),
             d.get('alcance',''), d.get('estado','Planeada')))
        aud_id = c.lastrowid
        try:
            audit_log(c, usuario=user, accion='CREAR_AUDITORIA',
                      tabla='auditorias', registro_id=aud_id,
                      despues={'tipo': d['tipo'], 'ente': d['ente_auditado'][:200],
                                'fecha': d.get('fecha_planeada')})
        except Exception as e:
            log.warning('audit_log CREAR_AUDITORIA fallo: %s', e)
        conn.commit()
        return jsonify({'ok':True, 'id':aud_id}), 201
    c.execute("SELECT * FROM auditorias ORDER BY fecha_planeada DESC LIMIT 100")
    cols = [x[0] for x in c.description]
    return jsonify([dict(zip(cols,r)) for r in c.fetchall()])


# ═══════════════════════════════════════════════════════════════════════════
# CALIDAD AMPLIADA · Micro Specs + Resultados (heatmap) + Agua + OOS
# Sebastian (30-abr-2026)
# ═══════════════════════════════════════════════════════════════════════════

def _calc_estado_micro(valor, valor_texto, spec):
    """Calcula estado de un resultado micro vs spec.
    spec = dict con limite_industria, meta_lab, tipo_limite.
    Returns: 'ok' / 'fuera_meta' / 'fuera_industria' / 'observacion'."""
    if not spec:
        return 'observacion'
    tipo = spec.get('tipo_limite', 'maximo')
    li = spec.get('limite_industria')
    ml = spec.get('meta_lab')
    if tipo == 'ausencia':
        # Si reportan numero > 0 o texto que no diga "ausencia/negativo/<10/<1/0"
        v_str = (valor_texto or '').strip().lower()
        if valor is not None and valor > 0:
            return 'fuera_industria'
        if v_str and not any(k in v_str for k in ['ausencia','ausente','negativo','<10','<1','<100','no detect','0 ufc','sin crecimiento']):
            return 'observacion'
        return 'ok'
    if valor is None:
        return 'observacion'
    if tipo == 'maximo':
        if li is not None and valor > li:
            return 'fuera_industria'
        if ml is not None and valor > ml:
            return 'fuera_meta'
        return 'ok'
    if tipo == 'minimo':
        if li is not None and valor < li:
            return 'fuera_industria'
        if ml is not None and valor < ml:
            return 'fuera_meta'
        return 'ok'
    return 'observacion'


@bp.route('/api/calidad/micro/specs', methods=['GET', 'POST'])
def calidad_micro_specs():
    """GET: lista todas las specs (incluye los defaults globales aplicables a
    cualquier producto si no tiene override).
    POST: crea/actualiza spec para un producto+microorganismo."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    if request.method == 'POST':
        # RBAC fix 28-may · antes cualquier logueado podía mover los límites
        # micro (limite_industria) que definen el veredicto OOS/cuarentena.
        err, code = _require_calidad()
        if err:
            return err, code
        d = request.get_json(silent=True) or {}
        prod = (d.get('producto_nombre') or '').strip()
        micro = (d.get('microorganismo') or '').strip()
        if not prod or not micro:
            return jsonify({'error': 'producto_nombre y microorganismo requeridos'}), 400
        c.execute("""INSERT INTO calidad_micro_specs
            (producto_nombre, microorganismo, unidad, limite_industria,
             meta_lab, tipo_limite, metodo_referencia, activa)
            VALUES (?,?,?,?,?,?,?,1)
            ON CONFLICT(producto_nombre, microorganismo) DO UPDATE SET
              unidad=excluded.unidad,
              limite_industria=excluded.limite_industria,
              meta_lab=excluded.meta_lab,
              tipo_limite=excluded.tipo_limite,
              metodo_referencia=excluded.metodo_referencia""",
            (prod, micro, d.get('unidad') or 'UFC/g',
             d.get('limite_industria'), d.get('meta_lab'),
             d.get('tipo_limite') or 'maximo',
             d.get('metodo_referencia')))
        conn.commit()
        return jsonify({'ok': True})

    producto = (request.args.get('producto') or '').strip()
    rows = c.execute("""SELECT id, producto_nombre, microorganismo, unidad,
                              limite_industria, meta_lab, tipo_limite,
                              metodo_referencia, activa
                       FROM calidad_micro_specs
                       WHERE activa=1
                         AND (? = '' OR producto_nombre = ?)
                       ORDER BY producto_nombre, microorganismo""",
                    (producto, producto)).fetchall()
    cols = ['id','producto_nombre','microorganismo','unidad','limite_industria',
            'meta_lab','tipo_limite','metodo_referencia','activa']
    specs = [dict(zip(cols, r)) for r in rows]
    # Defaults globales
    rows_d = c.execute("""SELECT microorganismo, unidad, limite_industria,
                                 meta_lab, tipo_limite, descripcion
                         FROM calidad_micro_specs_default
                         ORDER BY id""").fetchall()
    cols_d = ['microorganismo','unidad','limite_industria','meta_lab','tipo_limite','descripcion']
    defaults = [dict(zip(cols_d, r)) for r in rows_d]
    return jsonify({'specs': specs, 'defaults': defaults})


@bp.route('/api/calidad/micro/resultados', methods=['GET', 'POST'])
def calidad_micro_resultados():
    """GET: lista resultados con filtros (producto, lote, estado, desde, hasta).
    POST: registra un resultado nuevo. Calcula estado vs spec."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()

    if request.method == 'POST':
        # RBAC fix 28-may · antes cualquier logueado podía inyectar lecturas
        # micro y disparar OOS/cuarentena de un lote (decisión regulatoria).
        err, code = _require_calidad()
        if err:
            return err, code
        d = request.get_json(silent=True) or {}
        producto = (d.get('producto_nombre') or '').strip()
        lote = (d.get('lote') or '').strip()
        micro = (d.get('microorganismo') or '').strip()
        if not producto or not lote or not micro:
            return jsonify({'error': 'producto_nombre, lote y microorganismo requeridos'}), 400
        valor = d.get('valor')
        try:
            valor = float(valor) if valor not in (None, '') else None
        except (TypeError, ValueError):
            valor = None
        valor_texto = (d.get('valor_texto') or '').strip() or None

        # Buscar spec: primero por producto, luego default
        spec = c.execute("""SELECT unidad, limite_industria, meta_lab, tipo_limite
                            FROM calidad_micro_specs
                            WHERE producto_nombre=? AND microorganismo=? AND activa=1""",
                         (producto, micro)).fetchone()
        if not spec:
            spec_d = c.execute("""SELECT unidad, limite_industria, meta_lab, tipo_limite
                                  FROM calidad_micro_specs_default
                                  WHERE microorganismo=?""", (micro,)).fetchone()
            spec = spec_d
        spec_dict = None
        if spec:
            spec_dict = {'unidad': spec[0], 'limite_industria': spec[1],
                         'meta_lab': spec[2], 'tipo_limite': spec[3]}
        estado = _calc_estado_micro(valor, valor_texto, spec_dict)
        unidad = (d.get('unidad') or (spec_dict['unidad'] if spec_dict else 'UFC/g'))

        # M24 · fecha_analisis ancla Colombia (UTC-5), NO _date.today() UTC: en CoA
        # (evidencia primaria INVIMA) un desfase +1 día en ventana nocturna invalida la firma.
        _hoy_col = c.execute("SELECT date('now','-5 hours')").fetchone()[0]
        fecha_analisis = (d.get('fecha_analisis') or '').strip() or _hoy_col
        # Fase 2 · COA del laboratorio (URL http/https) + ligado al EBR/lote del PT
        coa_url = (d.get('archivo_coa_url') or '').strip() or None
        if coa_url and not (coa_url.startswith('http://') or coa_url.startswith('https://')):
            return jsonify({'error': 'archivo_coa_url debe ser una URL http(s)'}), 400
        ebr_id = d.get('ebr_id')
        try:
            ebr_id = int(ebr_id) if ebr_id not in (None, '') else None
        except (TypeError, ValueError):
            ebr_id = None
        categoria = (d.get('categoria') or 'producto').strip().lower()
        if categoria not in ('producto', 'materia_prima', 'ambiente'):
            categoria = 'producto'
        n_referencia = (d.get('n_referencia') or '').strip() or None
        c.execute("""INSERT INTO calidad_micro_resultados
            (lote, producto_nombre, fecha_muestreo, fecha_analisis,
             microorganismo, valor, valor_texto, unidad, estado, laboratorio,
             analista, metodo, observaciones, creado_por, archivo_coa_url, ebr_id,
             categoria, n_referencia)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (lote, producto,
             (d.get('fecha_muestreo') or '').strip() or None,
             fecha_analisis,
             micro, valor, valor_texto, unidad, estado,
             (d.get('laboratorio') or 'Interno').strip(),
             (d.get('analista') or '').strip() or user,
             (d.get('metodo') or '').strip() or None,
             (d.get('observaciones') or '').strip() or None,
             user, coa_url, ebr_id, categoria, n_referencia))
        new_id = c.lastrowid

        # Si fuera_industria → crear OOS automáticamente · race-safe
        # Audit zero-error 2-may-2026: el código OOS-NNN se generaba con
        # SELECT MAX + INSERT sin retry · bajo concurrencia 2 micros simultáneos
        # podían generar mismo código → IntegrityError 500 al usuario.
        oos_codigo = None
        if estado == 'fuera_industria':
            def _insert_oos():
                last = c.execute(
                    "SELECT codigo FROM calidad_oos WHERE codigo LIKE 'OOS-%' ORDER BY id DESC LIMIT 1"
                ).fetchone()
                n = 1
                if last:
                    try: n = int(last[0].split('-')[-1]) + 1
                    except: n = 1
                cod = f'OOS-{n:03d}'
                c.execute("""INSERT INTO calidad_oos
                    (codigo, origen, lote, producto, parametro, valor_obtenido,
                     valor_obtenido_texto, valor_esperado_texto, limite_violado,
                     accion_inmediata, creado_por)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (cod, 'micro', lote, producto, micro, valor, valor_texto,
                     f'≤ {spec_dict["limite_industria"]} {unidad}' if spec_dict else 'según spec',
                     'limite_industria',
                     f'Lote {lote} pasa a CUARENTENA. No liberar hasta cierre OOS.',
                     user))
                return cod, c.lastrowid
            try:
                oos_codigo, oos_id = intentar_insert_con_retry(_insert_oos)
                c.execute("UPDATE calidad_micro_resultados SET oos_id=? WHERE id=?", (oos_id, new_id))
                # Audit log INVIMA · OOS es decisión regulatoria crítica
                try:
                    audit_log(c, usuario=user, accion='CREAR_OOS',
                              tabla='calidad_oos', registro_id=oos_codigo,
                              despues={'lote': lote, 'producto': producto,
                                        'parametro': micro, 'valor': valor})
                except Exception as _e:
                    log.warning('audit_log CREAR_OOS fallo: %s', _e)
            except Exception as _e:
                log.exception('crear OOS fallo: %s', _e)
                # NO silenciar · OOS es regulatorio. Pero tampoco abortar el
                # registro de micro · loguear y seguir (oos_codigo queda None).
                oos_codigo = None
            # Notif in-app a calidad + admin (solo si OOS se creó OK)
            if oos_codigo:
                try:
                    from blueprints.notif import push_notif_multi
                    push_notif_multi(
                        ['controlcalidad.espagiria','aseguramiento.espagiria','sebastian','alejandro'],
                        'capa', f'⚠ OOS {oos_codigo}: {micro} en {producto}',
                        body=f'Lote {lote} · valor {valor or valor_texto} {unidad}',
                        link='/calidad', remitente=user, importante=True
                    )
                except Exception:
                    pass
        elif estado == 'fuera_meta':
            # Notif menos urgente · solo a calidad
            try:
                from blueprints.notif import push_notif
                push_notif('controlcalidad.espagiria', 'capa',
                           f'Resultado fuera de meta lab: {micro} en {producto}',
                           body=f'Lote {lote} · valor {valor or valor_texto} {unidad}',
                           link='/calidad', remitente=user)
            except Exception: pass
        conn.commit()
        return jsonify({'ok': True, 'id': new_id, 'estado': estado, 'oos_codigo': oos_codigo}), 201

    # GET
    producto = (request.args.get('producto') or '').strip()
    lote = (request.args.get('lote') or '').strip()
    estado = (request.args.get('estado') or '').strip()
    desde = (request.args.get('desde') or '').strip()
    hasta = (request.args.get('hasta') or '').strip()
    where = []; params = []
    if producto: where.append('producto_nombre=?'); params.append(producto)
    if lote: where.append('lote=?'); params.append(lote)
    if estado: where.append('estado=?'); params.append(estado)
    if desde: where.append('fecha_analisis >= ?'); params.append(desde)
    if hasta: where.append('fecha_analisis <= ?'); params.append(hasta)
    categoria_f = (request.args.get('categoria') or '').strip()
    if categoria_f:
        where.append('COALESCE(categoria,?)=?'); params.extend([categoria_f, categoria_f])
    sql = """SELECT id, lote, producto_nombre, fecha_muestreo, fecha_analisis,
                    microorganismo, valor, valor_texto, unidad, estado,
                    laboratorio, analista, metodo, observaciones, oos_id,
                    COALESCE(archivo_coa_url,''), ebr_id,
                    COALESCE(categoria,''), COALESCE(n_referencia,'')
             FROM calidad_micro_resultados"""
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY fecha_analisis DESC, id DESC LIMIT 500"
    rows = c.execute(sql, params).fetchall()
    cols = ['id','lote','producto_nombre','fecha_muestreo','fecha_analisis',
            'microorganismo','valor','valor_texto','unidad','estado',
            'laboratorio','analista','metodo','observaciones','oos_id',
            'archivo_coa_url','ebr_id','categoria','n_referencia']
    return jsonify({'resultados': [dict(zip(cols, r)) for r in rows]})


@bp.route('/api/calidad/micro/heatmap', methods=['GET'])
def calidad_micro_heatmap():
    """Mapa de calor: matriz producto × microorganismo con:
       - peor_estado (worst case en últimos N meses)
       - n_resultados
       - n_fuera_industria
       - n_fuera_meta
       - ultimo_valor / fecha
    Window: últimos 12 meses por default.
    Sebastian: 'tener un mapa de calor o de resultados consolidados con alerta'.
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    meses = int(request.args.get('meses', 12))
    conn = get_db(); c = conn.cursor()

    # Lista de microorganismos relevantes (defaults + custom usados)
    micros = [r[0] for r in c.execute(
        "SELECT microorganismo FROM calidad_micro_specs_default ORDER BY id"
    ).fetchall()]
    extras = [r[0] for r in c.execute(
        "SELECT DISTINCT microorganismo FROM calidad_micro_resultados "
        "WHERE microorganismo NOT IN (SELECT microorganismo FROM calidad_micro_specs_default)"
    ).fetchall()]
    micros += extras

    # Lista de productos con resultados en la ventana. Excluye monitoreo AMBIENTAL
    # (superficies/uniformes/agua) para que el heatmap sea producto×micro limpio.
    prods = [r[0] for r in c.execute(
        "SELECT DISTINCT producto_nombre FROM calidad_micro_resultados "
        "WHERE COALESCE(categoria,'producto')<>'ambiente' "
        "AND fecha_analisis >= date('now', '-5 hours', '-' || ? || ' months') "
        "ORDER BY producto_nombre", (meses,)
    ).fetchall()]

    # Construir matriz · PERF 16-jul: antes eran N×M queries (2 por cada celda producto×micro →
    # cientos de full-scans → el endpoint colgaba → "Cargando matriz..." infinito). Ahora 2 queries
    # agregadas + build en Python.
    _win = "COALESCE(categoria,'producto')<>'ambiente' AND fecha_analisis >= date('now','-5 hours','-' || ? || ' months')"
    _agg = c.execute(
        "SELECT producto_nombre, microorganismo, COUNT(*), "
        "SUM(CASE WHEN estado='fuera_industria' THEN 1 ELSE 0 END), "
        "SUM(CASE WHEN estado='fuera_meta' THEN 1 ELSE 0 END), MAX(fecha_analisis) "
        "FROM calidad_micro_resultados WHERE " + _win + " GROUP BY producto_nombre, microorganismo",
        (meses,)).fetchall()
    _aggmap = {(r[0], r[1]): r for r in _agg}
    # último resultado por (producto, micro): traer ordenado desc y quedarse con el 1º de cada par
    _ultmap = {}
    for r in c.execute(
        "SELECT producto_nombre, microorganismo, valor, valor_texto, unidad "
        "FROM calidad_micro_resultados WHERE " + _win + " ORDER BY fecha_analisis DESC, id DESC",
        (meses,)).fetchall():
        _k = (r[0], r[1])
        if _k not in _ultmap:
            _ultmap[_k] = r
    matriz = []
    for prod in prods:
        row = {'producto': prod, 'cells': []}
        for m in micros:
            a = _aggmap.get((prod, m))
            if not a or not a[2]:
                row['cells'].append({'micro': m, 'n': 0, 'estado': 'sin_dato'})
                continue
            n, n_fi, n_fm, ultima = a[2], (a[3] or 0), (a[4] or 0), a[5]
            u = _ultmap.get((prod, m))
            estado_peor = 'fuera_industria' if n_fi > 0 else ('fuera_meta' if n_fm > 0 else 'ok')
            row['cells'].append({
                'micro': m, 'n': n,
                'n_fuera_industria': n_fi,
                'n_fuera_meta': n_fm,
                'estado': estado_peor,
                'ultima_fecha': ultima,
                'ultimo_valor': u[2] if u else None,
                'ultimo_texto': u[3] if u else None,
                'unidad': u[4] if u else 'UFC/g',
            })
        matriz.append(row)

    # KPIs globales (solo producto/MP · el ambiente se mide aparte)
    _noamb = "COALESCE(categoria,'producto')<>'ambiente' AND "
    total_res = c.execute(
        "SELECT COUNT(*) FROM calidad_micro_resultados WHERE " + _noamb + "fecha_analisis >= date('now', '-5 hours', '-' || ? || ' months')", (meses,)
    ).fetchone()[0] or 0
    total_fi = c.execute(
        "SELECT COUNT(*) FROM calidad_micro_resultados WHERE " + _noamb + "estado='fuera_industria' AND fecha_analisis >= date('now', '-5 hours', '-' || ? || ' months')", (meses,)
    ).fetchone()[0] or 0
    total_fm = c.execute(
        "SELECT COUNT(*) FROM calidad_micro_resultados WHERE " + _noamb + "estado='fuera_meta' AND fecha_analisis >= date('now', '-5 hours', '-' || ? || ' months')", (meses,)
    ).fetchone()[0] or 0

    return jsonify({
        'meses_ventana': meses,
        'microorganismos': micros,
        'productos': prods,
        'matriz': matriz,
        'kpis': {
            'total_resultados': total_res,
            'total_fuera_industria': total_fi,
            'total_fuera_meta': total_fm,
            'tasa_ok': round((total_res - total_fi - total_fm) * 100 / total_res, 1) if total_res else None,
        },
    })


# ════════════════════════════════════════════════════════════════════════
# ANÁLISIS MICRO · panel pro (gráficas) + alertas accionables · 14-jun-2026
# Todo cross-DB (SUBSTR para mes, cutoff calculado en Python · sin julianday).
# ════════════════════════════════════════════════════════════════════════
_PATOGENOS = ('E. coli', 'Staphylococcus aureus', 'Pseudomonas aeruginosa',
              'Candida albicans', 'Burkholderia cepacia')


def _cutoff_meses(c, meses):
    """Primer día del mes hace `meses` meses, anclado a Colombia (M24)."""
    hoy = c.execute("SELECT date('now','-5 hours')").fetchone()[0]
    y, m = int(hoy[0:4]), int(hoy[5:7])
    m -= int(meses)
    while m <= 0:
        m += 12; y -= 1
    return f"{y:04d}-{m:02d}-01", hoy


@bp.route('/api/calidad/micro/analisis', methods=['GET'])
def calidad_micro_analisis():
    """Datos para el panel de gráficas de análisis micro (5 paneles en 1 llamada).
    Excluye 'ambiente' de los paneles de producto (tiene su propio panel)."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    meses = int(request.args.get('meses', 6) or 6)
    conn = get_db(); c = conn.cursor()
    cutoff, hoy = _cutoff_meses(c, meses)
    NOAMB = "COALESCE(categoria,'producto')<>'ambiente'"

    def q(sql, params=()):
        return c.execute(sql, params).fetchall()

    # Panel 1 · Tendencia OOS por mes (producto/MP)
    rows = q(f"SELECT SUBSTR(fecha_analisis,1,7) ym, COUNT(*), "
             f"SUM(CASE WHEN estado='fuera_industria' THEN 1 ELSE 0 END) "
             f"FROM calidad_micro_resultados WHERE {NOAMB} AND fecha_analisis>=? "
             f"GROUP BY SUBSTR(fecha_analisis,1,7) ORDER BY ym", (cutoff,))
    tendencia = [{'mes': r[0], 'total': r[1], 'oos': r[2] or 0,
                  'oos_pct': round((r[2] or 0) * 100 / r[1], 1) if r[1] else 0} for r in rows]

    # Panel 2 · Top microorganismos (producto/MP)
    rows = q(f"SELECT microorganismo, COUNT(*), "
             f"SUM(CASE WHEN estado='fuera_industria' THEN 1 ELSE 0 END) "
             f"FROM calidad_micro_resultados WHERE {NOAMB} AND fecha_analisis>=? "
             f"GROUP BY microorganismo ORDER BY COUNT(*) DESC LIMIT 10", (cutoff,))
    top_micro = [{'microorganismo': r[0], 'n': r[1], 'oos': r[2] or 0} for r in rows]

    # Panel 3 · Conformidad por producto (peores primero)
    rows = q(f"SELECT producto_nombre, COUNT(*), "
             f"SUM(CASE WHEN estado='ok' THEN 1 ELSE 0 END), "
             f"SUM(CASE WHEN estado='fuera_meta' THEN 1 ELSE 0 END), "
             f"SUM(CASE WHEN estado='fuera_industria' THEN 1 ELSE 0 END) "
             f"FROM calidad_micro_resultados WHERE {NOAMB} AND fecha_analisis>=? "
             f"GROUP BY producto_nombre ORDER BY "
             f"(SUM(CASE WHEN estado='ok' THEN 1 ELSE 0 END)*1.0/COUNT(*)) ASC, COUNT(*) DESC LIMIT 15", (cutoff,))
    conformidad = [{'producto': r[0], 'total': r[1], 'ok': r[2] or 0,
                    'meta': r[3] or 0, 'oos': r[4] or 0,
                    'pct_ok': round((r[2] or 0) * 100 / r[1], 1) if r[1] else 0} for r in rows]

    # Panel 4 · Top hallazgos OOS (producto + ambiente)
    rows = q("SELECT producto_nombre, COALESCE(categoria,'producto'), COUNT(*), MAX(fecha_analisis) "
             "FROM calidad_micro_resultados WHERE estado='fuera_industria' AND fecha_analisis>=? "
             "GROUP BY producto_nombre, COALESCE(categoria,'producto') ORDER BY COUNT(*) DESC, MAX(fecha_analisis) DESC LIMIT 12", (cutoff,))
    hallazgos = [{'nombre': r[0], 'categoria': r[1], 'oos': r[2], 'ultima': r[3]} for r in rows]

    # Panel 5 · Monitoreo ambiental por punto (categoria=ambiente)
    rows = q("SELECT producto_nombre, COUNT(*), "
             "SUM(CASE WHEN estado='fuera_industria' THEN 1 ELSE 0 END), MAX(fecha_analisis) "
             "FROM calidad_micro_resultados WHERE categoria='ambiente' AND fecha_analisis>=? "
             "GROUP BY producto_nombre ORDER BY SUM(CASE WHEN estado='fuera_industria' THEN 1 ELSE 0 END) DESC, MAX(fecha_analisis) DESC LIMIT 25", (cutoff,))
    ambiental = [{'punto': r[0], 'n': r[1], 'oos': r[2] or 0, 'ultima': r[3]} for r in rows]

    return jsonify({'meses': meses, 'desde': cutoff, 'hoy': hoy,
                    'tendencia': tendencia, 'top_microorganismos': top_micro,
                    'conformidad': conformidad, 'hallazgos': hallazgos, 'ambiental': ambiental})


@bp.route('/api/calidad/micro/alertas', methods=['GET'])
def calidad_micro_alertas():
    """Alertas accionables de micro para la bandeja del día."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    cutoff_30, hoy = _cutoff_meses(c, 1)
    alertas = []

    # A1 · tendencia creciente de OOS (mes actual vs anterior · producto/MP)
    NOAMB = "COALESCE(categoria,'producto')<>'ambiente'"
    rows = c.execute(f"SELECT SUBSTR(fecha_analisis,1,7) ym, COUNT(*), "
                     f"SUM(CASE WHEN estado='fuera_industria' THEN 1 ELSE 0 END) "
                     f"FROM calidad_micro_resultados WHERE {NOAMB} "
                     f"GROUP BY SUBSTR(fecha_analisis,1,7) ORDER BY ym DESC LIMIT 2").fetchall()
    if len(rows) == 2:
        cur_pct = (rows[0][2] or 0) * 100 / rows[0][1] if rows[0][1] else 0
        prev_pct = (rows[1][2] or 0) * 100 / rows[1][1] if rows[1][1] else 0
        if cur_pct > prev_pct and cur_pct > 0:
            alertas.append({'tipo': 'tendencia', 'severidad': 'rojo',
                            'mensaje': f'Tendencia ↑ de OOS micro: {round(cur_pct,1)}% este mes vs {round(prev_pct,1)}% el anterior. Investigar causa raíz.',
                            'cantidad': rows[0][2] or 0})

    # A2 · OOS repetido en mismo (producto × microorganismo) en 30d
    rep = c.execute("SELECT producto_nombre, microorganismo, COUNT(*) FROM calidad_micro_resultados "
                    "WHERE estado='fuera_industria' AND fecha_analisis>=? "
                    "GROUP BY producto_nombre, microorganismo HAVING COUNT(*)>=2 ORDER BY COUNT(*) DESC", (cutoff_30,)).fetchall()
    for r in rep:
        alertas.append({'tipo': 'repetido', 'severidad': 'naranja',
                        'mensaje': f'{r[2]} OOS de {r[1]} en "{r[0]}" en 30 días · patrón. Muestreo inmediato post-corrección.',
                        'cantidad': r[2]})

    # A3 · patógeno crítico detectado (últimos 30d)
    ph = ','.join('?' * len(_PATOGENOS))
    pat = c.execute(f"SELECT producto_nombre, microorganismo, lote, fecha_analisis, COALESCE(categoria,'') "
                    f"FROM calidad_micro_resultados WHERE estado='fuera_industria' "
                    f"AND microorganismo IN ({ph}) AND fecha_analisis>=? "
                    f"ORDER BY fecha_analisis DESC LIMIT 10", (*_PATOGENOS, cutoff_30)).fetchall()
    for r in pat:
        alertas.append({'tipo': 'patogeno', 'severidad': 'rojo',
                        'mensaje': f'⚠ Patógeno {r[1]} detectado en "{r[0]}"'
                                   + (f' lote {r[2]}' if r[2] else '') + f' ({r[3]}). Cuarentena + OOS + notificar gerencia.',
                        'cantidad': 1})

    return jsonify({'alertas': alertas, 'total': len(alertas),
                    'criticas': sum(1 for a in alertas if a['severidad'] == 'rojo')})


@bp.route('/api/calidad/lotes-planta', methods=['GET'])
def calidad_lotes_planta():
    """Lotes reales de Planta (EBR) para el picker al registrar un análisis. Conecta
    Calidad↔Producción: al elegir un lote se autocompleta producto + ebr_id, así el
    resultado micro queda ligado al legajo real (y habilita el gate de liberación)."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    try:
        dias = int(request.args.get('dias', 90) or 90)
    except ValueError:
        dias = 90
    hoy = c.execute("SELECT date('now','-5 hours')").fetchone()[0]
    try:
        cutoff = (datetime.fromisoformat(hoy[:10]) - timedelta(days=dias)).date().isoformat()
    except Exception:
        cutoff = '2025-01-01'
    try:
        rows = c.execute(
            "SELECT e.id, COALESCE(NULLIF(e.lote_codigo,''), e.lote), COALESCE(mt.producto_nombre,''), "
            "       e.estado, COALESCE(e.completado_at_utc, e.iniciado_at_utc,'') "
            "FROM ebr_ejecuciones e LEFT JOIN mbr_templates mt ON mt.id = e.mbr_template_id "
            "WHERE COALESCE(e.completado_at_utc, e.iniciado_at_utc,'') >= ? "
            "ORDER BY COALESCE(e.completado_at_utc, e.iniciado_at_utc,'') DESC LIMIT 150",
            (cutoff,)).fetchall()
    except Exception as e:
        logging.getLogger('calidad').info('lotes-planta: %s', e)
        rows = []
    lotes = [{'ebr_id': r[0], 'lote': r[1], 'producto': r[2],
              'estado': r[3], 'fecha': (r[4] or '')[:10]} for r in rows if r[1]]
    return jsonify({'lotes': lotes, 'total': len(lotes)})


@bp.route('/api/calidad/fisicoquimica/resultados', methods=['GET', 'POST'])
def calidad_fisicoquimica_resultados():
    """Resultados FISICOQUÍMICOS (pH, densidad, fósforo, viscosidad…). Valor medido vs
    referencia, sin recuento micro. GET lista; POST registra (solo Calidad/Admin)."""
    if request.method == 'POST':
        err, code = _require_calidad()
        if err:
            return err, code
    elif 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()

    if request.method == 'POST':
        d = request.get_json(silent=True) or {}
        producto = (d.get('producto_nombre') or '').strip()
        parametro = (d.get('parametro') or '').strip()
        if not producto or not parametro:
            return jsonify({'error': 'producto_nombre y parametro requeridos'}), 400
        coa = (d.get('archivo_coa_url') or '').strip() or None
        if coa and not (coa.startswith('http://') or coa.startswith('https://')):
            return jsonify({'error': 'archivo_coa_url debe ser URL http(s)'}), 400
        ebr_id = d.get('ebr_id')
        try:
            ebr_id = int(ebr_id) if ebr_id not in (None, '') else None
        except (TypeError, ValueError):
            ebr_id = None
        cat = (d.get('categoria') or 'producto').strip().lower()
        if cat not in ('producto', 'materia_prima', 'ambiente'):
            cat = 'producto'
        # M24 · ancla Colombia (UTC-5) para el fallback de fecha_analisis (CoA INVIMA)
        _hoy_col = c.execute("SELECT date('now','-5 hours')").fetchone()[0]
        c.execute(
            "INSERT INTO calidad_fisicoquimica_resultados "
            "(lote,producto_nombre,categoria,n_referencia,fecha_muestreo,fecha_analisis,parametro,"
            " metodo,resultado,unidad,valor_referencia,estado,laboratorio,analista,archivo_coa_url,ebr_id,observaciones,creado_por) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ((d.get('lote') or '').strip(), producto, cat,
             (d.get('n_referencia') or '').strip() or None,
             (d.get('fecha_muestreo') or '').strip() or None,
             (d.get('fecha_analisis') or '').strip() or _hoy_col,
             parametro, (d.get('metodo') or '').strip() or None,
             (d.get('resultado') or '').strip() or None,
             (d.get('unidad') or '').strip() or None,
             (d.get('valor_referencia') or '').strip() or None,
             (d.get('estado') or 'informado').strip().lower(),
             (d.get('laboratorio') or 'Interno').strip(),
             (d.get('analista') or '').strip() or user, coa, ebr_id,
             (d.get('observaciones') or '').strip() or None, user))
        new_id = c.lastrowid
        audit_log(c, usuario=user, accion='CREAR_FQ', tabla='calidad_fisicoquimica_resultados',
                  registro_id=new_id, despues={'producto': producto, 'parametro': parametro})
        conn.commit()
        return jsonify({'ok': True, 'id': new_id}), 201

    # GET
    prod = (request.args.get('producto') or '').strip()
    lote = (request.args.get('lote') or '').strip()
    where, params = [], []
    if prod:
        where.append('producto_nombre=?'); params.append(prod)
    if lote:
        where.append('lote=?'); params.append(lote)
    sql = ("SELECT id, lote, producto_nombre, categoria, n_referencia, fecha_analisis, "
           "parametro, metodo, resultado, unidad, valor_referencia, estado, laboratorio, "
           "COALESCE(archivo_coa_url,''), ebr_id FROM calidad_fisicoquimica_resultados")
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY fecha_analisis DESC, id DESC LIMIT 500"
    rows = c.execute(sql, params).fetchall()
    cols = ['id', 'lote', 'producto_nombre', 'categoria', 'n_referencia', 'fecha_analisis',
            'parametro', 'metodo', 'resultado', 'unidad', 'valor_referencia', 'estado',
            'laboratorio', 'archivo_coa_url', 'ebr_id']
    return jsonify({'resultados': [dict(zip(cols, r)) for r in rows]})


def _coas_dir():
    import os as _os
    from config import DB_PATH
    d = _os.path.join(_os.path.dirname(DB_PATH) or '.', 'coas')
    _os.makedirs(d, exist_ok=True)
    return d


@bp.route('/api/calidad/micro/importar-eml', methods=['POST'])
def calidad_importar_eml():
    """Sube el correo .eml del laboratorio (Microlab) → parsea los PDF, hace upsert de los
    resultados (micro + fisicoquímico, idempotente por N° de informe) y guarda cada COA.
    Re-subir un correo NO duplica: actualiza el COA de los que ya estaban."""
    err, code = _require_calidad()
    if err:
        return err, code
    import os as _os
    import re as _re
    f = request.files.get('archivo')
    if not f or not (f.filename or '').lower().endswith('.eml'):
        return jsonify({'error': 'Subí el archivo del correo (.eml) del laboratorio.'}), 400
    data = f.read()
    if not data or len(data) > 30 * 1024 * 1024:
        return jsonify({'error': 'Archivo vacío o demasiado grande (>30 MB).'}), 400
    try:
        from coa_import import parse_eml_bytes, upsert_sample
    except ImportError:
        from api.coa_import import parse_eml_bytes, upsert_sample
    try:
        parsed = parse_eml_bytes(data)
    except ImportError:
        return jsonify({'error': 'El servidor aún no tiene el lector de PDF (pdfplumber). '
                                 'Reintentá luego del próximo deploy.'}), 503
    except Exception as e:
        return jsonify({'error': f'No se pudo leer el correo: {e}'}), 400
    samples = parsed.get('samples') or []
    if not samples:
        return jsonify({'error': 'El correo no tiene informes de laboratorio reconocibles '
                                 '(¿es un informe de Microlab con PDF adjunto?).'}), 422
    coas_dir = _coas_dir()
    conn = get_db(); c = conn.cursor()
    user = session.get('compras_user', '')
    tot = {'informes': 0, 'nuevos': 0, 'actualizados': 0, 'oos': 0}
    for s in samples:
        ref = s.get('ref') or 'coa'
        safe = _re.sub(r'[^A-Za-z0-9_.-]', '_', ref) + '.pdf'
        try:
            with open(_os.path.join(coas_dir, safe), 'wb') as fh:
                fh.write(s.get('pdf_bytes') or b'')
        except Exception as _e:
            logging.getLogger('calidad').warning('no se pudo guardar COA %s: %s', safe, _e)
        coa_url = '/api/calidad/micro/coa/' + safe
        r = upsert_sample(conn, s, coa_url, usuario=user)
        tot['nuevos'] += r['nuevos']; tot['actualizados'] += r['actualizados']
        tot['oos'] += r['oos']; tot['informes'] += 1
    audit_log(c, usuario=user, accion='IMPORTAR_COA_EML', tabla='calidad_micro_resultados',
              registro_id=0, despues={**tot, 'archivo': (f.filename or '')[:120]})
    conn.commit()
    return jsonify({'ok': True, **tot, 'archivo': f.filename})


@bp.route('/api/calidad/micro/coa/<path:fname>', methods=['GET'])
def calidad_servir_coa(fname):
    """Sirve el PDF del COA guardado (solo Calidad/Aseguramiento/Admin · anti path-traversal)."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    u = session.get('compras_user', '')
    try:
        from config import ASEGURAMIENTO_USERS as _AC
    except Exception:
        _AC = set()
    if u not in (set(CALIDAD_USERS) | set(_AC) | set(ADMIN_USERS)):
        return jsonify({'error': 'no autorizado'}), 403
    import os as _os
    import re as _re
    safe = _os.path.basename(fname)
    if not _re.match(r'^[A-Za-z0-9_.\-]+\.pdf$', safe):
        return jsonify({'error': 'nombre inválido'}), 400
    path = _os.path.join(_coas_dir(), safe)
    if not _os.path.exists(path):
        return jsonify({'error': 'COA no encontrado (¿se importó el informe?)'}), 404
    from flask import send_file
    return send_file(path, mimetype='application/pdf', as_attachment=False,
                     download_name=safe)


@bp.route('/api/calidad/agua/registros', methods=['GET', 'POST'])
def calidad_agua_registros():
    """COC-PRO-008 Sistema de Agua. GET lista registros con filtro fecha+punto.
    POST registra una lectura nueva. Calcula estado vs umbrales BPM:
       pH purificada: 5.0-7.5
       conductividad ≤ 1.3 µS/cm a 25°C (USP <645>)
       TOC ≤ 500 ppb (USP <643>)
       microorganismos ≤ 100 UFC/100mL (USP)
    """
    if request.method == 'POST':
        # POST requiere Calidad/Admin · evidencia INVIMA
        err, code = _require_calidad()
        if err: return err, code
    elif 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    conn = get_db(); c = conn.cursor()

    if request.method == 'POST':
        d = request.get_json(silent=True) or {}
        punto = (d.get('punto_muestreo') or '').strip()
        if not punto:
            return jsonify({'error': 'punto_muestreo requerido'}), 400

        # Audit zero-error 2-may-2026: validación de plausibilidad física
        # antes de aceptar valores. Antes pH=15 se aceptaba como 'fuera_spec'
        # · ahora rechazamos físicamente imposible.
        ph = d.get('ph')
        cond = d.get('conductividad_us_cm')
        toc = d.get('toc_ppb')
        micro = d.get('microorganismos_ufc_ml')
        try: ph = float(ph) if ph not in (None,'') else None
        except: ph = None
        try: cond = float(cond) if cond not in (None,'') else None
        except: cond = None
        try: toc = float(toc) if toc not in (None,'') else None
        except: toc = None
        try: micro = float(micro) if micro not in (None,'') else None
        except: micro = None
        # Rangos físicos plausibles (valores fuera = error de tipeo)
        if ph is not None and not (0 <= ph <= 14):
            return jsonify({'error': f'pH={ph} fuera de rango físico (0-14)'}), 400
        if cond is not None and not (0 <= cond <= 50):
            return jsonify({'error': f'conductividad={cond} fuera de rango (0-50 µS/cm)'}), 400
        if toc is not None and toc < 0:
            return jsonify({'error': 'TOC no puede ser negativo'}), 400
        if micro is not None and micro < 0:
            return jsonify({'error': 'microorganismos no puede ser negativo'}), 400

        # Calcular estado (USP · agua purificada)
        estado = 'ok'
        warnings = []
        if ph is not None:
            if ph < 5.0 or ph > 7.5: estado = 'fuera_spec'; warnings.append(f'pH={ph} fuera 5.0-7.5')
            elif ph < 5.5 or ph > 7.0: estado = 'alerta' if estado=='ok' else estado
        if cond is not None:
            if cond > 1.3: estado = 'fuera_spec'; warnings.append(f'cond={cond}µS > 1.3')
            elif cond > 1.1: estado = 'alerta' if estado=='ok' else estado
        if toc is not None:
            if toc > 500: estado = 'fuera_spec'; warnings.append(f'TOC={toc}ppb > 500')
            elif toc > 400: estado = 'alerta' if estado=='ok' else estado
        if micro is not None:
            if micro > 100: estado = 'fuera_spec'; warnings.append(f'micro={micro}UFC/ml > 100')
            elif micro > 50: estado = 'alerta' if estado=='ok' else estado

        # FIX · 2026-06-12 · TZ writer↔bandeja: fecha por defecto = HOY Colombia
        # vía SQLite (COALESCE más abajo), igual anclaje que la bandeja de Calidad
        # (date('now','-5 hours')). Antes _date.today() (UTC en Render) desfasaba de
        # noche → la lectura del día no se detectaba → falso "falta registro de agua".
        fecha_reg = (d.get('fecha') or '').strip() or None
        obs_extra = d.get('observaciones') or ''
        if warnings:
            obs_final = '; '.join(warnings) + (' | ' + obs_extra if obs_extra else '')
        else:
            obs_final = obs_extra.strip() or None
        c.execute("""INSERT INTO calidad_sistema_agua
            (fecha, hora, punto_muestreo, tipo_agua, ph, conductividad_us_cm,
             toc_ppb, microorganismos_ufc_ml, cloro_residual_ppm, temperatura_c,
             estado, observaciones, operador)
            VALUES (COALESCE(?, date('now','-5 hours')),?,?,?,?,?,?,?,?,?,?,?,?)""",
            (fecha_reg,
             (d.get('hora') or '').strip() or None,
             punto, d.get('tipo_agua') or 'purificada',
             ph, cond, toc, micro,
             d.get('cloro_residual_ppm'), d.get('temperatura_c'),
             estado, obs_final, user))
        new_id = c.lastrowid
        # Audit log INVIMA · cada lectura de agua es evidencia regulatoria
        try:
            audit_log(c, usuario=user, accion='REGISTRAR_AGUA',
                      tabla='calidad_sistema_agua', registro_id=new_id,
                      despues={'fecha': fecha_reg, 'punto': punto, 'estado': estado,
                                'ph': ph, 'conductividad': cond, 'toc': toc, 'micro': micro})
        except Exception as _e:
            log.warning('audit_log REGISTRAR_AGUA fallo: %s', _e)
        # Si fuera_spec → notif urgente
        if estado == 'fuera_spec':
            try:
                from blueprints.notif import push_notif_multi
                push_notif_multi(
                    ['controlcalidad.espagiria','aseguramiento.espagiria','sebastian'],
                    'capa', f'⚠ Sistema de agua FUERA DE SPEC: {punto}',
                    body='; '.join(warnings),
                    link='/calidad', remitente=user, importante=True
                )
            except Exception: pass
        conn.commit()
        return jsonify({'ok': True, 'id': new_id, 'estado': estado, 'warnings': warnings}), 201

    # GET
    desde = (request.args.get('desde') or '').strip()
    hasta = (request.args.get('hasta') or '').strip()
    punto = (request.args.get('punto') or '').strip()
    where = []; params = []
    if desde: where.append('fecha >= ?'); params.append(desde)
    if hasta: where.append('fecha <= ?'); params.append(hasta)
    if punto: where.append('punto_muestreo=?'); params.append(punto)
    sql = "SELECT * FROM calidad_sistema_agua"
    if where: sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY fecha DESC, hora DESC, id DESC LIMIT 500"
    rows = c.execute(sql, params).fetchall()
    cols = [d[0] for d in c.description]
    out = [dict(zip(cols, r)) for r in rows]
    return jsonify({'registros': out})


@bp.route('/api/calidad/agua/estado-hoy', methods=['GET'])
def calidad_agua_estado_hoy():
    """Estado del registro del sistema de agua HOY.

    Retorna: { registrado: bool, ultimo_registro: {...}, hora_actual,
               necesita_alerta: bool (si pasaron 12pm sin registro) }
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    row = c.execute("""
        SELECT id, fecha, hora, punto_muestreo, tipo_agua, ph,
               conductividad_us_cm, toc_ppb, microorganismos_ufc_ml,
               cloro_residual_ppm, temperatura_c, estado, observaciones, operador
        FROM calidad_sistema_agua
        WHERE date(fecha) = date('now', '-5 hours')
        ORDER BY id DESC LIMIT 1
    """).fetchone()
    ahora = datetime.now()
    out = {
        'fecha_hoy': ahora.date().isoformat(),
        'hora_actual': ahora.strftime('%H:%M'),
        'registrado': bool(row),
        'necesita_alerta': False,
        'ultimo_registro': None,
    }
    if row:
        cols = ['id','fecha','hora','punto_muestreo','tipo_agua','ph',
                'conductividad_us_cm','toc_ppb','microorganismos_ufc_ml',
                'cloro_residual_ppm','temperatura_c','estado',
                'observaciones','operador']
        out['ultimo_registro'] = dict(zip(cols, row))
    else:
        # Si pasó del mediodía y no hay registro → alerta
        out['necesita_alerta'] = ahora.hour >= 12
    return jsonify(out)


@bp.route('/api/calidad/agua/tendencia', methods=['GET'])
def calidad_agua_tendencia():
    """Tendencia del sistema de agua últimos N días (default 30).

    Retorna arrays para gráfico + drift detection (3+ lecturas crecientes
    consecutivas en conductividad), conteo fuera_spec, kpis.
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    try:
        dias = int(request.args.get('dias', 30))
    except (ValueError, TypeError):
        dias = 30
    if not (1 <= dias <= 365):
        return jsonify({'error': 'dias fuera de rango (1-365)'}), 400
    conn = get_db(); c = conn.cursor()
    # Una lectura por fecha (la más reciente del día)
    rows = c.execute("""
        SELECT fecha, MAX(hora) as hora_max,
               AVG(ph) as ph_avg,
               AVG(conductividad_us_cm) as cond_avg,
               AVG(toc_ppb) as toc_avg,
               AVG(microorganismos_ufc_ml) as micro_avg,
               SUM(CASE WHEN estado='fuera_spec' THEN 1 ELSE 0 END) as n_fuera,
               SUM(CASE WHEN estado='alerta' THEN 1 ELSE 0 END) as n_alerta,
               COUNT(*) as n_total
        FROM calidad_sistema_agua
        WHERE date(fecha) >= date('now', '-5 hours', '-' || ? || ' days')
        GROUP BY fecha
        ORDER BY fecha ASC
    """, (dias,)).fetchall()
    serie = [{
        'fecha': r[0], 'hora_max': r[1],
        'ph': round(r[2], 2) if r[2] is not None else None,
        'conductividad': round(r[3], 3) if r[3] is not None else None,
        'toc': round(r[4], 1) if r[4] is not None else None,
        'micro': round(r[5], 1) if r[5] is not None else None,
        'n_fuera_spec': r[6] or 0,
        'n_alerta': r[7] or 0,
        'n_total': r[8] or 0,
    } for r in rows]

    # Drift detection: 3+ lecturas consecutivas crecientes en conductividad
    drift_alerta = False
    drift_dias = 0
    if len(serie) >= 3:
        cond_vals = [(s['fecha'], s['conductividad']) for s in serie if s['conductividad'] is not None]
        if len(cond_vals) >= 3:
            # Ventana móvil de 3
            for i in range(len(cond_vals) - 2):
                a, b, c_v = cond_vals[i][1], cond_vals[i+1][1], cond_vals[i+2][1]
                if a < b < c_v:
                    drift_dias = 3
                    if i + 3 < len(cond_vals) and cond_vals[i+3][1] > c_v:
                        drift_dias = 4
                    drift_alerta = True
            # Si la racha continúa hasta hoy, también marca
            ult3 = cond_vals[-3:]
            if len(ult3) == 3 and ult3[0][1] < ult3[1][1] < ult3[2][1]:
                drift_alerta = True

    total_dias_con_registro = sum(1 for s in serie if s['n_total'] > 0)
    total_fuera_spec = sum(s['n_fuera_spec'] for s in serie)
    total_alerta = sum(s['n_alerta'] for s in serie)
    total_lecturas = sum(s['n_total'] for s in serie)

    return jsonify({
        'dias_ventana': dias,
        'serie': serie,
        'drift_alerta': drift_alerta,
        'drift_dias_consecutivos': drift_dias,
        'kpis': {
            'dias_con_registro': total_dias_con_registro,
            'dias_sin_registro': dias - total_dias_con_registro,
            'cobertura_pct': round(total_dias_con_registro * 100 / dias, 1) if dias else 0,
            'lecturas_totales': total_lecturas,
            'lecturas_fuera_spec': total_fuera_spec,
            'lecturas_alerta': total_alerta,
            'tasa_ok_pct': round((total_lecturas - total_fuera_spec - total_alerta) * 100 / total_lecturas, 1) if total_lecturas else None,
        },
    })


@bp.route('/api/calidad/agua/exportar-csv', methods=['GET'])
def calidad_agua_exportar_csv():
    """Exporta registros del sistema de agua en CSV (para INVIMA)."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    desde = (request.args.get('desde') or '').strip()
    hasta = (request.args.get('hasta') or '').strip()
    conn = get_db(); c = conn.cursor()
    where = []; params = []
    if desde: where.append('fecha >= ?'); params.append(desde)
    if hasta: where.append('fecha <= ?'); params.append(hasta)
    sql = ("SELECT fecha, hora, punto_muestreo, tipo_agua, ph, "
           "conductividad_us_cm, toc_ppb, microorganismos_ufc_ml, "
           "cloro_residual_ppm, temperatura_c, estado, observaciones, operador "
           "FROM calidad_sistema_agua")
    if where: sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY fecha DESC, hora DESC LIMIT 10000"
    rows = c.execute(sql, params).fetchall()
    import csv
    from io import StringIO
    buf = StringIO()
    w = csv.writer(buf)
    w.writerow(['Fecha','Hora','Punto','Tipo','pH','Conductividad uS/cm',
                 'TOC ppb','Micro UFC/mL','Cloro ppm','Temp C',
                 'Estado','Observaciones','Operador'])
    for r in rows:
        w.writerow([str(x) if x is not None else '' for x in r])
    csv_text = buf.getvalue()
    fn = f'sistema_agua_{datetime.now().strftime("%Y%m%d_%H%M")}.csv'
    return Response(
        csv_text,
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename={fn}'},
    )


@bp.route('/api/calidad/oos', methods=['GET'])
def calidad_oos_list():
    """Lista de OOS (Out Of Spec). Filtros: estado, desde, hasta, lote."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    estado = (request.args.get('estado') or '').strip()
    conn = get_db(); c = conn.cursor()
    sql = "SELECT * FROM calidad_oos"
    params = []
    if estado: sql += " WHERE estado=?"; params.append(estado)
    sql += " ORDER BY estado='cerrado' ASC, fecha_deteccion DESC LIMIT 200"
    rows = c.execute(sql, params).fetchall()
    cols = [d[0] for d in c.description]
    return jsonify({'oos': [dict(zip(cols, r)) for r in rows]})


@bp.route('/api/calidad/oos/<int:oos_id>', methods=['PATCH'])
def calidad_oos_update(oos_id):
    """Actualiza OOS · flujo investigación → aprobación → cierre."""
    err, code = _require_calidad()
    if err:
        return err, code
    user = session.get('compras_user', '')
    d = request.get_json(silent=True) or {}
    conn = get_db(); c = conn.cursor()
    fila = c.execute(
        "SELECT causa_raiz, disposicion FROM calidad_oos WHERE id=?", (oos_id,)
    ).fetchone()
    if not fila:
        return jsonify({'error': 'OOS no encontrado'}), 404
    sets = []; params = []
    for col in ('accion_inmediata','causa_raiz','disposicion','aprobado_por',
                'fecha_objetivo_cierre','capa_id','aprobado_gerencia'):
        if col in d:
            sets.append(f'{col}=?'); params.append(d[col])
    if 'estado' in d:
        nuevo = d['estado']
        if nuevo not in ('abierto','en_investigacion','en_aprobacion','cerrado','rechazado'):
            return jsonify({'error': 'estado invalido'}), 400
        if nuevo == 'cerrado':
            # Cerrar un OOS libera un lote fuera de especificación de la
            # cuarentena · exigir causa raíz documentada y disposición.
            causa = str(d.get('causa_raiz') if 'causa_raiz' in d else (fila[0] or '') or '')
            disp = str(d.get('disposicion') if 'disposicion' in d else (fila[1] or '') or '')
            if len(causa.strip()) < 20:
                return jsonify({'error': 'No se puede cerrar un OOS sin causa raíz documentada (mín. 20 caracteres)'}), 422
            if not disp.strip():
                return jsonify({'error': 'No se puede cerrar un OOS sin disposición del lote'}), 422
            # DOBLE APROBACIÓN (GMP · 14-jun): rechazo/destrucción de producto exige una 2ª
            # firma de GERENCIA, distinta del Jefe de Calidad que cierra.
            if disp.strip().lower() in ('rechazado', 'rechazo', 'destruido', 'destruccion', 'destrucción'):
                aprob_ger = str(d.get('aprobado_gerencia') or '').strip().lower()
                if not aprob_ger or aprob_ger not in set(ADMIN_USERS):
                    return jsonify({'error': 'Disposición de RECHAZO/DESTRUCCIÓN requiere aprobación de '
                                             'gerencia (campo aprobado_gerencia = usuario de gerencia).',
                                    'codigo': 'REQUIERE_APROBACION_GERENCIA'}), 422
                if aprob_ger == (user or '').lower():
                    return jsonify({'error': 'La aprobación de gerencia debe ser una persona distinta '
                                             'de quien cierra el OOS (segregación de funciones).',
                                    'codigo': 'DOBLE_APROBACION_MISMO_USUARIO'}), 422
            # E-FIRMA Part 11 (§11.200 · 14-jun): cerrar un OOS exige firma electrónica
            # (meaning='aprueba' sobre calidad_oos). El frontend firma con /api/sign.
            if not _validar_e_sign_cal(c, d.get('signature_id'), record_table='calidad_oos',
                                       record_id=oos_id, meaning='aprueba', signer=user):
                return jsonify({
                    'error': "Cerrar un OOS requiere firma electrónica (Part 11). Firmá con "
                             "meaning='aprueba', record_table='calidad_oos', record_id=%d y reenviá "
                             "signature_id." % oos_id,
                    'codigo': 'FIRMA_REQUERIDA'}), 400
        sets.append('estado=?'); params.append(nuevo)
        if nuevo == 'cerrado':
            sets.append('fecha_cierre=?'); params.append(datetime.now().date().isoformat())
            sets.append('aprobado_por=?'); params.append(user)
            sets.append('fecha_aprobacion=?'); params.append(datetime.now().isoformat())
            # AUTO-CAPA (14-jun): todo OOS cerrado debe tener una acción correctiva. Se crea
            # la cadena OOS → NC → CAPA (capa_acciones · correctiva, plazo 30d). NOTA: NO se
            # escribe calidad_oos.capa_id (esa columna tiene FK a capa_desviaciones, el CAPA de
            # Aseguramiento, no a capa_acciones); el vínculo OOS↔NC es por el código del OOS en
            # la descripción de la NC. Idempotente: no duplica si ya existe una NC de ese OOS.
            try:
                _oi = c.execute("SELECT COALESCE(codigo,''), COALESCE(lote,''), "
                                "COALESCE(producto,''), COALESCE(parametro,'') "
                                "FROM calidad_oos WHERE id=?", (oos_id,)).fetchone()
                _marca = f"OOS {_oi[0]}:"
                _ya = c.execute("SELECT id FROM no_conformidades WHERE descripcion LIKE ?",
                                (_marca + '%',)).fetchone()
                if not _ya:
                    _desc = (f"{_marca} {_oi[3]} fuera de spec en {_oi[2]} lote {_oi[1]}")[:300]
                    c.execute("INSERT INTO no_conformidades (fecha,tipo,descripcion,area,responsable,"
                              "lote,impacto,estado,creado_por) VALUES "
                              "(date('now','-5 hours'),'Producto',?,'Calidad',?,?,'Alto','Abierta',?)",
                              (_desc, user, _oi[1], user))
                    _nc_id = c.lastrowid
                    c.execute("INSERT INTO capa_acciones (nc_id,tipo,descripcion,responsable,"
                              "fecha_compromiso,estado) VALUES (?,'correctiva',?,?,"
                              "date('now','-5 hours','+30 days'),'Pendiente')",
                              (_nc_id, (f"Acción correctiva por OOS {_oi[0]} ({disp})")[:300], user))
            except Exception as _ec:
                log.warning('auto-CAPA OOS %s fallo: %s', oos_id, _ec)
    if not sets:
        return jsonify({'error': 'nada que actualizar'}), 400
    params.append(oos_id)
    c.execute(f"UPDATE calidad_oos SET {', '.join(sets)} WHERE id=?", params)
    try:
        audit_log(c, usuario=user, accion='ACTUALIZAR_OOS', tabla='calidad_oos',
                  registro_id=oos_id, despues=d)
    except Exception as e:
        log.warning('audit_log ACTUALIZAR_OOS fallo: %s', e)
    conn.commit()
    return jsonify({'ok': True})


# ════════════════════════════════════════════════════════════════════════
# EQUIPOS Y CALIBRACIONES · COC-PRO-006 + COC-PRO-012 + PRD-PRO-004
# Sebastián 1-may-2026: integra los 104 equipos del seed con tracking de
# vigencia, hoja de vida y cronograma 2026 importado del xlsx oficial.
# ════════════════════════════════════════════════════════════════════════

def _autorizados_equipos():
    """Quién puede registrar eventos de equipos (calibración/mantenimiento).

    La BITÁCORA DE CALIBRACIÓN es de ASEGURAMIENTO (Miguel · decisión de Sebastián 21-jul),
    pero los endpoints vivían gateados solo a CALIDAD_USERS → Miguel VEÍA su bitácora y no
    podía registrar nada (403 silencioso · es exactamente el patrón M32: al dividir un cargo,
    el dueño del módulo pierde la escritura porque el gate de la página y el de la mutación
    son DOS controles distintos).
    """
    from config import ADMIN_USERS as _ADM
    try:
        from config import CALIDAD_USERS as _CAL
    except Exception:
        _CAL = set()
    try:
        from config import ASEGURAMIENTO_USERS as _ASEG
    except Exception:
        _ASEG = set()
    return set(_CAL) | set(_ASEG) | set(_ADM)


@bp.route('/api/calidad/equipos/dashboard', methods=['GET'])
def calidad_equipos_dashboard():
    """KPIs + lista de equipos vencidos/próximos. Pantalla principal del módulo."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()

    # Total equipos activos
    total_activos = c.execute(
        "SELECT COUNT(DISTINCT codigo) FROM equipos_planta WHERE COALESCE(activo,1)=1"
    ).fetchone()[0] or 0

    # Por equipo, calcular última fecha_proxima del último evento de calibración o verificación
    # Si no hay evento, queda como "sin tracking"
    rows = c.execute("""
        SELECT ep.codigo, ep.nombre, ep.area_codigo, ep.ubicacion_raw, ep.tipo,
               (SELECT MAX(fecha_proxima) FROM equipos_eventos
                WHERE equipo_codigo = ep.codigo
                  AND tipo_evento IN ('calibracion','verificacion_semestral')
                  AND fecha_proxima IS NOT NULL) as fecha_proxima_cal,
               (SELECT MAX(fecha) FROM equipos_eventos
                WHERE equipo_codigo = ep.codigo
                  AND tipo_evento = 'calibracion') as ultima_cal
        FROM equipos_planta ep
        WHERE COALESCE(ep.activo,1) = 1
        -- PG exige toda columna no-agregada del SELECT en el GROUP BY (SQLite no).
        -- ep.codigo es único, así que agrupar por todas las ep.* preserva el
        -- resultado. Sin esto: 500 'must appear in the GROUP BY clause'. Suite PG.
        GROUP BY ep.codigo, ep.nombre, ep.area_codigo, ep.ubicacion_raw, ep.tipo
        ORDER BY ep.codigo
    """).fetchall()

    vencidos = []
    proximos_30d = []
    sin_tracking = []
    vigentes = 0
    for cod, nom, area, ubic, tipo, prox, ult in rows:
        if not prox:
            sin_tracking.append({
                'codigo': cod, 'nombre': nom, 'area': area,
                'ubicacion': ubic, 'tipo': tipo,
                'ultima_calibracion': ult,
            })
            continue
        # Calcular días
        try:
            from datetime import date as _date
            f_prox = _date.fromisoformat(prox)
            dias = (f_prox - _date.today()).days
        except Exception:
            sin_tracking.append({'codigo': cod, 'nombre': nom, 'tipo': tipo})
            continue
        item = {
            'codigo': cod, 'nombre': nom, 'area': area,
            'ubicacion': ubic, 'tipo': tipo,
            'fecha_proxima': prox, 'ultima_calibracion': ult,
            'dias_para_vencer': dias,
        }
        if dias < 0:
            item['dias_vencido'] = abs(dias)
            vencidos.append(item)
        elif dias <= 30:
            proximos_30d.append(item)
        else:
            vigentes += 1
    vencidos.sort(key=lambda x: x['dias_vencido'], reverse=True)
    proximos_30d.sort(key=lambda x: x['dias_para_vencer'])

    return jsonify({
        'kpis': {
            'total_activos': total_activos,
            'vigentes': vigentes,
            'proximos_30d': len(proximos_30d),
            'vencidos': len(vencidos),
            'sin_tracking': len(sin_tracking),
        },
        'vencidos': vencidos[:50],
        'proximos_30d': proximos_30d[:50],
        'sin_tracking': sin_tracking[:50],
    })


@bp.route('/api/calidad/equipos/cronograma', methods=['GET'])
def calidad_equipos_cronograma():
    """Cronograma del mes (default mes actual). Querystring: ?mes=N&anio=YYYY."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    from datetime import date as _date
    hoy = _date.today()
    try:
        mes = int(request.args.get('mes', hoy.month))
        anio = int(request.args.get('anio', hoy.year))
    except (ValueError, TypeError):
        return jsonify({'error': 'mes y anio deben ser enteros'}), 400
    if not (1 <= mes <= 12):
        return jsonify({'error': 'mes fuera de rango'}), 400
    conn = get_db(); c = conn.cursor()
    rows = c.execute("""
        SELECT cron.id, cron.equipo_codigo, ep.nombre, ep.area_codigo,
               cron.tipo_actividad, cron.estado, cron.fecha_completado,
               cron.completado_por, cron.observaciones
        FROM equipos_cronograma cron
        LEFT JOIN equipos_planta ep ON ep.codigo = cron.equipo_codigo
        WHERE cron.anio = ? AND cron.mes = ?
        ORDER BY cron.tipo_actividad, cron.equipo_codigo
        LIMIT 500
    """, (anio, mes)).fetchall()
    items = [{
        'id': r[0], 'equipo_codigo': r[1], 'equipo_nombre': r[2] or '',
        'area': r[3] or '', 'tipo_actividad': r[4],
        'estado': r[5], 'fecha_completado': r[6],
        'completado_por': r[7], 'observaciones': r[8],
    } for r in rows]
    completados = sum(1 for i in items if i['estado'] == 'completado')
    return jsonify({
        'anio': anio, 'mes': mes,
        'items': items,
        'kpis': {
            'total': len(items),
            'completados': completados,
            'pendientes': len(items) - completados,
            'cumplimiento_pct': round(completados * 100 / len(items), 1) if items else None,
        },
    })


@bp.route('/api/calidad/equipos/<path:codigo>/hoja-vida', methods=['GET'])
def calidad_equipos_hoja_vida(codigo):
    """Histórico completo del equipo: datos + todos los eventos."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    eq = c.execute("""
        SELECT codigo, nombre, area_codigo, ubicacion_raw, tipo,
               capacidad_raw, capacidad_litros, capacidad_kg,
               estado_operacional, activo, notas, creado_en
        FROM equipos_planta
        WHERE codigo = ?
        LIMIT 1
    """, (codigo,)).fetchone()
    if not eq:
        return jsonify({'error': f'equipo {codigo} no encontrado'}), 404
    eventos = c.execute("""
        SELECT id, tipo_evento, fecha, fecha_proxima, estado, responsable,
               empresa_externa, certificado_url, resultado, observaciones, creado_por
        FROM equipos_eventos
        WHERE equipo_codigo = ?
        ORDER BY fecha DESC, id DESC
        LIMIT 200
    """, (codigo,)).fetchall()
    cronograma = c.execute("""
        SELECT anio, mes, tipo_actividad, estado, fecha_completado
        FROM equipos_cronograma
        WHERE equipo_codigo = ?
        ORDER BY anio DESC, mes DESC
        LIMIT 50
    """, (codigo,)).fetchall()
    return jsonify({
        'equipo': {
            'codigo': eq[0], 'nombre': eq[1], 'area': eq[2],
            'ubicacion': eq[3], 'tipo': eq[4],
            'capacidad_raw': eq[5], 'capacidad_litros': eq[6], 'capacidad_kg': eq[7],
            'estado_operacional': eq[8], 'activo': bool(eq[9]),
            'notas': eq[10], 'creado_en': eq[11],
        },
        'eventos': [{
            'id': r[0], 'tipo_evento': r[1], 'fecha': r[2],
            'fecha_proxima': r[3], 'estado': r[4], 'responsable': r[5],
            'empresa_externa': r[6], 'certificado_url': r[7],
            'resultado': r[8], 'observaciones': r[9], 'creado_por': r[10],
        } for r in eventos],
        'cronograma': [{
            'anio': r[0], 'mes': r[1], 'tipo_actividad': r[2],
            'estado': r[3], 'fecha_completado': r[4],
        } for r in cronograma],
    })


@bp.route('/api/calidad/equipos/<path:codigo>/registrar-evento', methods=['POST'])
def calidad_equipos_registrar_evento(codigo):
    """Registra un evento (calibración, verificación, mantenimiento, etc.) en hoja de vida.

    Body: {
      tipo_evento: str (req · uno de los CHECK constraint),
      fecha_proxima: str opt (cuándo vence)
      estado: str opt (default 'completado'),
      responsable, empresa_externa, certificado_url, resultado, observaciones,
      numero_oc: str opt (OC con que se compró la calibración · trazabilidad compra→registro)
    }

    RBAC: CALIDAD + ASEGURAMIENTO (Miguel · dueño de la bitácora de calibración) + ADMIN.
    """
    user = session.get('compras_user', '')
    autorizados = _autorizados_equipos()
    if user not in autorizados:
        return jsonify({'error': 'Solo Calidad, Aseguramiento o Admin pueden registrar eventos de equipos'}), 403

    conn = get_db(); c = conn.cursor()
    eq = c.execute("SELECT 1 FROM equipos_planta WHERE codigo=?", (codigo,)).fetchone()
    if not eq:
        return jsonify({'error': f'equipo {codigo} no encontrado'}), 404

    d = request.get_json(silent=True) or {}
    tipo = (d.get('tipo_evento') or '').strip()
    valid_tipos = ('calibracion','verificacion_diaria','verificacion_semestral',
                    'mantenimiento_preventivo','mantenimiento_correctivo',
                    'baja','reparacion','validacion','reactivacion')
    if tipo not in valid_tipos:
        return jsonify({'error': f'tipo_evento inválido. Uno de: {", ".join(valid_tipos)}'}), 400

    fecha = (d.get('fecha') or datetime.now().date().isoformat()).strip()
    fecha_proxima = (d.get('fecha_proxima') or '').strip() or None
    estado = (d.get('estado') or 'completado').strip()
    if estado not in ('completado','programado','en_curso','cancelado'):
        return jsonify({'error': 'estado inválido'}), 400

    _oc = (str(d.get('numero_oc') or '')).strip()[:40]
    try:
        c.execute("""
            INSERT INTO equipos_eventos
              (equipo_codigo, tipo_evento, fecha, fecha_proxima, estado,
               responsable, empresa_externa, certificado_url, resultado,
               observaciones, creado_por, numero_oc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (codigo, tipo, fecha, fecha_proxima, estado,
              d.get('responsable'), d.get('empresa_externa'),
              d.get('certificado_url'), d.get('resultado'),
              d.get('observaciones'), user, _oc))
        evento_id = c.lastrowid
        # Si es completado y reactiva, actualizar estado_operacional
        if tipo in ('reactivacion','calibracion','verificacion_semestral') and estado == 'completado':
            c.execute("UPDATE equipos_planta SET estado_operacional='operativo' "
                      "WHERE codigo=? AND estado_operacional!='baja'", (codigo,))
        elif tipo == 'baja':
            c.execute("UPDATE equipos_planta SET estado_operacional='baja' "
                      "WHERE codigo=?", (codigo,))
        elif tipo in ('mantenimiento_correctivo','reparacion'):
            c.execute("UPDATE equipos_planta SET estado_operacional='mantenimiento' "
                      "WHERE codigo=? AND estado_operacional!='baja'", (codigo,))
        # Audit log
        try:
            import json as _json
            c.execute("""
                INSERT INTO audit_log (usuario, accion, registro_id, despues)
                VALUES (?, 'EQUIPOS_REGISTRAR_EVENTO', ?, ?)
            """, (user, codigo, _json.dumps({
                'tipo': tipo, 'fecha': fecha, 'fecha_proxima': fecha_proxima,
                'estado': estado, 'evento_id': evento_id,
            })))
        except Exception as _e:
            logging.getLogger('calidad').debug('audit equipos registrar fallo: %s', _e)
        conn.commit()
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        return jsonify({'error': str(e)[:200]}), 500
    return jsonify({'ok': True, 'evento_id': evento_id})


@bp.route('/api/calidad/equipos/por-calificar', methods=['GET'])
def calidad_equipos_por_calificar():
    """Equipos recibidos que todavía NO se pueden usar (la cola de Aseguramiento).

    Es el equivalente de la bandeja de cuarentena de materia prima: llegó, está registrado,
    y hasta que alguien lo califique no entra a producción.
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db(); c = conn.cursor()
    items = []
    try:
        for r in c.execute(
            "SELECT codigo, nombre, COALESCE(marca,''), COALESCE(modelo,''), COALESCE(serial,''), "
            "COALESCE(area_codigo,''), COALESCE(ubicacion_raw,''), COALESCE(fecha_ingreso,''), "
            "COALESCE(recibido_por,''), COALESCE(empresa,''), COALESCE(proveedor,'') "
            "FROM equipos_planta WHERE COALESCE(estado_calificacion,'NO_APLICA')='PENDIENTE' "
            "AND COALESCE(activo,1)=1 ORDER BY fecha_ingreso, codigo").fetchall():
            items.append({'codigo': r[0], 'nombre': r[1], 'marca': r[2], 'modelo': r[3],
                          'serial': r[4], 'area': r[5], 'ubicacion': r[6], 'fecha_ingreso': r[7],
                          'recibido_por': r[8], 'empresa': r[9], 'proveedor': r[10]})
    except Exception as e:
        log.warning('cola de equipos por calificar: %s', e)
        return jsonify({'ok': True, 'items': [], 'error_lectura': True})
    return jsonify({'ok': True, 'items': items,
                    'puede_calificar': session.get('compras_user', '') in _autorizados_equipos()})


@bp.route('/api/calidad/equipos/<path:codigo>/calificar', methods=['POST'])
def calidad_equipos_calificar(codigo):
    """Aseguramiento CALIFICA el equipo (IQ/OQ/PQ) y recién ahí queda operativo.

    Body: {resultado: 'CALIFICADO'|'RECHAZADO', iq, oq, pq (bool), notas}

    El que RECIBE no califica (el mismo principio que ya rige los controles en proceso): la
    recepción es de Compras/Luz y esto es de Aseguramiento. Va con CAS sobre el estado: dos
    calificaciones concurrentes no pueden dejar el equipo en dos estados distintos (M27), y un
    equipo ya calificado no se vuelve a calificar por un doble click.
    """
    user = session.get('compras_user', '')
    if user not in _autorizados_equipos():
        return jsonify({'error': 'Solo Aseguramiento, Calidad o Admin califican un equipo'}), 403
    d = request.get_json(silent=True) or {}
    resultado = str(d.get('resultado') or '').strip().upper()
    if resultado not in ('CALIFICADO', 'RECHAZADO'):
        return jsonify({'error': "resultado debe ser 'CALIFICADO' o 'RECHAZADO'"}), 400
    notas = str(d.get('notas') or '').strip()
    if resultado == 'RECHAZADO' and not notas:
        # Rechazar un equipo sin decir por qué deja un registro que no explica nada.
        return jsonify({'error': 'Para rechazar un equipo hace falta el motivo'}), 400
    cod = str(codigo or '').strip()
    fases = [k.upper() for k in ('iq', 'oq', 'pq') if d.get(k)]
    conn = get_db(); c = conn.cursor()
    fila = c.execute(
        "SELECT nombre, COALESCE(estado_calificacion,'NO_APLICA') FROM equipos_planta "
        "WHERE UPPER(TRIM(codigo))=UPPER(TRIM(?)) AND COALESCE(activo,1)=1", (cod,)).fetchone()
    if not fila:
        return jsonify({'error': 'Equipo %s no encontrado' % cod}), 404
    ahora = (datetime.utcnow()).replace(microsecond=0).isoformat()
    hoy_co = (datetime.utcnow() - timedelta(hours=5)).date().isoformat()
    nuevo_op = 'operativo' if resultado == 'CALIFICADO' else 'baja'
    c.execute(
        "UPDATE equipos_planta SET estado_calificacion=?, calificado_por=?, calificado_at_utc=?, "
        "calificacion_notas=?, estado_operacional=?, actualizado_en=? "
        "WHERE UPPER(TRIM(codigo))=UPPER(TRIM(?)) AND COALESCE(estado_calificacion,'')='PENDIENTE'",
        (resultado, user, ahora, notas, nuevo_op, ahora, cod))
    if c.rowcount == 0:
        conn.rollback()
        return jsonify({'error': 'Ese equipo ya no está pendiente de calificación (está en %s)'
                                 % fila[1], 'estado_actual': fila[1]}), 409
    # La calificación es un EVENTO de la hoja de vida: si no queda ahí, mañana nadie puede
    # demostrar que se calificó antes de usarlo. 'validacion' es el valor que admite el CHECK
    # de la tabla — inventar uno nuevo haría fallar el INSERT en silencio (M62).
    try:
        c.execute(
            "INSERT INTO equipos_eventos (equipo_codigo, tipo_evento, fecha, estado, responsable, "
            "resultado, observaciones, creado_por) VALUES (?,'validacion',?,'completado',?,?,?,?)",
            (cod, hoy_co, user, resultado,
             ('Calificación de recepción' + (' · fases ' + '/'.join(fases) if fases else '')
              + (' · ' + notas if notas else '')), user))
    except Exception as e:
        conn.rollback()
        return jsonify({'error': 'No se pudo registrar la calificación en la hoja de vida',
                        'detalle': str(e)}), 500
    audit_log(c, usuario=user, accion='CALIFICAR_EQUIPO', tabla='equipos_planta', registro_id=cod,
              antes={'estado_calificacion': 'PENDIENTE'},
              despues={'estado_calificacion': resultado, 'fases': fases, 'notas': notas},
              detalle='%s %s · %s' % (resultado, cod, fila[0]))
    conn.commit()
    return jsonify({'ok': True, 'codigo': cod, 'estado_calificacion': resultado,
                    'estado_operacional': nuevo_op,
                    'mensaje': ('Equipo calificado: ya puede usarse en producción.'
                                if resultado == 'CALIFICADO' else
                                'Equipo RECHAZADO: queda registrado y fuera de operación.')})


@bp.route('/api/calidad/equipos/cronograma/<int:cron_id>/completar', methods=['POST'])
def calidad_equipos_cronograma_completar(cron_id):
    """Marca un item del cronograma como completado y crea evento asociado.

    Body opcional: {observaciones, responsable}
    """
    user = session.get('compras_user', '')
    if user not in _autorizados_equipos():
        return jsonify({'error': 'Solo Calidad, Aseguramiento o Admin'}), 403

    conn = get_db(); c = conn.cursor()
    row = c.execute("""
        SELECT equipo_codigo, anio, mes, tipo_actividad, estado
        FROM equipos_cronograma WHERE id=?
    """, (cron_id,)).fetchone()
    if not row:
        return jsonify({'error': 'cronograma no encontrado'}), 404
    if row[4] == 'completado':
        return jsonify({'error': 'ya está completado'}), 409

    d = request.get_json(silent=True) or {}
    obs = (d.get('observaciones') or '').strip()
    resp = (d.get('responsable') or user).strip()
    fecha_hoy = datetime.now().date().isoformat()

    try:
        # Mapear tipo_actividad → tipo_evento
        tipo_map = {
            'preventivo': 'mantenimiento_preventivo',
            'correctivo': 'mantenimiento_correctivo',
            'verificacion': 'verificacion_semestral',
            'calibracion': 'calibracion',
        }
        tipo_evento = tipo_map.get(row[3], 'mantenimiento_preventivo')
        c.execute("""
            INSERT INTO equipos_eventos
              (equipo_codigo, tipo_evento, fecha, estado, responsable,
               observaciones, creado_por)
            VALUES (?, ?, ?, 'completado', ?, ?, ?)
        """, (row[0], tipo_evento, fecha_hoy, resp, obs or None, user))
        evento_id = c.lastrowid
        c.execute("""
            UPDATE equipos_cronograma
            SET estado='completado', fecha_completado=?, completado_por=?,
                evento_id=?, observaciones=?
            WHERE id=?
        """, (fecha_hoy, user, evento_id, obs or None, cron_id))
        conn.commit()
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        return jsonify({'error': str(e)[:200]}), 500
    return jsonify({'ok': True, 'evento_id': evento_id})


@bp.route('/api/calidad/equipos/importar-cronograma', methods=['POST'])
def calidad_equipos_importar_cronograma():
    """Importa items del cronograma anual desde JSON. RBAC admin.

    Body: {
      anio: int (default 2026),
      items: [{equipo_codigo, mes, tipo_actividad}, ...]
    }
    Idempotente · UNIQUE(equipo_codigo, anio, mes, tipo_actividad).
    """
    user = session.get('compras_user', '')
    from config import ADMIN_USERS
    if user not in ADMIN_USERS:
        return jsonify({'error': 'Solo Admin'}), 403
    d = request.get_json(silent=True) or {}
    try:
        anio = int(d.get('anio', 2026))
    except (ValueError, TypeError):
        return jsonify({'error': 'anio inválido'}), 400
    items = d.get('items') or []
    if not isinstance(items, list) or not items:
        return jsonify({'error': 'items debe ser lista no vacía'}), 400

    conn = get_db(); c = conn.cursor()
    insertados = 0
    saltados = 0
    errores = []
    for it in items[:5000]:  # límite anti-bomb
        try:
            eq = (it.get('equipo_codigo') or '').strip()
            mes = int(it.get('mes', 0))
            tipo = (it.get('tipo_actividad') or '').strip()
            if not eq or not (1 <= mes <= 12):
                errores.append(f'invalid: {it}')
                continue
            if tipo not in ('preventivo','correctivo','verificacion','calibracion'):
                errores.append(f'tipo invalido: {it}')
                continue
            r = c.execute("""
                INSERT OR IGNORE INTO equipos_cronograma
                  (equipo_codigo, anio, mes, tipo_actividad)
                VALUES (?, ?, ?, ?)
            """, (eq, anio, mes, tipo))
            if r.rowcount > 0:
                insertados += 1
            else:
                saltados += 1
        except Exception as e:
            errores.append(f'{it}: {e}')
    conn.commit()
    return jsonify({
        'ok': True, 'anio': anio,
        'insertados': insertados,
        'saltados_ya_existian': saltados,
        'errores': errores[:20],
    })


# ─────────────────────────────────────────────────────────────────────────────
# MAESTRO DE LOTES · lote x presentacion, teoricas vs liberadas (15-ago-2026)
#
# Es la unica vista funcional que MyBatch tiene (Aseguramiento > "Maestro de lotes")
# y EOS no armaba: el dato estaba entero -unidades por presentacion en
# `ebr_envasado_unidades`, granel envasable en el propio legajo, liberacion en el
# kardex de PT- pero repartido en tres tablas y solo visible ABRIENDO legajo por
# legajo. Un auditor pregunta "de este lote, cuantas salieron y cuantas se liberaron"
# y esa pregunta no tenia pantalla (M121 en su forma suave: la capacidad existe, pero
# esta a un click que nadie da).
#
# Y aca EOS puede ser mejor que MyBatch sin inventar nada: el mismo cuadro trae de
# donde SALIO el lote (el calendario), para QUIEN es (los clientes B2B con su envase y
# su foto) y con que se envaso. MyBatch muestra lote x presentacion y nada mas.
#
# Rendimiento: TODO se arma con consultas agregadas sobre la ventana. Ni una consulta
# por lote -llamar al repartidor de envases por fila es exactamente lo que satura los
# tres workers (M43/M63)- y el TOTAL se cuenta APARTE del recorte, porque un total
# calculado sobre una ventana recortada es un total falso (M155/M207).
# ─────────────────────────────────────────────────────────────────────────────

# Cuantos lotes fisicos entrega una pagina. El total NO sale de aca.
_MAESTRO_LOTES_PAGINA = 60
# Techo de legajos que se leen para armar esa pagina (hasta 3 fases por lote + margen).
_MAESTRO_LOTES_LEGAJOS = 600

_MAESTRO_FASE_ORDEN = {'fabricacion': 1, 'envasado': 2, 'acondicionamiento': 3}


def _maestro_lote_fisico(lote_codigo, lote):
    """El lote FISICO. La columna `lote` lleva sufijo de fase (-OF/-OA) porque es UNIQUE
    (M10); lo que un auditor busca es el lote de verdad, que vive en `lote_codigo`."""
    return (str(lote_codigo or '').strip() or str(lote or '').strip())


def _maestro_teoricas_por_presentacion(ml_envasable, presentaciones):
    """Cuantas unidades DEBIERON salir de este granel, presentacion por presentacion.

    No se llama al repartidor de envases (pesado · una consulta por lote tumba la
    pantalla · M43): se reparte el granel envasable en la MISMA proporcion de VOLUMEN
    que lo realmente envasado. Eso contesta la pregunta de la conciliacion -"con este
    granel y esta mezcla, cuantas debieron salir"- y es dimensionalmente correcto: una
    unidad de 30 ml se lleva el triple de granel que una de 10 (M72).

    Si no hay granel envasable medido, devuelve None y la pantalla lo DICE: una teorica
    inventada se lee igual que una medida, y sobre esta se firma (M124).
    """
    try:
        ml_tot = float(ml_envasable or 0)
    except Exception:
        ml_tot = 0.0
    if ml_tot <= 0:
        return None
    volumen_ocupado = 0.0
    for p in presentaciones:
        volumen_ocupado += float(p.get('volumen_ml') or 0) * float(p.get('registradas') or 0)
    if volumen_ocupado <= 0:
        return None
    out = {}
    for p in presentaciones:
        ml_u = float(p.get('volumen_ml') or 0)
        if ml_u <= 0:
            continue
        porcion = (ml_u * float(p.get('registradas') or 0)) / volumen_ocupado
        out[p.get('codigo') or ''] = int(round((ml_tot * porcion) / ml_u))
    return out


@bp.route('/api/calidad/maestro-lotes', methods=['GET'])
def calidad_maestro_lotes():
    """Maestro de lotes · un renglon por lote FISICO con su cuadro de unidades.

    Lectura pura. La ve quien trabaja con lotes (Calidad, Aseguramiento, Planta y
    admin): es la pantalla que se le muestra a una auditoria, y cerrarla a un solo rol
    la vuelve inalcanzable justo para quien la necesita (M32/M121).
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    conn = get_db()
    q = (request.args.get('q') or '').strip()
    desde = (request.args.get('desde') or '').strip()
    hasta = (request.args.get('hasta') or '').strip()

    where, params = [], []
    if q:
        like = '%' + q.upper() + '%'
        where.append("(UPPER(COALESCE(e.lote_codigo,'')) LIKE ? OR UPPER(e.lote) LIKE ? "
                     "OR UPPER(COALESCE(m.producto_nombre,'')) LIKE ? "
                     "OR UPPER(COALESCE(e.numero_op,'')) LIKE ?)")
        params += [like, like, like, like]
    if desde:
        where.append("substr(COALESCE(e.iniciado_at_utc,''),1,10) >= ?")
        params.append(desde)
    if hasta:
        where.append("substr(COALESCE(e.iniciado_at_utc,''),1,10) <= ?")
        params.append(hasta)
    w = (' WHERE ' + ' AND '.join(where)) if where else ''

    # 1) TOTAL de lotes fisicos que cumplen el filtro. Se cuenta sobre TODO, nunca sobre
    #    la ventana: un total calculado sobre un recorte es un total falso (M207).
    total_lotes = 0
    try:
        total_lotes = int(conn.execute(
            "SELECT COUNT(*) FROM (SELECT DISTINCT COALESCE(NULLIF(TRIM(e.lote_codigo),''), e.lote) AS lf "
            "FROM ebr_ejecuciones e LEFT JOIN mbr_templates m ON m.id=e.mbr_template_id" + w + ") t",
            params).fetchone()[0] or 0)
    except Exception as _e:
        log.warning('maestro-lotes total fallo: %s', _e)

    # 2) Los legajos de la ventana (fabricacion + envasado + acondicionamiento).
    filas = conn.execute(
        "SELECT e.id, e.lote, COALESCE(e.lote_codigo,''), COALESCE(e.fase,'fabricacion'), "
        "       e.estado, COALESCE(m.producto_nombre,''), COALESCE(e.numero_op,''), "
        "       COALESCE(e.iniciado_at_utc,''), COALESCE(e.liberado_at_utc,''), "
        "       COALESCE(e.liberado_por,''), e.cantidad_objetivo_g, e.cantidad_real_g, "
        "       e.yield_pct, e.ml_envasable, e.densidad_g_ml, e.unidades_teoricas, "
        "       e.unidades_buenas_real, e.produccion_id, COALESCE(pp.cantidad_kg,0), "
        "       COALESCE(pp.fecha_programada,''), COALESCE(e.yield_justificacion,'') "
        "  FROM ebr_ejecuciones e "
        "  LEFT JOIN mbr_templates m ON m.id = e.mbr_template_id "
        "  LEFT JOIN produccion_programada pp ON pp.id = e.produccion_id" + w +
        " ORDER BY e.iniciado_at_utc DESC, e.id DESC LIMIT %d" % _MAESTRO_LOTES_LEGAJOS,
        params).fetchall()

    lotes, orden = {}, []
    for r in filas:
        lf = _maestro_lote_fisico(r[2], r[1])
        if not lf:
            continue
        if lf not in lotes:
            lotes[lf] = {
                'lote': lf, 'producto': r[5] or '', 'numero_op': r[6] or '',
                'fecha': (r[19] or (r[7] or '')[:10]), 'kg': float(r[18] or 0),
                'produccion_id': (int(r[17]) if r[17] else None),
                'fases': {}, 'granel_g': None, 'ml_envasable': None,
                'densidad_g_ml': None, 'yield_pct': None, 'yield_justificacion': '',
                'unidades': {'teoricas': None, 'registradas': 0, 'liberadas': None,
                             'diferencia': None, 'yield_uds_pct': None},
                'presentaciones': [], 'clientes': [], 'unidades_clientes': 0,
                'materiales': [], 'material_sin_entregar': 0.0,
                'material_cliente': [], 'material_cliente_sin_definir': 0,
                'material_sin_explicar': 0.0,
                'pt_vigente': 0.0, 'pt_cuarentena': 0.0,
            }
            orden.append(lf)
        L = lotes[lf]
        fase = r[3] or 'fabricacion'
        L['fases'][fase] = {
            'ebr_id': r[0], 'estado': r[4] or '', 'llave': r[1],
            'liberado_at': r[8] or '', 'liberado_por': r[9] or '',
            'objetivo_g': float(r[10] or 0),
            'real_g': (float(r[11]) if r[11] is not None else None),
            'yield_pct': (float(r[12]) if r[12] is not None else None),
        }
        if not L['producto'] and r[5]:
            L['producto'] = r[5]
        if not L['produccion_id'] and r[17]:
            L['produccion_id'] = int(r[17])
        if fase == 'fabricacion':
            L['granel_g'] = (float(r[11]) if r[11] is not None else None)
            L['yield_pct'] = (float(r[12]) if r[12] is not None else None)
            L['yield_justificacion'] = r[20] or ''
        if r[13] is not None and float(r[13] or 0) > 0:
            L['ml_envasable'] = float(r[13])
        if r[14] is not None and float(r[14] or 0) > 0:
            L['densidad_g_ml'] = float(r[14])
        if r[15] is not None and float(r[15] or 0) > 0:
            L['unidades']['teoricas'] = int(float(r[15]))

    # El recorte se mide DESPUES de recortar, o el numero declarado no es el que falta.
    orden = orden[:_MAESTRO_LOTES_PAGINA]
    vista = {k: lotes[k] for k in orden}
    recortado = max(0, total_lotes - len(orden))
    ids = [f['ebr_id'] for L in vista.values() for f in L['fases'].values()]

    # 3) Unidades por presentacion · UNA consulta para toda la pagina.
    if ids:
        ph = ','.join('?' for _ in ids)
        por_ebr = {}
        try:
            for r in conn.execute(
                "SELECT ebr_id, COALESCE(presentacion_codigo,''), COALESCE(etiqueta,''), "
                "       COALESCE(volumen_ml,0), COALESCE(unidades,0) "
                "  FROM ebr_envasado_unidades WHERE ebr_id IN (%s)" % ph, ids).fetchall():
                if float(r[4] or 0) <= 0:
                    continue
                por_ebr.setdefault(r[0], []).append({
                    'codigo': r[1] or '', 'etiqueta': r[2] or '',
                    'volumen_ml': float(r[3] or 0), 'registradas': int(float(r[4] or 0)),
                    'teoricas': None, 'diferencia': None,
                })
        except Exception as _e:
            log.warning('maestro-lotes presentaciones fallo: %s', _e)
        for L in vista.values():
            acc = {}
            for f in L['fases'].values():
                for p in por_ebr.get(f['ebr_id'], []):
                    k = (p['codigo'], p['volumen_ml'])
                    if k in acc:
                        acc[k]['registradas'] += p['registradas']
                    else:
                        acc[k] = dict(p)
            L['presentaciones'] = sorted(acc.values(),
                                         key=lambda x: (x['volumen_ml'], x['etiqueta']))
            L['unidades']['registradas'] = sum(p['registradas'] for p in L['presentaciones'])
            teo = _maestro_teoricas_por_presentacion(L['ml_envasable'], L['presentaciones'])
            if teo is not None:
                for p in L['presentaciones']:
                    p['teoricas'] = teo.get(p['codigo'])
                    if p['teoricas'] is not None:
                        p['diferencia'] = p['registradas'] - p['teoricas']
                if L['unidades']['teoricas'] is None:
                    L['unidades']['teoricas'] = sum(teo.values())

    # 3b) El MATERIAL DE ENVASE del lote · la punta que conecta con Compras: lo que se
    #     pidió, lo que Compras entregó, lo que la línea usó, lo que volvió a bodega y lo
    #     que se rompió. La DIFERENCIA se deriva con el helper canónico de `brd` -no se
    #     recalcula acá: dos copias de la misma resta divergen el día que alguien corrige
    #     una (M3/M99)- y lo que Compras no entregó completo queda señalado aparte.
    if ids:
        try:
            try:
                from blueprints.brd import _conc_diferencia
            except Exception:
                from api.blueprints.brd import _conc_diferencia
            ph = ','.join('?' for _ in ids)
            por_ebr_mat = {}
            for r in conn.execute(
                "SELECT ebr_id, COALESCE(material_codigo,''), material_nombre, "
                "       COALESCE(cant_requerida,0), COALESCE(cant_recibida,0), "
                "       COALESCE(cant_utilizada,0), COALESCE(cant_devuelta,0), "
                "       COALESCE(cant_averiada,0) "
                "  FROM ebr_conciliacion_material WHERE ebr_id IN (%s)" % ph, ids).fetchall():
                por_ebr_mat.setdefault(r[0], []).append({
                    'codigo': r[1] or '', 'nombre': r[2] or '',
                    'requerida': float(r[3] or 0), 'recibida': float(r[4] or 0),
                    'utilizada': float(r[5] or 0), 'devuelta': float(r[6] or 0),
                    'averiada': float(r[7] or 0),
                    'diferencia': _conc_diferencia(r[3], r[4], r[6], r[5], r[7]),
                    # Lo que se pidió y no llegó: es lo que hay que reclamarle a Compras.
                    'sin_entregar': max(0.0, float(r[3] or 0) - float(r[4] or 0)),
                })
            for L in vista.values():
                mats = []
                for f in L['fases'].values():
                    mats.extend(por_ebr_mat.get(f['ebr_id'], []))
                L['materiales'] = mats
                L['material_sin_entregar'] = sum(m['sin_entregar'] for m in mats)
                L['material_sin_explicar'] = sum(
                    m['diferencia'] for m in mats if m['diferencia'] > 0)
        except Exception as _e:
            log.warning('maestro-lotes material de envase fallo: %s', _e)

    # 4) Producto terminado en el kardex · liberado (VIGENTE) vs esperando a Calidad.
    if orden:
        ph = ','.join('?' for _ in orden)
        try:
            for r in conn.execute(
                "SELECT lote, UPPER(COALESCE(estado_lote,'')), SUM(COALESCE(cantidad,0)) "
                "  FROM movimientos WHERE lote IN (%s) AND tipo='Entrada' "
                "   AND COALESCE(material_id,'') LIKE 'PT\\_%%' ESCAPE '\\' "
                " GROUP BY lote, UPPER(COALESCE(estado_lote,''))" % ph, orden).fetchall():
                L = vista.get(r[0])
                if not L:
                    continue
                if r[1] == 'VIGENTE':
                    L['pt_vigente'] += float(r[2] or 0)
                elif r[1] in ('CUARENTENA', 'CUARENTENA_EXTENDIDA'):
                    L['pt_cuarentena'] += float(r[2] or 0)
        except Exception as _e:
            log.warning('maestro-lotes PT fallo: %s', _e)

    # 5) Para QUE CLIENTE es este lote (lo que MyBatch no tiene) · consultas agregadas.
    pid_de_lote = {lf: L['produccion_id'] for lf, L in vista.items() if L.get('produccion_id')}
    pids = sorted(set(pid_de_lote.values()))
    if pids:
        ph = ','.join('?' for _ in pids)
        por_pid, codigos = {}, set()
        try:
            for r in conn.execute(
                "SELECT lote_produccion_id, COALESCE(cliente_nombre,''), "
                "       SUM(COALESCE(unidades_aporte,0)), MAX(COALESCE(envase_codigo,'')), "
                "       MAX(COALESCE(ml_unidad,0)) FROM pedidos_b2b_lote "
                " WHERE lote_produccion_id IN (%s) "
                " GROUP BY lote_produccion_id, cliente_nombre" % ph, pids).fetchall():
                if float(r[2] or 0) <= 0:
                    continue
                cod = (r[3] or '').strip()
                if cod:
                    codigos.add(cod.upper())
                por_pid.setdefault(int(r[0]), []).append({
                    'cliente': r[1] or '(sin nombre)', 'unidades': int(float(r[2] or 0)),
                    'volumen_ml': float(r[4] or 0), 'envase_codigo': cod,
                    'envase_foto': '', 'envase_desc': '',
                })
            if codigos:
                fp = ','.join('?' for _ in codigos)
                fotos = {}
                for r in conn.execute(
                    "SELECT UPPER(TRIM(codigo)), COALESCE(imagen_url,''), COALESCE(descripcion,'') "
                    "  FROM maestro_mee WHERE UPPER(TRIM(codigo)) IN (%s)" % fp,
                        sorted(codigos)).fetchall():
                    fotos[r[0]] = (r[1], r[2])
                for filas_c in por_pid.values():
                    for cli in filas_c:
                        f = fotos.get((cli['envase_codigo'] or '').upper())
                        if f:
                            cli['envase_foto'], cli['envase_desc'] = f[0], f[1]
            for lf, L in vista.items():
                L['clientes'] = por_pid.get(pid_de_lote.get(lf) or 0, [])
                L['unidades_clientes'] = sum(c['unidades'] for c in L['clientes'])
        except Exception as _e:
            log.warning('maestro-lotes clientes fallo: %s', _e)

        # El material de MARCA DEL CLIENTE (etiqueta y caja): Catalina define al aceptar
        # SI el pedido lo lleva, y sin el código no se puede comprar ni alistar. Se
        # resuelve con el helper canónico -no se recalcula acá (M3)- y lo que falta
        # definir se DECLARA, que es justo lo que antes quedaba en silencio.
        try:
            try:
                from blueprints.programacion import _material_cliente_lotes
            except Exception:
                from api.blueprints.programacion import _material_cliente_lotes
            # UNA consulta para toda la página, no una por lote: pedirlo fila por fila es
            # exactamente lo que satura los tres workers (M43/M63).
            _mat_cli = _material_cliente_lotes(conn, list(pid_de_lote.values()))
            for lf, L in vista.items():
                mats = _mat_cli.get(pid_de_lote.get(lf) or 0, [])
                L['material_cliente'] = mats
                L['material_cliente_sin_definir'] = len(
                    [m for m in mats if m.get('falta_definir')])
        except Exception as _e:
            log.warning('maestro-lotes material de cliente fallo: %s', _e)

    # 6) El estado del LOTE es el de su fase mas avanzada.
    salida = []
    for lf in orden:
        L = vista[lf]
        fase_final, orden_max = '', 0
        for fase, f in L['fases'].items():
            o = _MAESTRO_FASE_ORDEN.get(fase, 1)
            if o >= orden_max:
                orden_max, fase_final = o, fase
        est = (L['fases'].get(fase_final, {}).get('estado') or '').lower()
        L['fase_final'] = fase_final
        L['estado'] = est
        if est == 'liberado':
            L['estado_liberacion'] = 'liberado'
            L['unidades']['liberadas'] = L['unidades']['registradas'] or None
        elif est == 'rechazado':
            L['estado_liberacion'] = 'rechazado'
            L['unidades']['liberadas'] = 0
        elif est in ('completado', 'en_revision_qc'):
            L['estado_liberacion'] = 'espera_calidad'
        else:
            L['estado_liberacion'] = 'en_proceso'
        t, g = L['unidades']['teoricas'], L['unidades']['registradas']
        if t:
            L['unidades']['diferencia'] = g - t
            L['unidades']['yield_uds_pct'] = round(100.0 * g / t, 1)
        salida.append(L)

    return jsonify({
        'ok': True,
        'lotes': salida,
        'total': total_lotes,
        'mostrados': len(salida),
        'recortado': recortado,
        # Se DECLARA el recorte y de donde sale la teorica: un numero cuyo origen no se
        # puede leer no se puede auditar, y este cuadro se firma (M124/M155).
        'teorica_origen': 'granel envasable repartido por el volumen de la mezcla real',
        'pagina': _MAESTRO_LOTES_PAGINA,
    })


@bp.route('/calidad/maestro-lotes', methods=['GET'])
def calidad_maestro_lotes_page():
    """Pagina · Maestro de lotes (el cuadro de unidades que MyBatch tiene en Aseguramiento)."""
    if 'compras_user' not in session:
        return redirect('/login?next=/calidad/maestro-lotes')
    return Response(_MAESTRO_LOTES_HTML, mimetype='text/html')


_MAESTRO_LOTES_HTML = r"""<!DOCTYPE html><html lang="es" translate="no"><head><meta charset="UTF-8">
<meta name="google" content="notranslate">
<meta name="viewport" content="width=device-width,initial-scale=1.0,viewport-fit=cover"><title>Maestro de lotes &middot; Calidad &middot; EOS</title>
<link rel="stylesheet" href="/static/cortex.css?v=eos15">
<script>(function(){try{var t=localStorage.getItem("cx-theme");if(t==="dark")document.documentElement.setAttribute("data-theme","dark");}catch(e){}})();</script>
<style>
body{background:var(--cx-bg);color:var(--cx-text);margin:0;font-family:'Inter',system-ui,-apple-system,sans-serif;}
*{box-sizing:border-box}
.ml-wrap{width:96vw;max-width:1720px;margin:0 auto;padding:22px 18px 72px;}
.ml-intro{color:var(--cx-text-mute);font-size:13.5px;line-height:1.55;max-width:900px;margin:0 0 16px;}
.card{background:var(--cx-card);border:1px solid var(--cx-hairline);border-radius:18px;box-shadow:0 1px 3px rgba(15,23,42,.04),0 10px 30px rgba(15,23,42,.05);padding:20px 22px;margin-bottom:16px;}
.searchbar{display:flex;gap:10px;flex-wrap:wrap;align-items:center;}
#q{flex:1;min-width:260px;font-size:15px;}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(168px,1fr));gap:12px;margin-bottom:16px;}
.kpi{background:var(--cx-card);border:1px solid var(--cx-hairline);border-radius:14px;padding:14px 16px;position:relative;overflow:hidden;}
.kpi:before{content:'';position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--cx-hairline);}
.kpi.ok:before{background:var(--cx-success-text, #15803d);} .kpi.esp:before{background:var(--cx-warn-text, #b45309);}
.kpi.dif:before{background:var(--cx-danger-text, #b91c1c);} .kpi.pri:before{background:var(--cx-primary-text);}
.kpi .n{font-size:26px;font-weight:800;letter-spacing:-.02em;color:var(--cx-text);line-height:1.1;}
.kpi .t{font-size:11.5px;color:var(--cx-text-mute);margin-top:3px;font-weight:600;}
.lote{background:var(--cx-card);border:1px solid var(--cx-hairline);border-radius:16px;box-shadow:0 2px 14px rgba(15,23,42,.05);padding:0;margin-bottom:14px;overflow:hidden;}
.lote-head{display:flex;gap:16px;align-items:center;padding:16px 20px;cursor:pointer;flex-wrap:wrap;}
.lote-head:hover{background:var(--cx-bg-alt);}
.lote-id{min-width:210px;}
.lote-id .l{font-size:15.5px;font-weight:800;color:var(--cx-text);font-family:ui-monospace,monospace;letter-spacing:-.01em;}
.lote-id .p{font-size:12.5px;color:var(--cx-text-mute);margin-top:2px;}
.chip{display:inline-flex;align-items:center;gap:5px;font-size:11px;font-weight:800;padding:4px 11px;border-radius:999px;border:1px solid var(--cx-hairline);color:var(--cx-text-soft);white-space:nowrap;}
.chip.liberado{color:var(--cx-success-text, #15803d);border-color:rgba(21,128,61,.35);background:rgba(21,128,61,.09);}
.chip.espera_calidad{color:var(--cx-warn-text, #b45309);border-color:rgba(180,83,9,.35);background:rgba(180,83,9,.10);}
.chip.rechazado{color:var(--cx-danger-text, #b91c1c);border-color:rgba(185,28,28,.35);background:rgba(185,28,28,.09);}
.chip.en_proceso{color:var(--cx-info-text, #2563eb);border-color:rgba(37,99,235,.3);background:rgba(37,99,235,.08);}
.uds{display:flex;gap:20px;flex-wrap:wrap;margin-left:auto;align-items:center;}
.ud{text-align:right;min-width:74px;}
.ud .n{font-size:17px;font-weight:800;color:var(--cx-text);line-height:1.15;}
.ud .t{font-size:10.5px;color:var(--cx-text-mute);font-weight:600;text-transform:uppercase;letter-spacing:.03em;}
.ud .n.pos{color:var(--cx-success-text, #15803d);} .ud .n.neg{color:var(--cx-danger-text, #b91c1c);}
.ud .n.nd{color:var(--cx-text-faint);font-size:13px;font-weight:700;}
.det{display:none;border-top:1px solid var(--cx-hairline);padding:18px 20px;background:var(--cx-bg-alt);}
.det.open{display:block;}
.det h3{font-size:12.5px;font-weight:800;text-transform:uppercase;letter-spacing:.04em;color:var(--cx-text-mute);margin:0 0 10px;}
.det-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:22px;}
.det-full{grid-column:1/-1;min-width:0;}
.det-grid > div{min-width:0;}
.tscroll{overflow-x:auto;max-width:100%;}
table.pres{width:100%;border-collapse:collapse;font-size:13px;}
table.pres th{text-align:left;font-size:10.5px;text-transform:uppercase;letter-spacing:.04em;color:var(--cx-text-mute);border-bottom:1px solid var(--cx-hairline);padding:6px 8px;font-weight:700;}
table.pres td{padding:7px 8px;border-bottom:1px solid var(--cx-hairline);color:var(--cx-text);}
table.pres td.num{text-align:right;font-variant-numeric:tabular-nums;font-weight:700;}
table.pres td.neg{color:var(--cx-danger-text, #b91c1c);} table.pres td.pos{color:var(--cx-success-text, #15803d);}
.cli{display:flex;gap:10px;align-items:center;padding:8px 0;border-bottom:1px solid var(--cx-hairline);}
.cli img{width:38px;height:38px;object-fit:contain;border-radius:8px;background:var(--cx-card);border:1px solid var(--cx-hairline);}
.cli .nm{font-size:13px;font-weight:700;color:var(--cx-text);} .cli .sb{font-size:11.5px;color:var(--cx-text-mute);}
.cli .u{margin-left:auto;font-size:15px;font-weight:800;color:var(--cx-text);font-variant-numeric:tabular-nums;}
.origen{font-size:12.5px;color:var(--cx-text-mute);line-height:1.7;}
.origen b{color:var(--cx-text);font-weight:700;}
.acc{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px;}
.empty{color:var(--cx-text-mute);font-size:14px;padding:42px 0;text-align:center;}
.nota{font-size:11.5px;color:var(--cx-text-faint);margin-top:10px;line-height:1.5;}
.fases{display:flex;gap:6px;flex-wrap:wrap;}
</style></head><body>
<header class="cx-mod-header cx-fade-in">
  <span class="cx-mod-header__logo" style="display:inline-flex;align-items:center;color:var(--cx-primary-text);"><svg viewBox="0 0 24 24" width="34" height="34" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7h18M3 12h18M3 17h18"/><path d="M8 4v16"/></svg></span>
  <div>
    <div class="cx-mod-header__title">Maestro de lotes</div>
    <div class="cx-mod-header__sub"><strong>Calidad</strong> &middot; Espagiria &middot; unidades por lote y presentaci&oacute;n</div>
  </div>
  <div class="cx-mod-header__nav">
    <a href="/calidad/expediente" class="cx-btn cx-btn-ghost cx-btn-sm" title="Todos los documentos de un lote">&#128194; Expediente</a>
    <a href="/calidad/genealogia" class="cx-btn cx-btn-ghost cx-btn-sm" title="De qu&eacute; est&aacute; hecho un lote">&#129514; Genealog&iacute;a</a>
    <a href="/calidad" class="cx-btn cx-btn-ghost cx-btn-sm">&larr; Calidad</a>
    <a href="/modulos" class="cx-btn cx-btn-ghost cx-btn-sm">M&oacute;dulos</a>
    <button class="cx-theme-toggle" onclick="cxToggleTheme()" title="Modo claro/oscuro"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4 12H2M22 12h-2M5.6 5.6 4.2 4.2M19.8 19.8l-1.4-1.4M5.6 18.4l-1.4 1.4M19.8 4.2l-1.4 1.4"/></svg></button>
  </div>
</header>
<script>function cxToggleTheme(){var h=document.documentElement;var n=h.getAttribute('data-theme')==='dark'?'light':'dark';if(n==='dark')h.setAttribute('data-theme','dark');else h.removeAttribute('data-theme');try{localStorage.setItem('cx-theme',n);}catch(e){}}</script>
<div class="ml-wrap">
<div class="card">
<div class="ml-intro">Cada lote con su cuadro de unidades: cu&aacute;ntas <b>deb&iacute;an</b> salir de ese granel, cu&aacute;ntas se <b>envasaron</b> de verdad, la <b>diferencia</b> y si Calidad ya lo <b>liber&oacute;</b>. Abr&iacute; un lote y ves el desglose por presentaci&oacute;n, para qu&eacute; cliente es y de d&oacute;nde sali&oacute;.</div>
<div class="searchbar">
<input id="q" class="cx-input" placeholder="Lote, producto u orden&hellip;" autocomplete="off">
<input id="desde" type="date" class="cx-input" style="max-width:170px" title="Desde">
<input id="hasta" type="date" class="cx-input" style="max-width:170px" title="Hasta">
<select id="festado" class="cx-input" style="max-width:210px" title="Filtra los lotes mostrados">
  <option value="">Todos los estados</option>
  <option value="espera_calidad">Esperando a Calidad</option>
  <option value="liberado">Liberados</option>
  <option value="en_proceso">En proceso</option>
  <option value="rechazado">Rechazados</option>
</select>
<button class="cx-btn cx-btn-grad" onclick="mlCargar()">Buscar</button>
<span id="msg" style="font-size:12.5px;font-weight:700"></span>
</div>
</div>
<div id="kpis" class="kpis"></div>
<div id="res"></div>
<div id="nota" class="nota"></div>
</div>
<script>
var ML_DATA = [];
function esc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function num(n){if(n==null)return '';return Number(n).toLocaleString('es-CO');}
function mlCargar(){
  var q=document.getElementById('q').value.trim();
  var d=document.getElementById('desde').value, h=document.getElementById('hasta').value;
  document.getElementById('msg').textContent='Cargando...';
  var u='/api/calidad/maestro-lotes?q='+encodeURIComponent(q)+'&desde='+encodeURIComponent(d)+'&hasta='+encodeURIComponent(h);
  fetch(u,{credentials:'same-origin'}).then(function(r){return r.json();}).then(function(j){
    if(!j || !j.ok){document.getElementById('msg').textContent='No se pudo cargar';return;}
    ML_DATA=j.lotes||[];
    document.getElementById('msg').textContent='';
    var nota='Mostrando '+j.mostrados+' de '+j.total+' lotes con legajo.';
    if(j.recortado>0) nota+=' Quedan '+j.recortado+' fuera de esta página: acotá con el buscador o el rango de fechas.';
    nota+=' La columna Debían sale del '+j.teorica_origen+'; cuando el granel envasable no está medido, se muestra en blanco en vez de estimarlo.';
    document.getElementById('nota').textContent=nota;
    mlPintar();
  }).catch(function(e){document.getElementById('msg').textContent='Error: '+e;});
}
function mlPintar(){
  var f=document.getElementById('festado').value;
  var L=ML_DATA.filter(function(x){return !f || x.estado_liberacion===f;});
  var kpi=[{k:'pri',n:L.length,t:'lotes'},
           {k:'ok',n:L.filter(function(x){return x.estado_liberacion==='liberado';}).length,t:'liberados'},
           {k:'esp',n:L.filter(function(x){return x.estado_liberacion==='espera_calidad';}).length,t:'esperando a Calidad'},
           {k:'pri',n:num(L.reduce(function(a,x){return a+(x.unidades.registradas||0);},0)),t:'unidades envasadas'},
           {k:'dif',n:L.filter(function(x){return x.unidades.diferencia!=null && Math.abs(x.unidades.diferencia)>0;}).length,t:'con diferencia'}];
  document.getElementById('kpis').innerHTML=kpi.map(function(x){
    return '<div class="kpi '+x.k+'"><div class="n">'+x.n+'</div><div class="t">'+x.t+'</div></div>';}).join('');
  if(!L.length){document.getElementById('res').innerHTML='<div class="card"><div class="empty">No hay lotes que coincidan.</div></div>';return;}
  document.getElementById('res').innerHTML=L.map(mlFila).join('');
}
function mlEstadoTxt(e){
  return e==='liberado'?'Liberado':e==='espera_calidad'?'Espera a Calidad':e==='rechazado'?'Rechazado':'En proceso';}
function mlFila(x,i){
  var u=x.unidades||{};
  var dif=u.diferencia;
  var difCls=dif==null?'nd':(dif<0?'neg':(dif>0?'pos':''));
  var difTxt=dif==null?'sin medir':(dif>0?'+'+num(dif):num(dif));
  var h='<div class="lote"><div class="lote-head" onclick="mlToggle('+i+')">';
  h+='<div class="lote-id"><div class="l">'+esc(x.lote)+'</div><div class="p">'+esc(x.producto||'(sin producto)')+(x.fecha?' &middot; '+esc(x.fecha):'')+'</div></div>';
  h+='<span class="chip '+esc(x.estado_liberacion)+'">'+mlEstadoTxt(x.estado_liberacion)+'</span>';
  if(x.clientes && x.clientes.length) h+='<span class="chip" title="Este lote lleva unidades de cliente">&#128100; '+x.clientes.length+' cliente'+(x.clientes.length>1?'s':'')+'</span>';
  if(x.material_sin_entregar>0) h+='<span class="chip" style="color:var(--cx-warn-text, #b45309);border-color:rgba(180,83,9,.35);background:rgba(180,83,9,.10)" title="Material de envase que se pidio y no llego completo">&#128230; falta material</span>';
  h+='<div class="uds">';
  h+='<div class="ud"><div class="n'+(u.teoricas==null?' nd':'')+'">'+(u.teoricas==null?'sin medir':num(u.teoricas))+'</div><div class="t">Debían</div></div>';
  h+='<div class="ud"><div class="n">'+num(u.registradas||0)+'</div><div class="t">Envasadas</div></div>';
  h+='<div class="ud"><div class="n '+difCls+'">'+difTxt+'</div><div class="t">Diferencia</div></div>';
  h+='<div class="ud"><div class="n'+(u.liberadas==null?' nd':'')+'">'+(u.liberadas==null?'-':num(u.liberadas))+'</div><div class="t">Liberadas</div></div>';
  h+='</div></div>';
  h+='<div class="det" id="det-'+i+'">'+mlDetalle(x)+'</div></div>';
  return h;
}
function mlDetalle(x){
  var h='<div class="det-grid">';
  h+='<div><h3>Por presentación</h3>';
  if(x.presentaciones && x.presentaciones.length){
    h+='<div class="tscroll"><table class="pres"><thead><tr><th>Presentación</th><th style="text-align:right">ml</th><th style="text-align:right">Debían</th><th style="text-align:right">Envasadas</th><th style="text-align:right">Diferencia</th></tr></thead><tbody>';
    x.presentaciones.forEach(function(p){
      var d=p.diferencia;
      h+='<tr><td>'+esc(p.etiqueta||p.codigo||'-')+'</td><td class="num">'+num(p.volumen_ml)+'</td>'
        +'<td class="num">'+(p.teoricas==null?'-':num(p.teoricas))+'</td>'
        +'<td class="num">'+num(p.registradas)+'</td>'
        +'<td class="num '+(d==null?'':(d<0?'neg':(d>0?'pos':'')))+'">'+(d==null?'-':(d>0?'+'+num(d):num(d)))+'</td></tr>';
    });
    h+='</tbody></table></div>';
  } else { h+='<div class="origen">Todavía no se registraron unidades envasadas para este lote.</div>'; }
  h+='</div>';
  h+='<div><h3>Para quién es</h3>';
  if(x.clientes && x.clientes.length){
    x.clientes.forEach(function(c){
      h+='<div class="cli">';
      if(c.envase_foto) h+='<img src="'+esc(c.envase_foto)+'" alt="">';
      h+='<div><div class="nm">'+esc(c.cliente)+'</div><div class="sb">'+(c.volumen_ml?num(c.volumen_ml)+' ml':'')+(c.envase_desc?' &middot; '+esc(c.envase_desc):'')+'</div></div>';
      h+='<div class="u">'+num(c.unidades)+'</div></div>';
    });
    h+='<div class="origen" style="margin-top:8px">El resto del lote es de ÁNIMUS.</div>';
  }
  if(x.material_cliente && x.material_cliente.length){
    h+='<div class="origen" style="margin-top:10px"><b>Material de marca del cliente</b><br>';
    x.material_cliente.forEach(function(m){
      h+='&middot; '+esc(m.descripcion)+' &times; '+num(m.unidades)+' ';
      h+= m.falta_definir
        ? '<span style="color:var(--cx-danger-text, #b91c1c);font-weight:700">falta definir cu&aacute;l</span>'
        : '<span style="color:var(--cx-text-mute)">('+esc(m.codigo)+')</span>';
      h+='<br>';
    });
    if(x.material_cliente_sin_definir>0) h+='<span style="color:var(--cx-danger-text, #b91c1c)">Sin el c&oacute;digo no se puede comprar ni alistar: def&iacute;nilo al aceptar el pedido.</span>';
    h+='</div>';
  }
  if(!(x.clientes && x.clientes.length)){
    h+='<div class="origen">Lote completo de ÁNIMUS: ningún pedido de cliente se sumó acá.</div>';
  }
  h+='</div>';
  h+='<div class="det-full"><h3>Material de envase</h3>';
  if(x.materiales && x.materiales.length){
    h+='<div class="tscroll"><table class="pres"><thead><tr><th>Material</th><th style="text-align:right">Pedido</th><th style="text-align:right">Recibido</th><th style="text-align:right">Usado</th><th style="text-align:right">Devuelto</th><th style="text-align:right">Averiado</th><th style="text-align:right">Sin explicar</th></tr></thead><tbody>';
    x.materiales.forEach(function(m){
      h+='<tr><td>'+esc(m.nombre||m.codigo||'-')+'</td><td class="num">'+num(m.requerida)+'</td>'
        +'<td class="num'+(m.sin_entregar>0?' neg':'')+'">'+num(m.recibida)+'</td>'
        +'<td class="num">'+num(m.utilizada)+'</td><td class="num">'+num(m.devuelta)+'</td>'
        +'<td class="num">'+num(m.averiada)+'</td>'
        +'<td class="num'+(m.diferencia>0?' neg':'')+'">'+num(m.diferencia)+'</td></tr>';
    });
    h+='</tbody></table></div>';
    if(x.material_sin_entregar>0) h+='<div class="origen" style="margin-top:8px">Se pidieron <b>'+num(x.material_sin_entregar)+'</b> unidades que no llegaron a la línea: eso se le reclama a Compras. <a href="/compras" style="color:var(--cx-primary-text);font-weight:700;text-decoration:none">Ir a Compras &rarr;</a></div>';
    if(x.material_sin_explicar>0) h+='<div class="origen" style="margin-top:6px;color:var(--cx-danger-text, #b91c1c)"><b>'+num(x.material_sin_explicar)+'</b> unidades entraron a la línea y no se explican con lo usado, lo devuelto y lo averiado.</div>';
  } else { h+='<div class="origen">Todavía no se concilió material de envase para este lote.</div>'; }
  h+='</div>';
  h+='<div><h3>De dónde salió</h3><div class="origen">';
  if(x.kg) h+='Programado por <b>'+num(x.kg)+' kg</b> en el calendario.<br>';
  if(x.granel_g!=null) h+='Granel fabricado: <b>'+num(Math.round(x.granel_g))+' g</b>'+(x.yield_pct!=null?' (rendimiento '+x.yield_pct+'%)':'')+'.<br>';
  if(x.densidad_g_ml) h+='Densidad <b>'+x.densidad_g_ml+' g/mL</b> &rarr; envasable <b>'+num(Math.round(x.ml_envasable||0))+' mL</b>.<br>';
  if(x.yield_justificacion) h+='Justificación del rendimiento: <b>'+esc(x.yield_justificacion)+'</b><br>';
  if(x.pt_vigente) h+='Producto terminado liberado en bodega: <b>'+num(Math.round(x.pt_vigente))+'</b>.<br>';
  if(x.pt_cuarentena) h+='En cuarentena esperando a Calidad: <b>'+num(Math.round(x.pt_cuarentena))+'</b>.<br>';
  h+='<div class="fases" style="margin-top:8px">';
  ['fabricacion','envasado','acondicionamiento'].forEach(function(f){
    if(x.fases && x.fases[f]){var nf=mlFaseNom(f); h+='<span class="chip">'+nf.charAt(0).toUpperCase()+nf.slice(1)+': '+esc(x.fases[f].estado)+'</span>';}
  });
  h+='</div></div>';
  h+='<div class="acc">';
  ['fabricacion','envasado','acondicionamiento'].forEach(function(f){
    if(x.fases && x.fases[f]) h+='<a class="cx-btn cx-btn-ghost cx-btn-sm" target="_blank" href="/api/brd/ebr/'+x.fases[f].ebr_id+'/vista-completa">Legajo de '+mlFaseNom(f)+'</a>';
  });
  h+='<a class="cx-btn cx-btn-ghost cx-btn-sm" href="/calidad/expediente?lote='+encodeURIComponent(x.lote)+'">Expediente</a>';
  h+='<a class="cx-btn cx-btn-ghost cx-btn-sm" href="/calidad/genealogia?lote='+encodeURIComponent(x.lote)+'">Genealogía</a>';
  h+='</div></div></div>';
  return h;
}
function mlFaseNom(f){return f==='fabricacion'?'fabricación':(f==='envasado'?'envasado':'acondicionamiento');}
function mlToggle(i){var d=document.getElementById('det-'+i);if(d)d.classList.toggle('open');}
document.getElementById('q').addEventListener('keydown',function(e){if(e.key==='Enter')mlCargar();});
document.getElementById('festado').addEventListener('change',mlPintar);
mlCargar();
</script>
</body></html>"""
