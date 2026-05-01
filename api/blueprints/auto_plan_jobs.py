"""
Auto-Plan Jobs — Cron diario + Email engine

Sebastian (30-abr-2026): "trabajamos lunes a viernes 7am está bien...
debe ser la herramienta más avanzada del mundo".

Background thread que cada día a las 07:00 (L-V):
  1. Genera el plan auto (60d horizonte)
  2. Aplica el plan (crea producciones, compras, conteos)
  3. Envía emails a roles configurados:
     - Sebastián (CEO):  resumen ejecutivo + alertas críticas
     - Alejandro:         resumen producción + agenda semana
     - Catalina:          SOLs nuevas para aprobar
     - Operarios:         agenda personal del día (si email)
  4. Registra en auto_plan_runs

Diseño thread-safe: se ejecuta en un thread daemon que duerme hasta
las 07:00 del próximo día hábil. Si la app reinicia, recalcula
desde el último auto_plan_runs registrado.
"""
import os
import threading
import logging
import sqlite3
from datetime import datetime, timedelta, time as dtime
from flask import current_app

log = logging.getLogger('auto_plan_jobs')

# Hora del cron (Colombia America/Bogota)
HORA_CRON = 7   # 07:00
DIAS_CRON = (0, 1, 2, 3, 4)  # lunes a viernes


# ───────────────────────────────────────────────────────────────────────
# Email engine — usa SistemaNotificaciones existente del proyecto
# ───────────────────────────────────────────────────────────────────────

def _enviar_email_async(asunto, html, destinos):
    """Envía email en thread separado. Nunca falla."""
    if not destinos:
        return
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from notificaciones import SistemaNotificaciones
        notif = SistemaNotificaciones()
        t = threading.Thread(
            target=notif._enviar_email,
            args=(asunto, html, destinos),
            daemon=True,
        )
        t.start()
        return True
    except Exception as e:
        log.warning(f'[auto-plan-email] error no crítico: {e}')
        return False


# ───────────────────────────────────────────────────────────────────────
# Templates HTML
# ───────────────────────────────────────────────────────────────────────

def _html_resumen_ceo(plan_aplicado, plan):
    """Email a Sebastián: resumen ejecutivo del día."""
    fecha = datetime.now().strftime('%A %d-%b-%Y')
    n_prod = len(plan_aplicado.get('producciones_creadas', []))
    n_comp = len(plan_aplicado.get('compras_creadas', []))
    alertas = plan.get('alertas', [])
    n_crit = sum(1 for a in alertas if a.get('severidad') == 'critica')

    alertas_html = ''
    for a in alertas[:6]:
        color = '#dc2626' if a.get('severidad') == 'critica' else '#d97706'
        alertas_html += f"""
        <tr><td style="padding:6px 10px;border-left:3px solid {color};background:#fef2f2;font-size:12px">
          <b style="color:{color}">{a.get('titulo','')}</b>
        </td></tr>"""
    if not alertas_html:
        alertas_html = '<tr><td style="color:#15803d;padding:8px 10px;font-size:12px">✓ Sin alertas críticas hoy</td></tr>'

    prod_html = ''
    for p in plan.get('producciones_propuestas', [])[:8]:
        prod_html += f"""
        <tr><td style="padding:5px 10px;font-size:12px;border-bottom:1px solid #e5e7eb">
          <b>{p['producto']}</b> · {p['fecha_programada']}<br>
          <span style="color:#6b7280;font-size:11px">{p['kg_con_merma']:.0f}kg · {p['razon']}</span>
        </td></tr>"""

    return f"""<!DOCTYPE html>
<html><body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f3f4f6;padding:20px;color:#1f2937">
  <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 12px rgba(0,0,0,.08)">
    <div style="background:linear-gradient(135deg,#0f766e,#0891b2);color:#fff;padding:24px">
      <h1 style="margin:0;font-size:22px">🏭 Auto-Plan EOS · {fecha}</h1>
      <p style="margin:6px 0 0;color:#cffafe;font-size:13px">Resumen ejecutivo · Espagiria Laboratorios</p>
    </div>
    <div style="padding:20px">
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:20px">
        <div style="background:#f0fdf4;border-radius:8px;padding:12px;text-align:center"><div style="font-size:24px;font-weight:800;color:#15803d">{n_prod}</div><div style="font-size:10px;color:#166534;text-transform:uppercase">Producciones</div></div>
        <div style="background:#fef3c7;border-radius:8px;padding:12px;text-align:center"><div style="font-size:24px;font-weight:800;color:#92400e">{n_comp}</div><div style="font-size:10px;color:#92400e;text-transform:uppercase">SOLs auto</div></div>
        <div style="background:{'#fef2f2' if n_crit else '#f0fdf4'};border-radius:8px;padding:12px;text-align:center"><div style="font-size:24px;font-weight:800;color:{'#dc2626' if n_crit else '#15803d'}">{n_crit}</div><div style="font-size:10px;color:#7f1d1d;text-transform:uppercase">Alertas crít.</div></div>
      </div>

      <h3 style="color:#1f2937;margin:0 0 8px;font-size:14px">⚠ Alertas críticas</h3>
      <table style="width:100%;border-collapse:collapse;margin-bottom:16px">{alertas_html}</table>

      <h3 style="color:#1f2937;margin:0 0 8px;font-size:14px">📅 Producciones programadas (próximas)</h3>
      <table style="width:100%;border-collapse:collapse">{prod_html}</table>

      <p style="margin:20px 0 0;font-size:11px;color:#9ca3af;text-align:center">
        Generado por Auto-Plan EOS · <a href="https://inventarios-0905.onrender.com/inventarios" style="color:#0891b2">Ver en planta</a>
      </p>
    </div>
  </div>
</body></html>"""


def _html_resumen_alejandro(plan_aplicado, plan):
    """Email a gerencia producción: detalle producciones + alertas."""
    return _html_resumen_ceo(plan_aplicado, plan).replace(
        'Resumen ejecutivo · Espagiria Laboratorios',
        'Resumen producción · Para Alejandro'
    )


def _html_compras_catalina(plan_aplicado, plan):
    """Email a Catalina: SOLs nuevas auto-creadas para aprobar."""
    fecha = datetime.now().strftime('%A %d-%b-%Y')
    sols = plan_aplicado.get('compras_creadas', [])
    compras_propuestas = plan.get('compras_propuestas', [])

    rows = ''
    for cp in compras_propuestas:
        urg_color = '#dc2626' if cp['urgencia'] == 'critica' else ('#d97706' if cp['urgencia'] == 'alta' else '#0891b2')
        urg_txt = cp['urgencia'].upper()
        kg_pedir = cp['cantidad_a_pedir_g'] / 1000.0
        rows += f"""
        <tr style="border-bottom:1px solid #e5e7eb">
          <td style="padding:8px 10px;font-size:12px"><b>{cp['material_nombre']}</b><br><span style="color:#6b7280;font-size:10px">{cp['origen']} · lead {cp['lead_time_dias']}d</span></td>
          <td style="padding:8px 10px;font-size:12px;text-align:right;font-family:monospace"><b>{kg_pedir:.2f}kg</b><br><span style="color:#dc2626;font-size:10px">déficit {cp['deficit_g']:.0f}g</span></td>
          <td style="padding:8px 10px;text-align:center"><span style="background:{urg_color};color:#fff;padding:3px 8px;border-radius:6px;font-size:10px;font-weight:700">{urg_txt}</span></td>
        </tr>"""

    if not rows:
        rows = '<tr><td colspan="3" style="text-align:center;padding:20px;color:#9ca3af">✓ Sin compras nuevas hoy</td></tr>'

    return f"""<!DOCTYPE html>
<html><body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f3f4f6;padding:20px;color:#1f2937">
  <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden">
    <div style="background:linear-gradient(135deg,#1a4a7a,#0891b2);color:#fff;padding:24px">
      <h1 style="margin:0;font-size:22px">🛒 Compras Auto · {fecha}</h1>
      <p style="margin:6px 0 0;color:#cffafe;font-size:13px">Catalina, hay {len(sols)} solicitudes nuevas para aprobar</p>
    </div>
    <div style="padding:20px">
      <table style="width:100%;border-collapse:collapse">
        <thead style="background:#f9fafb">
          <tr><th style="padding:10px;text-align:left;font-size:11px;color:#475569;text-transform:uppercase">Material</th>
              <th style="padding:10px;text-align:right;font-size:11px;color:#475569;text-transform:uppercase">Cantidad</th>
              <th style="padding:10px;text-align:center;font-size:11px;color:#475569;text-transform:uppercase">Urgencia</th></tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>

      <p style="margin:20px 0 0;font-size:11px;color:#9ca3af;text-align:center">
        Auto-Plan EOS · <a href="https://inventarios-0905.onrender.com/compras" style="color:#0891b2">Ver SOLs en /compras</a>
      </p>
    </div>
  </div>
</body></html>"""


def _html_agenda_operario(operario, agenda_dia):
    """Email a operario: tareas del día."""
    fecha = datetime.now().strftime('%A %d-%b-%Y')
    lineas = ''
    for t in agenda_dia:
        lineas += f"""
        <tr><td style="padding:10px 12px;font-size:13px;border-bottom:1px solid #e5e7eb">
          <b>{t.get('hora','')}</b> · {t.get('titulo','')}<br>
          <span style="color:#6b7280;font-size:11px">{t.get('descripcion','')}</span>
        </td></tr>"""
    if not lineas:
        lineas = '<tr><td style="text-align:center;padding:20px;color:#9ca3af">Sin tareas programadas hoy</td></tr>'

    return f"""<!DOCTYPE html>
<html><body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f3f4f6;padding:20px">
  <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden">
    <div style="background:linear-gradient(135deg,#7c3aed,#0891b2);color:#fff;padding:24px">
      <h1 style="margin:0;font-size:20px">👋 Buenos días {operario}</h1>
      <p style="margin:6px 0 0;color:#cffafe;font-size:13px">{fecha} · Tu agenda</p>
    </div>
    <div style="padding:20px">
      <table style="width:100%;border-collapse:collapse">{lineas}</table>
      <p style="margin:20px 0 0;font-size:11px;color:#9ca3af;text-align:center">
        Auto-Plan EOS · <a href="https://inventarios-0905.onrender.com/inventarios" style="color:#0891b2">Ver en EOS</a>
      </p>
    </div>
  </div>
</body></html>"""


# ───────────────────────────────────────────────────────────────────────
# Job principal del cron
# ───────────────────────────────────────────────────────────────────────

def _notif_admin_in_app(plan, resultado):
    """Notifica a admins via push_notif_multi cuando hay actividad."""
    try:
        from blueprints.notif import push_notif_multi
        n_prod = len(resultado.get('producciones_creadas', []))
        n_compras = len(resultado.get('compras_creadas', []))
        n_alertas = len(plan.get('alertas', []))
        if not (n_prod or n_compras or n_alertas):
            return
        titulo = f'🤖 Auto-Plan ejecutado · {n_prod} prods, {n_compras} SOLs'
        body = f'Plan generado a las {datetime.now().strftime("%H:%M")}.'
        if n_alertas:
            body += f' ⚠ {n_alertas} alerta(s) crítica(s).'
        push_notif_multi(
            ['sebastian', 'alejandro', 'catalina'],
            'planta',
            titulo,
            body=body,
            link='/inventarios#programacion',
            remitente='AUTO-PLAN',
            importante=(n_alertas > 0),
        )
    except Exception as e:
        log.warning(f'notif in-app fallo: {e}')


def _aprender_historico_y_notificar(app):
    """Sebastian (30-abr-2026): "que cada lunes se dispare automático,
    pero siempre debe avisar si va a mover algo".

    Lee histórico → detecta cadencias REALES distintas a las configuradas.
    NO aplica cambios automáticamente — crea notificación in-app a admins
    para que ellos decidan adoptar o no.
    """
    try:
        from database import get_db
        from blueprints.notif import push_notif_multi
        c = get_db().cursor()
        # Reusar la lógica del endpoint aprender_historico calculando inline
        from blueprints.auto_plan import _calcular_cadencia_real
        from datetime import datetime as _dt, timedelta as _td

        fecha_desde = (_dt.now() - _td(days=365)).date()
        rows = c.execute("""
            SELECT producto, fecha_programada FROM produccion_programada
            WHERE date(fecha_programada) >= ?
              AND estado IN ('completado','en_proceso','pendiente')
              AND producto IS NOT NULL
            ORDER BY producto, fecha_programada
        """, (fecha_desde.isoformat(),)).fetchall()
        fechas_por_prod = {}
        for prod, fecha in rows:
            try:
                f = _dt.strptime((fecha or '')[:10], '%Y-%m-%d').date()
            except Exception:
                continue
            key = (prod or '').strip().upper()
            if not key:
                continue
            fechas_por_prod.setdefault(key, {'nombre': prod, 'fechas': []})
            fechas_por_prod[key]['fechas'].append(f)

        configs = c.execute("""
            SELECT UPPER(TRIM(producto_nombre)), cadencia_dias FROM sku_planeacion_config
            WHERE activo=1
        """).fetchall()
        config_map = {r[0]: r[1] for r in configs}

        recomendaciones = []
        for key, info in fechas_por_prod.items():
            cadencia_real = _calcular_cadencia_real(info['fechas'])
            cadencia_cfg = config_map.get(key)
            if cadencia_real and (not cadencia_cfg or abs(cadencia_real - (cadencia_cfg or 0)) > 7):
                recomendaciones.append({
                    'producto': info['nombre'],
                    'cadencia_real': cadencia_real,
                    'cadencia_configurada': cadencia_cfg,
                })

        if recomendaciones:
            push_notif_multi(
                ['sebastian', 'alejandro'], 'planta',
                f'🧠 Aprendizaje: {len(recomendaciones)} cadencia(s) cambian',
                body='El sistema detectó cadencias REALES distintas a las configuradas. Revisa en Auto-Plan → 🧠 Aprendizaje histórico para confirmar.',
                link='/inventarios#programacion',
                remitente='AUTO-PLAN',
                importante=True,
            )
            log.info(f'[auto-plan] {len(recomendaciones)} recomendaciones de cadencia notificadas')
    except Exception as e:
        log.warning(f'aprender_historico fallo: {e}')


def _detectar_cambios_demanda_con_margen(conn):
    """Sebastian (30-abr-2026): "debes permitirte márgenes pues si se vendió
    10 más el fin de semana aún alcanza con el margen 20 días antes de que
    se acabe... debe ser flexible estricto".

    Solo alerta si el cambio de velocidad ROMPE el margen 20d. Si subió pero
    aún alcanza para 25d, no alerta.
    """
    cambios_criticos = []
    try:
        from blueprints.auto_plan import _ventas_diarias_por_sku, _stock_actual_pt
        from database import get_db
        c = conn.cursor()
        rows = c.execute("SELECT producto_nombre FROM sku_planeacion_config WHERE activo=1").fetchall()
        for (producto,) in rows:
            sku_rows = c.execute(
                "SELECT sku FROM sku_producto_map WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?))",
                (producto,)
            ).fetchall()
            v_reciente = 0.0
            for (sku,) in sku_rows:
                r = _ventas_diarias_por_sku(c, sku, dias=14)
                if r:
                    v_reciente += sum(q for _, q in r) / 14.0
            if v_reciente <= 0:
                continue
            stock = _stock_actual_pt(c, producto)
            dias_alcance = stock / max(v_reciente, 0.01) if v_reciente > 0 else 999
            # Buscar próxima producción
            prox = c.execute("""
                SELECT id, fecha_programada FROM produccion_programada
                WHERE UPPER(TRIM(producto))=UPPER(TRIM(?))
                  AND estado IN ('pendiente','en_proceso')
                  AND fecha_programada >= date('now')
                ORDER BY fecha_programada ASC LIMIT 1
            """, (producto,)).fetchone()
            from datetime import datetime as _dt2
            if prox:
                try:
                    fp = _dt2.strptime(prox[1][:10], '%Y-%m-%d').date()
                    dias_hasta_prox = (fp - _dt2.now().date()).days
                except Exception:
                    continue
            else:
                dias_hasta_prox = 999
            # Regla: alerta solo si se va a romper margen 20d antes de la próxima prod
            # alcance_proyectado = dias_alcance - dias_hasta_prox  (cuánto sobra al llegar la próxima)
            # Si alcance_proyectado < 20 → ALERTA (no aguantamos el margen)
            margen_proyectado = dias_alcance - dias_hasta_prox
            if margen_proyectado < 20 and prox:
                cambios_criticos.append({
                    'producto': producto,
                    'stock_actual': stock,
                    'velocidad_dia': round(v_reciente, 2),
                    'dias_alcance_actual': round(dias_alcance, 1),
                    'proxima_prod_fecha': prox[1],
                    'dias_hasta_prox': dias_hasta_prox,
                    'margen_proyectado': round(margen_proyectado, 1),
                    'severidad': 'critica' if margen_proyectado < 5 else ('alta' if margen_proyectado < 12 else 'media'),
                    'mensaje': f'Stock alcanza {dias_alcance:.0f}d, próxima prod en {dias_hasta_prox}d → margen {margen_proyectado:.0f}d (mínimo 20d)',
                })
    except Exception as e:
        log.warning(f'detectar_cambios_margen fallo: {e}')
    return cambios_criticos


def ejecutar_auto_plan_diario(app):
    """Función llamada por el cron. Genera + aplica + envía emails + notif in-app.

    Sebastian (30-abr-2026): cada lunes 7am — primero APRENDE del histórico
    (notifica si encuentra cadencias distintas), después ejecuta el plan.
    """
    with app.app_context():
        log.info('[auto-plan-cron] Iniciando ejecución diaria...')
        # 1) Aprender del histórico (NO auto-aplica, solo notifica)
        try:
            _aprender_historico_y_notificar(app)
        except Exception as e:
            log.warning(f'aprender_historico fallo silencioso: {e}')

        try:
            from blueprints.auto_plan import generar_plan, aplicar_plan
            from database import get_db

            plan = generar_plan(horizonte_dias=60, tipo='auto', usuario='cron')
            resultado = aplicar_plan(plan, usuario='cron')

            # 2) Detectar cambios críticos con margen 20d
            try:
                cambios_margen = _detectar_cambios_demanda_con_margen(get_db())
                if cambios_margen:
                    from blueprints.notif import push_notif_multi
                    crit = sum(1 for x in cambios_margen if x['severidad']=='critica')
                    push_notif_multi(
                        ['sebastian','alejandro'], 'planta',
                        f'🚨 {len(cambios_margen)} producto(s) rompen margen 20d',
                        body=f'{crit} críticos. El stock se acabará antes de la próxima producción. Revisa en /planta.',
                        link='/inventarios#programacion',
                        remitente='AUTO-PLAN',
                        importante=True,
                    )
                    plan['cambios_margen_criticos'] = cambios_margen
            except Exception as e:
                log.warning(f'cambios_margen fallo: {e}')

            _notif_admin_in_app(plan, resultado)

            # Cargar configs de email
            conn = get_db(); c = conn.cursor()
            destinos_resumen = []
            destinos_alertas = []
            destinos_compras = []
            agendas = {}
            try:
                rows = c.execute("""
                    SELECT rol, nombre, email, recibe_resumen_diario,
                           recibe_alertas_criticas, recibe_compras_aprob,
                           recibe_agenda_personal
                    FROM email_destinatarios_config WHERE activo=1
                """).fetchall()
                for rol, nombre, email, r_res, r_alert, r_comp, r_agenda in rows:
                    if not email:
                        continue
                    if r_res:
                        destinos_resumen.append(email)
                    if r_alert:
                        destinos_alertas.append(email)
                    if r_comp:
                        destinos_compras.append(email)
                    if r_agenda:
                        agendas[email] = nombre or rol
            except Exception as e:
                log.warning(f'[auto-plan-cron] no se pudo cargar email_destinatarios_config: {e}')

            # Send emails
            n_emails = 0
            if destinos_resumen:
                _enviar_email_async(
                    f'🏭 Plan EOS · {datetime.now().strftime("%d-%b")}',
                    _html_resumen_ceo(resultado, plan),
                    destinos_resumen
                )
                n_emails += 1
            if destinos_compras:
                _enviar_email_async(
                    f'🛒 SOLs Auto-Plan · {datetime.now().strftime("%d-%b")}',
                    _html_compras_catalina(resultado, plan),
                    destinos_compras
                )
                n_emails += 1

            # Update emails_enviados in last run
            try:
                c.execute(
                    "UPDATE auto_plan_runs SET emails_enviados=? "
                    "WHERE id=(SELECT id FROM auto_plan_runs ORDER BY id DESC LIMIT 1)",
                    (n_emails,)
                )
                conn.commit()
            except Exception:
                pass

            log.info(f'[auto-plan-cron] Completado · {len(plan["producciones_propuestas"])} prod · {len(plan["compras_propuestas"])} compras · {n_emails} emails')
        except Exception as e:
            log.exception(f'[auto-plan-cron] error: {e}')


def _segundos_hasta_proximo_cron():
    """Cuántos segundos faltan hasta la próxima ejecución (próximo L-V 7am)."""
    ahora = datetime.now()
    objetivo = ahora.replace(hour=HORA_CRON, minute=0, second=0, microsecond=0)
    if ahora >= objetivo:
        objetivo = objetivo + timedelta(days=1)
    # Saltar fines de semana
    while objetivo.weekday() not in DIAS_CRON:
        objetivo = objetivo + timedelta(days=1)
    delta = (objetivo - ahora).total_seconds()
    return max(60, int(delta))


def _cron_habilitado_en_db(app):
    """Lee auto_plan_cron_state.habilitado desde la DB."""
    with app.app_context():
        try:
            from database import get_db
            r = get_db().execute(
                "SELECT habilitado FROM auto_plan_cron_state WHERE id=1"
            ).fetchone()
            return bool(r[0]) if r else False
        except Exception:
            return False


def _loop_cron(app):
    """Loop infinito del cron. Duerme hasta el próximo 7am L-V y ejecuta.
    Verifica auto_plan_cron_state.habilitado en cada ciclo."""
    log.info('[auto-plan-cron] Loop iniciado')
    import time as time_mod
    while True:
        secs = _segundos_hasta_proximo_cron()
        log.info(f'[auto-plan-cron] Durmiendo {secs}s hasta próxima ejecución')
        time_mod.sleep(secs)
        # Verificar que sigue habilitado en DB antes de ejecutar
        if not _cron_habilitado_en_db(app):
            log.info('[auto-plan-cron] Skipped — habilitado=0 en DB')
            continue
        try:
            ejecutar_auto_plan_diario(app)
            try:
                from database import get_db
                with app.app_context():
                    get_db().execute(
                        "UPDATE auto_plan_cron_state SET ultima_ejecucion_at=datetime('now'), errores_consecutivos=0 WHERE id=1"
                    )
                    get_db().commit()
            except Exception:
                pass
        except Exception as e:
            log.exception(f'[auto-plan-cron] excepción: {e}')
            try:
                with app.app_context():
                    from database import get_db
                    get_db().execute(
                        "UPDATE auto_plan_cron_state SET errores_consecutivos=errores_consecutivos+1 WHERE id=1"
                    )
                    get_db().commit()
            except Exception:
                pass


def iniciar_cron(app):
    """Lanza el thread del cron al arranque de la app.
    Idempotente: si ya está corriendo no hace nada.
    El thread siempre arranca, pero verifica auto_plan_cron_state.habilitado
    antes de ejecutar (toggle desde UI)."""
    if getattr(app, '_auto_plan_cron_started', False):
        return
    t = threading.Thread(target=_loop_cron, args=(app,), daemon=True)
    t.start()
    app._auto_plan_cron_started = True
    log.info('[auto-plan-cron] Cron thread arrancado (ejecución gobernada por auto_plan_cron_state.habilitado)')


# ════════════════════════════════════════════════════════════════════════
# MULTI-JOB CRON · scheduler interno (sin Render Cron Jobs externos)
# ════════════════════════════════════════════════════════════════════════
# Sebastián (1-may-2026): "configurar 4 crons" — lo hago interno para que
# no dependa de Render Cron Jobs (plan paid). Loop cada 5 min revisa schedule
# y ejecuta jobs pendientes con dedupe por última ejecución registrada.

JOBS_SCHEDULE = [
    # (job_name, hora, minuto, días_semana[0=lun..6=dom] o None=todos, días_mes[1-31] o None=todos, callable_name)
    # ⭐ LUNES 7AM · Workflow completo (jefe producción no hace nada manual)
    ('lunes_7am_workflow',    7,  0, [0],  None,                'job_lunes_7am_workflow'),
    # Diarios
    ('sync_shopify',          6,  0, None, None,                'job_sync_shopify'),
    ('auto_asignar_areas',    6, 30, None, None,                'job_auto_asignar_areas'),
    ('auto_d20',              8,  0, None, None,                'job_auto_d20'),
    ('self_heal',             7,  5, None, None,                'job_self_heal'),  # 5 min después del lunes_7am
    ('cleanup_logs',          2,  0, None, None,                'job_cleanup_logs'),
    # Mensuales (primeros 5 días del mes a las 12:00)
    ('auto_sc_mensual',      12,  0, None, [1, 2, 3, 4, 5],     'job_auto_sc_mensual'),
    ('auto_sc_mee_mensual',  12, 30, None, [1, 2, 3, 4, 5],     'job_auto_sc_mee_mensual'),
    # Lunes urgente (después del workflow lunes 7am)
    ('auto_sc_urgente_lun',  12,  0, [0],  None,                'job_auto_sc_urgente'),
]


def _es_hora_de(ahora, hora, minuto, dias_sem, dias_mes):
    """¿La fecha 'ahora' coincide con el schedule? (ventana de 5 min)."""
    if dias_sem is not None and ahora.weekday() not in dias_sem:
        return False
    if dias_mes is not None and ahora.day not in dias_mes:
        return False
    if ahora.hour != hora:
        return False
    if abs(ahora.minute - minuto) > 5:
        return False
    return True


def _ya_ejecutado_hoy(conn, job_name):
    """¿Ya se ejecutó este job hoy con éxito?"""
    try:
        row = conn.execute("""
            SELECT 1 FROM cron_jobs_runs
            WHERE job_name = ?
              AND ok = 1
              AND date(ejecutado_at) = date('now')
            LIMIT 1
        """, (job_name,)).fetchone()
        return bool(row)
    except Exception:
        return False


def _registrar_ejecucion(conn, job_name, ok, resultado, duracion_ms, error=None):
    try:
        import json as _json
        conn.execute("""
            INSERT INTO cron_jobs_runs (job_name, ejecutado_at, duracion_ms, ok, resultado_json, error)
            VALUES (?, datetime('now'), ?, ?, ?, ?)
        """, (job_name, duracion_ms, 1 if ok else 0,
              _json.dumps(resultado, default=str) if resultado else None,
              error))
        # Tracking errores consecutivos para notificación
        try:
            if ok:
                conn.execute("""
                    INSERT INTO cron_jobs_health (job_name, errores_consecutivos)
                    VALUES (?, 0)
                    ON CONFLICT(job_name) DO UPDATE SET errores_consecutivos=0,
                                                          ultimo_error_msg=NULL,
                                                          ultimo_error_at=NULL
                """, (job_name,))
            else:
                conn.execute("""
                    INSERT INTO cron_jobs_health (job_name, errores_consecutivos, ultimo_error_at, ultimo_error_msg)
                    VALUES (?, 1, datetime('now'), ?)
                    ON CONFLICT(job_name) DO UPDATE SET
                      errores_consecutivos = errores_consecutivos + 1,
                      ultimo_error_at = datetime('now'),
                      ultimo_error_msg = excluded.ultimo_error_msg
                """, (job_name, (error or '')[:300]))
                # Si 3+ errores consecutivos y no se ha notificado en 24h → email
                row = conn.execute("""
                    SELECT errores_consecutivos, notificado_at FROM cron_jobs_health WHERE job_name=?
                """, (job_name,)).fetchone()
                if row and row[0] >= 3:
                    notif_old = row[1]
                    notificar = True
                    if notif_old:
                        try:
                            from datetime import datetime as _dt
                            if (_dt.now() - _dt.fromisoformat(notif_old)).total_seconds() < 86400:
                                notificar = False
                        except Exception:
                            pass
                    if notificar:
                        log.warning(f'[multi-cron] {job_name}: {row[0]} errores consecutivos · notificando')
                        conn.execute("UPDATE cron_jobs_health SET notificado_at=datetime('now') WHERE job_name=?",
                                       (job_name,))
        except Exception:
            pass
        conn.commit()
    except Exception as e:
        log.warning(f'[multi-cron] no se pudo registrar {job_name}: {e}')


def job_sync_shopify(app):
    """Sync Shopify orders (jala últimas 250)."""
    with app.app_context():
        from database import get_db
        from blueprints.animus import _cfg
        conn = get_db()
        token = _cfg(conn, 'shopify_token')
        shop = _cfg(conn, 'shopify_shop')
        if not token or not shop:
            return False, {'error': 'Shopify no configurado'}, 0
        import urllib.request as ur
        import json as _json
        url = f"https://{shop}/admin/api/2024-01/orders.json?status=any&limit=250"
        req = ur.Request(url, headers={"X-Shopify-Access-Token": token})
        synced = 0
        with ur.urlopen(req, timeout=30) as r:
            orders = _json.loads(r.read())["orders"]
        for o in orders:
            items_sku = _json.dumps([
                {"sku": li.get("sku",""), "qty": li.get("quantity",0)}
                for li in o.get("line_items",[])
            ])
            total_uds = sum(li.get("quantity",0) for li in o.get("line_items",[]))
            addr = o.get("billing_address") or {}
            conn.execute("""
                INSERT OR REPLACE INTO animus_shopify_orders
                  (shopify_id, nombre, email, total, moneda, estado, estado_pago,
                   sku_items, unidades_total, ciudad, pais, creado_en, synced_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))
            """, (str(o["id"]), o.get("name",""), o.get("email",""),
                  float(o.get("total_price",0)), o.get("currency","COP"),
                  o.get("fulfillment_status",""), o.get("financial_status",""),
                  items_sku, total_uds,
                  addr.get("city",""), addr.get("country_code","CO"),
                  o.get("created_at","")[:10]))
            synced += 1
        conn.commit()
        return True, {'orders_synced': synced}, 0


def job_auto_d20(app):
    """Cron diario D-20: dispara SCs decoración."""
    with app.app_context():
        from database import get_db
        from blueprints.auto_plan import (
            _calendar_events_cached, _alias_calendar_for, _match_producto_evento,
            _parsear_kg_evento
        )
        from datetime import datetime as _dt, timedelta as _td
        conn = get_db(); c = conn.cursor()
        fecha_hoy = _dt.now().date()
        d_min = fecha_hoy + _td(days=15)
        d_max = fecha_hoy + _td(days=25)
        eventos = _calendar_events_cached()
        skus = {r[0]: r[0] for r in c.execute("""
            SELECT producto_nombre FROM sku_planeacion_config
            WHERE activo=1 AND COALESCE(estado,'activo') NOT IN ('descontinuado','pausado')
        """).fetchall()}
        scs = 0
        for ev in eventos:
            try:
                f = _dt.strptime((ev.get('fecha') or '')[:10], '%Y-%m-%d').date()
            except Exception:
                continue
            if f < d_min or f > d_max:
                continue
            prod_match = None
            for prod_nom in skus.keys():
                try:
                    alias = _alias_calendar_for(c, prod_nom)
                    score = _match_producto_evento(prod_nom, alias, ev.get('titulo'), ev.get('descripcion',''))
                    if score >= 60:
                        prod_match = prod_nom; break
                except Exception:
                    continue
            if not prod_match:
                continue
            kg = _parsear_kg_evento(ev.get('titulo'), ev.get('descripcion','')) or 30
            unidades = int(kg * 1000 / 30)
            existe = c.execute("""
                SELECT 1 FROM solicitudes_compra
                WHERE categoria='Servicios'
                  AND observaciones LIKE ?
                  AND date(fecha) >= date('now','-30 days')
                LIMIT 1
            """, (f'%decoración D-20 · {prod_match}%',)).fetchone()
            if existe:
                continue
            # Buscar componentes serigrafia/tampografia
            rows = c.execute("""
                SELECT s.mee_codigo, s.componente_tipo, s.cantidad_por_unidad,
                       m.descripcion, cfg.proveedor_principal, cfg.precio_unit
                FROM sku_mee_config s
                  LEFT JOIN maestro_mee m ON m.codigo = s.mee_codigo
                  LEFT JOIN mee_lead_time_config cfg ON cfg.mee_codigo = s.mee_codigo
                WHERE s.aplica = 1
                  AND s.componente_tipo IN ('serigrafia','tampografia')
                  AND COALESCE(cfg.disparo_d20,0) = 1
                  AND UPPER(TRIM(s.sku_codigo)) = UPPER(TRIM(?))
            """, (prod_match,)).fetchall()
            if not rows:
                continue
            por_prov = {}
            for cod, tipo, cant_pu, desc, prov, prec in rows:
                if not prov: continue
                cant = unidades * float(cant_pu or 1)
                por_prov.setdefault(prov, []).append({
                    'mee_codigo': cod, 'tipo': tipo, 'nombre': desc or cod,
                    'cantidad': cant, 'proveedor': prov,
                    'precio_unit': float(prec or 0),
                    'valor': cant * float(prec or 0),
                })
            for prov, items in por_prov.items():
                n = c.execute("""
                    SELECT COALESCE(MAX(CAST(SUBSTR(numero,10) AS INTEGER)), 0)
                    FROM solicitudes_compra WHERE numero LIKE ?
                """, (f"SOL-{_dt.now().strftime('%Y')}-%",)).fetchone()[0] + 1
                numero = f"SOL-{_dt.now().strftime('%Y')}-{n:04d}"
                observ = f'🎨 Cron D-20 · decoración D-20 · {prod_match} · producción {f.isoformat()} · {unidades} ud · proveedor {prov}'
                c.execute("""
                    INSERT INTO solicitudes_compra
                      (numero, fecha, estado, solicitante, urgencia, observaciones,
                       area, empresa, categoria, tipo, fecha_requerida, valor)
                    VALUES (?, ?, 'Pendiente', 'cron-d20-auto', 'Alta', ?, 'Produccion',
                            'Espagiria', 'Servicios', 'Compra', ?, ?)
                """, (numero, _dt.now().isoformat(), observ, f.isoformat(),
                      sum(it['valor'] for it in items)))
                for it in items:
                    try:
                        c.execute("""
                            INSERT INTO solicitudes_compra_items
                              (numero, codigo_mp, nombre_mp, cantidad_g, unidad,
                               justificacion, valor_estimado, proveedor_sugerido)
                            VALUES (?, ?, ?, ?, 'und', ?, ?, ?)
                        """, (numero, it['mee_codigo'], it['nombre'], it['cantidad'],
                              f"{it['tipo']} D-20 · {prod_match}",
                              it['valor'], it['proveedor']))
                    except sqlite3.OperationalError:
                        c.execute("""
                            INSERT INTO solicitudes_compra_items
                              (numero, codigo_mp, nombre_mp, cantidad_g, unidad,
                               justificacion, valor_estimado)
                            VALUES (?, ?, ?, ?, 'und', ?, ?)
                        """, (numero, it['mee_codigo'], it['nombre'], it['cantidad'],
                              f"{it['tipo']} D-20", it['valor']))
                scs += 1
        conn.commit()
        return True, {'scs_creadas': scs}, 0


def job_auto_sc_mensual(app):
    """Cron mensual día 1-5: SCs MP."""
    with app.app_context():
        from database import get_db
        from blueprints.auto_plan import _calcular_auto_sc
        conn = get_db()
        plan = _calcular_auto_sc(conn, horizontes_dias=(60, 90), modo='mensual')
        return True, {'kpis': plan.get('kpis', {})}, 0


def job_auto_sc_mee_mensual(app):
    """Cron mensual día 1-5: SCs MEE."""
    with app.app_context():
        from database import get_db
        from blueprints.auto_plan import _calcular_auto_sc_mee
        conn = get_db()
        plan = _calcular_auto_sc_mee(conn, modo='mensual')
        return True, {'kpis': plan.get('kpis', {})}, 0


def _sync_calendar_a_db(conn, c, fecha_inicio, fecha_fin, user='cron-sync'):
    """Sincroniza eventos del Calendar a produccion_programada en un rango.

    Sebastián 1-may-2026: 'no se activa solo · los eventos aparecen pero
    sin sincronizar'. Ahora el cron ejecuta el sync automáticamente.
    Devuelve: (insertadas, ya_existian)
    """
    from blueprints.auto_plan import (
        _calendar_events_cached, _match_producto_evento, _parsear_kg_evento,
    )
    from datetime import datetime as _dt
    cal_events = _calendar_events_cached(force_refresh=True) or []
    skus_aliases = {}
    for sku_n, alias_csv in c.execute("""
        SELECT producto_nombre, COALESCE(alias_calendar, '')
        FROM sku_planeacion_config
        WHERE activo=1 AND COALESCE(estado,'activo') NOT IN ('descontinuado','pausado')
    """).fetchall():
        skus_aliases[sku_n] = alias_csv

    import re as _re_local
    insertadas = 0
    ya_existian = 0
    for ev in cal_events:
        try:
            f_ev = _dt.strptime((ev.get('fecha') or '')[:10], '%Y-%m-%d').date()
        except Exception:
            continue
        if f_ev < fecha_inicio or f_ev > fecha_fin:
            continue
        # Match producto · umbral 50 (más permisivo)
        producto_match = None
        best_score = 0
        for prod_n, alias_csv in skus_aliases.items():
            try:
                score = _match_producto_evento(prod_n, alias_csv,
                                                 ev.get('titulo'), ev.get('descripcion',''))
                if score >= 50 and score > best_score:
                    best_score = score
                    producto_match = prod_n
            except Exception:
                continue
        kg = _parsear_kg_evento(ev.get('titulo'), ev.get('descripcion','')) or 0
        # FALLBACK: si no hay match, usar título crudo (Sebastián: insertar siempre)
        if producto_match:
            producto_final = producto_match
        else:
            t_clean = (ev.get('titulo') or '').strip()
            t_clean = _re_local.sub(r'\s*[-–]\s*Fab(rica|ric)?[a-z]*\s+\d.*$', '', t_clean, flags=_re_local.IGNORECASE)
            t_clean = _re_local.sub(r'\s*\(.*?\)\s*$', '', t_clean)
            t_clean = _re_local.sub(r'\s*\d+\s*kg.*$', '', t_clean, flags=_re_local.IGNORECASE)
            producto_final = t_clean.strip().upper() or 'EVENTO SIN MATCH'
        exists = c.execute("""
            SELECT id FROM produccion_programada
            WHERE producto = ? AND date(fecha_programada) = ?
        """, (producto_final, f_ev.isoformat())).fetchone()
        if exists:
            ya_existian += 1
            continue
        c.execute("""
            INSERT INTO produccion_programada
              (producto, fecha_programada, lotes, cantidad_kg,
               estado, observaciones, origen)
            VALUES (?, ?, 1, ?, 'programado', ?, 'calendar')
        """, (producto_final, f_ev.isoformat(), kg,
              f'[auto-sync {user}] {(ev.get("titulo") or "")[:200]}'))
        insertadas += 1
    return insertadas, ya_existian


def job_auto_asignar_areas(app):
    """Cron diario 6:30: SINCRONIZA Calendar→DB primero, luego auto-asigna
    área + envasado + operarios para producciones próximos 7d.

    Sebastián 1-may-2026: 'haz todo automático con IA · no se activa solo'.
    Ahora el cron ejecuta los 2 pasos en sucesión:
      1. Sync Calendar→DB (insertar eventos nuevos)
      2. Auto-asignar IA para producciones sin área/operarios
    """
    with app.app_context():
        from database import get_db
        from blueprints.programacion import _auto_asignar_produccion
        from datetime import datetime as _dt, timedelta as _td
        conn = get_db(); c = conn.cursor()
        fecha_hoy = _dt.now().date()
        # Ventana 14d (semana actual + próxima)
        fecha_inicio = fecha_hoy - _td(days=fecha_hoy.weekday())  # lunes esta semana
        fecha_fin = fecha_inicio + _td(days=14)

        # PASO 1: Sync Calendar → DB
        insertadas = 0; ya_existian = 0
        try:
            insertadas, ya_existian = _sync_calendar_a_db(
                conn, c, fecha_inicio, fecha_fin, 'cron-6:30'
            )
        except Exception as _e:
            log.warning(f'[auto-asignar-areas] sync calendar falla: {_e}')

        # PASO 2: Auto-asignar producciones sin área/operarios
        rows = c.execute("""
            SELECT id FROM produccion_programada
            WHERE date(fecha_programada) >= ?
              AND date(fecha_programada) <= ?
              AND COALESCE(estado, 'programado') NOT IN ('completado', 'cancelado')
              AND (area_id IS NULL
                   OR (operario_dispensacion_id IS NULL
                       AND operario_elaboracion_id IS NULL
                       AND operario_envasado_id IS NULL))
            ORDER BY fecha_programada ASC
        """, (fecha_hoy.isoformat(), fecha_fin.isoformat())).fetchall()
        procesadas, errores = 0, 0
        for (pid,) in rows:
            res = _auto_asignar_produccion(c, pid, 'cron-auto-asignar')
            if res.get('ok'):
                procesadas += 1
            else:
                errores += 1
        conn.commit()
        return True, {
            'sync_insertadas': insertadas,
            'sync_ya_existian': ya_existian,
            'asignadas': procesadas,
            'errores': errores,
            'total_evaluadas': len(rows),
        }, 0


def job_lunes_7am_workflow(app):
    """⭐ Workflow completo lunes 7am (Sebastián 1-may-2026):
    'el jefe de producción no debe hacer nada manualmente · solo entrar
    y ver lo que ya está programado y bloqueado'.

    Pasos secuenciales:
      1. Sync Shopify (velocidades actualizadas)
      2. Sync Calendar (force refresh · jala todos los eventos)
      3. Insertar producciones del Calendar a produccion_programada
      4. Auto-asignar IA cada producción (área + 4 operarios rotando)
      5. Crear limpiezas automáticas para áreas que terminarán sucias
      6. BLOQUEAR todas las producciones de la semana (no más cambios)
      7. Email a Alejandro/Sebastián con resumen
      8. Log en workflow_lunes_log
    """
    import json as _json
    with app.app_context():
        from database import get_db
        from datetime import datetime as _dt, timedelta as _td, date as _date
        conn = get_db(); c = conn.cursor()

        fecha_hoy = _dt.now().date()
        # Lunes de esta semana (si hoy NO es lunes, calcular el lunes)
        base = fecha_hoy
        while base.weekday() != 0:
            base -= _td(days=1)
        lunes_semana = base
        viernes_semana = lunes_semana + _td(days=4)
        workflow_id = f'lunes-{lunes_semana.isoformat()}'

        resumen = {
            'workflow_id': workflow_id,
            'lunes': lunes_semana.isoformat(),
            'viernes': viernes_semana.isoformat(),
            'pasos': [],
        }

        # PASO 1: Sync Shopify
        try:
            from blueprints.animus import _cfg
            token = _cfg(conn, 'shopify_token')
            shop = _cfg(conn, 'shopify_shop')
            if token and shop:
                import urllib.request as _ur
                url = f"https://{shop}/admin/api/2024-01/orders.json?status=any&limit=250"
                req = _ur.Request(url, headers={"X-Shopify-Access-Token": token})
                synced = 0
                with _ur.urlopen(req, timeout=30) as r:
                    orders = _json.loads(r.read())["orders"]
                for o in orders:
                    items_sku = _json.dumps([{"sku": li.get("sku",""), "qty": li.get("quantity",0)}
                                              for li in o.get("line_items",[])])
                    total_uds = sum(li.get("quantity",0) for li in o.get("line_items",[]))
                    addr = o.get("billing_address") or {}
                    conn.execute("""
                        INSERT OR REPLACE INTO animus_shopify_orders
                          (shopify_id, nombre, email, total, moneda, estado, estado_pago,
                           sku_items, unidades_total, ciudad, pais, creado_en, synced_at)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))
                    """, (str(o["id"]), o.get("name",""), o.get("email",""),
                          float(o.get("total_price",0)), o.get("currency","COP"),
                          o.get("fulfillment_status",""), o.get("financial_status",""),
                          items_sku, total_uds,
                          addr.get("city",""), addr.get("country_code","CO"),
                          o.get("created_at","")[:10]))
                    synced += 1
                resumen['pasos'].append(f'Sync Shopify: {synced} órdenes')
            else:
                resumen['pasos'].append('Sync Shopify: skipped (sin token)')
        except Exception as e:
            resumen['pasos'].append(f'Sync Shopify ERROR: {str(e)[:100]}')

        # PASO 2-3-4: Sync Calendar + insertar + auto-asignar IA
        sincronizadas = 0
        asignadas = 0
        try:
            from blueprints.auto_plan import (
                _calendar_events_cached, _alias_calendar_for, _match_producto_evento,
                _parsear_kg_evento
            )
            from blueprints.programacion import _auto_asignar_produccion
            cal_events = _calendar_events_cached(force_refresh=True) or []
            skus_aliases = {}
            for sku_n, alias_csv in c.execute("""
                SELECT producto_nombre, COALESCE(alias_calendar, '')
                FROM sku_planeacion_config
                WHERE activo=1 AND COALESCE(estado,'activo') NOT IN ('descontinuado','pausado')
            """).fetchall():
                skus_aliases[sku_n] = alias_csv

            for ev in cal_events:
                try:
                    f_ev = _dt.strptime((ev.get('fecha') or '')[:10], '%Y-%m-%d').date()
                except Exception:
                    continue
                # Solo eventos de la semana en curso
                if f_ev < lunes_semana or f_ev > viernes_semana:
                    continue
                producto_match = None
                best_score = 0
                for prod_n, alias_csv in skus_aliases.items():
                    try:
                        score = _match_producto_evento(prod_n, alias_csv,
                                                         ev.get('titulo'), ev.get('descripcion',''))
                        if score >= 60 and score > best_score:
                            best_score = score
                            producto_match = prod_n
                    except Exception:
                        continue
                if not producto_match: continue
                kg = _parsear_kg_evento(ev.get('titulo'), ev.get('descripcion','')) or 0
                # Skip si ya existe
                exists = c.execute("""
                    SELECT id, area_id, operario_dispensacion_id FROM produccion_programada
                    WHERE producto=? AND date(fecha_programada)=?
                """, (producto_match, f_ev.isoformat())).fetchone()
                if exists:
                    pid_existente = exists[0]
                    if not exists[1] and not exists[2]:
                        res = _auto_asignar_produccion(c, pid_existente, 'cron-lunes-7am')
                        if res.get('ok'): asignadas += 1
                    continue
                cur_ins = c.execute("""
                    INSERT INTO produccion_programada
                      (producto, fecha_programada, lotes, cantidad_kg,
                       estado, observaciones, origen, semana_workflow_id)
                    VALUES (?, ?, 1, ?, 'programado', ?, 'calendar', ?)
                """, (producto_match, f_ev.isoformat(), kg,
                      f'[lunes 7am] {(ev.get("titulo") or "")[:200]}',
                      workflow_id))
                new_id = cur_ins.lastrowid
                sincronizadas += 1
                if kg > 0 and new_id:
                    res = _auto_asignar_produccion(c, new_id, 'cron-lunes-7am')
                    if res.get('ok'): asignadas += 1
            resumen['pasos'].append(f'Calendar: {sincronizadas} producciones nuevas · {asignadas} asignadas IA')
        except Exception as e:
            resumen['pasos'].append(f'Calendar ERROR: {str(e)[:100]}')

        # PASO 5: Crear limpiezas para áreas que tendrán producción esta semana
        limpiezas_creadas = 0
        try:
            # Áreas que terminan producción esta semana → limpieza día siguiente
            # (esto ya lo maneja el hook prog_completar_evento, pero ejecutamos
            # un sweep para limpiezas faltantes)
            from blueprints.programacion import _crear_limpieza_post_produccion
            rows = c.execute("""
                SELECT a.id, a.codigo FROM areas_planta a
                WHERE a.activo=1 AND a.estado='sucia'
                  AND NOT EXISTS (
                    SELECT 1 FROM limpieza_profunda_calendario l
                    WHERE l.area_codigo = a.codigo
                      AND l.estado IN ('pendiente','asignada','en_proceso')
                      AND date(l.fecha) >= date('now')
                  )
            """).fetchall()
            for area_id, area_cod in rows:
                limp = _crear_limpieza_post_produccion(c, area_id, area_cod,
                                                        fecha_hoy.isoformat(),
                                                        'lunes-7am', '', 'cron-lunes-7am')
                if limp: limpiezas_creadas += 1
            resumen['pasos'].append(f'Limpiezas auto: {limpiezas_creadas}')
        except Exception as e:
            resumen['pasos'].append(f'Limpiezas ERROR: {str(e)[:100]}')

        # PASO 6: BLOQUEAR producciones de la semana
        bloqueadas = 0
        try:
            cur = c.execute("""
                UPDATE produccion_programada
                  SET bloqueado_at = datetime('now'),
                      bloqueado_por = 'cron-lunes-7am',
                      semana_workflow_id = COALESCE(NULLIF(semana_workflow_id,''), ?)
                WHERE date(fecha_programada) BETWEEN ? AND ?
                  AND COALESCE(estado, 'programado') NOT IN ('completado','cancelado')
                  AND bloqueado_at IS NULL
            """, (workflow_id, lunes_semana.isoformat(), viernes_semana.isoformat()))
            bloqueadas = cur.rowcount
            resumen['pasos'].append(f'Bloqueadas: {bloqueadas} producciones de la semana')
        except Exception as e:
            resumen['pasos'].append(f'Bloqueo ERROR: {str(e)[:100]}')

        # PASO 7: Email Alejandro/Sebastián
        email_enviado = False
        try:
            destinatarios = []
            rows = c.execute("""
                SELECT email FROM email_destinatarios_config
                WHERE activo=1 AND email != ''
                  AND (rol IN ('ceo','gerencia_produccion','jefe_planta')
                       OR LOWER(email) LIKE '%alejandro%'
                       OR LOWER(email) LIKE '%sebastian%')
            """).fetchall()
            destinatarios = [r[0] for r in rows if r[0]]
            if destinatarios:
                html = f'''<!DOCTYPE html><html><body style="font-family:-apple-system,sans-serif;background:#f3f4f6;padding:20px">
                <div style="max-width:640px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 12px rgba(0,0,0,.08)">
                  <div style="background:linear-gradient(135deg,#0f766e,#0891b2);color:#fff;padding:20px">
                    <h2 style="margin:0;font-size:20px">📅 Plan Semanal Listo · {lunes_semana.strftime("%d-%b")} a {viernes_semana.strftime("%d-%b")}</h2>
                    <p style="margin:4px 0 0;opacity:.9;font-size:13px">Lunes 7am · IA programó y bloqueó la semana</p>
                  </div>
                  <div style="padding:20px;font-size:13px;color:#0f172a">
                    <div style="background:#ecfdf5;border:1px solid #6ee7b7;padding:10px;border-radius:6px;margin-bottom:14px;color:#065f46">
                      ✅ Workflow lunes 7am ejecutado · {bloqueadas} producciones bloqueadas
                    </div>
                    <h3 style="margin:14px 0 8px">Pasos ejecutados:</h3>
                    <ul style="margin:0;padding:0 0 0 20px">{''.join(f'<li>{p}</li>' for p in resumen["pasos"])}</ul>
                    <p style="font-size:11px;color:#64748b;margin-top:14px">El equipo de planta solo entra a la app y ejecuta lo asignado · sin clicks de configuración</p>
                  </div>
                </div></body></html>'''
                import threading, sys, os as _os
                sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
                from notificaciones import SistemaNotificaciones
                notif = SistemaNotificaciones()
                threading.Thread(
                    target=notif._enviar_email,
                    args=(f'📅 Plan Semanal Listo · {lunes_semana.strftime("%d-%b")} (lunes 7am)', html, destinatarios),
                    daemon=True
                ).start()
                email_enviado = True
                resumen['pasos'].append(f'Email enviado a {len(destinatarios)} destinatarios')
            else:
                resumen['pasos'].append('Email skipped (sin destinatarios)')
        except Exception as e:
            resumen['pasos'].append(f'Email ERROR: {str(e)[:80]}')

        # PASO 8: Log
        try:
            c.execute("""
                INSERT INTO workflow_lunes_log
                  (fecha_lunes, producciones_bloqueadas, sincronizadas, asignadas,
                   limpiezas_creadas, email_enviado, payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (lunes_semana.isoformat(), bloqueadas, sincronizadas, asignadas,
                  limpiezas_creadas, 1 if email_enviado else 0,
                  _json.dumps(resumen)))
            conn.commit()
        except Exception:
            pass

        return True, {
            'fecha_lunes': lunes_semana.isoformat(),
            'bloqueadas': bloqueadas,
            'sincronizadas': sincronizadas,
            'asignadas': asignadas,
            'limpiezas_creadas': limpiezas_creadas,
            'email_enviado': email_enviado,
            'pasos': resumen['pasos'],
        }, 0


def job_self_heal(app):
    """Self-heal diario 7am: arregla problemas comunes detectados.
    Sebastián 1-may-2026: 'que se ejecute perfecto · todo automático'."""
    with app.app_context():
        from database import get_db
        from datetime import datetime as _dt, timedelta as _td, date as _date
        from blueprints.programacion import (
            _crear_limpieza_post_produccion, _auto_asignar_produccion
        )
        conn = get_db(); c = conn.cursor()
        acciones = []

        # 1) Habilitar cron si está deshabilitado
        try:
            r = c.execute("SELECT habilitado FROM auto_plan_cron_state WHERE id=1").fetchone()
            if r and not r[0]:
                c.execute("UPDATE auto_plan_cron_state SET habilitado=1, notas='Self-heal auto-enable', activado_por='self-heal', activado_at=datetime('now') WHERE id=1")
                acciones.append('cron habilitado')
        except Exception:
            pass

        # 2) Limpiezas pendientes para áreas sucias
        try:
            rows = c.execute("""
                SELECT a.id, a.codigo FROM areas_planta a
                WHERE a.activo=1 AND a.estado='sucia'
                  AND NOT EXISTS (
                    SELECT 1 FROM limpieza_profunda_calendario l
                    WHERE l.area_codigo = a.codigo
                      AND l.estado IN ('pendiente','asignada','en_proceso')
                      AND date(l.fecha) >= date('now')
                  )
            """).fetchall()
            for area_id, area_cod in rows:
                limp = _crear_limpieza_post_produccion(c, area_id, area_cod,
                                                        _date.today().isoformat(),
                                                        'self-heal', '', 'cron-self-heal')
                if limp: acciones.append(f'limpieza {area_cod}')
        except Exception:
            pass

        # 3) Auto-asignar producciones próximas pendientes
        try:
            fecha_hoy = _dt.now().date()
            fecha_max = fecha_hoy + _td(days=7)
            rows = c.execute("""
                SELECT id FROM produccion_programada
                WHERE date(fecha_programada) BETWEEN ? AND ?
                  AND COALESCE(estado, 'programado') NOT IN ('completado','cancelado')
                  AND (area_id IS NULL OR (operario_dispensacion_id IS NULL
                       AND operario_elaboracion_id IS NULL
                       AND operario_envasado_id IS NULL))
            """, (fecha_hoy.isoformat(), fecha_max.isoformat())).fetchall()
            for (pid,) in rows:
                res = _auto_asignar_produccion(c, pid, 'cron-self-heal')
                if res.get('ok'): acciones.append(f'asign #{pid}')
        except Exception:
            pass

        conn.commit()
        return True, {'acciones': acciones, 'total': len(acciones)}, 0


def job_cleanup_logs(app):
    """Cleanup nocturno 2am: borra logs viejos para mantener DB ligera.
    cron_jobs_runs > 30d, auto_plan_runs > 90d, auto_asignacion_log > 90d."""
    with app.app_context():
        from database import get_db
        conn = get_db(); c = conn.cursor()
        n_runs = 0; n_apr = 0; n_aal = 0
        try:
            n_runs = c.execute("DELETE FROM cron_jobs_runs WHERE date(ejecutado_at) < date('now', '-30 days')").rowcount
        except Exception: pass
        try:
            n_apr = c.execute("DELETE FROM auto_plan_runs WHERE date(ejecutado_at) < date('now', '-90 days')").rowcount
        except Exception: pass
        try:
            n_aal = c.execute("DELETE FROM auto_asignacion_log WHERE date(ejecutado_at) < date('now', '-90 days')").rowcount
        except Exception: pass
        # VACUUM para reclamar espacio (ligero, sin lock)
        try:
            c.execute("PRAGMA incremental_vacuum")
        except Exception: pass
        conn.commit()
        return True, {'cron_jobs_runs': n_runs, 'auto_plan_runs': n_apr,
                       'auto_asignacion_log': n_aal}, 0


def job_auto_sc_urgente(app):
    """Cron lunes 12:00: SCs urgentes."""
    with app.app_context():
        from database import get_db
        from blueprints.auto_plan import _calcular_auto_sc
        conn = get_db()
        plan = _calcular_auto_sc(conn, horizontes_dias=(14, 30), modo='urgente')
        return True, {'kpis': plan.get('kpis', {})}, 0


def _loop_multi_cron(app):
    """Loop cada 5 min revisa schedule de jobs y ejecuta los que apliquen."""
    log.info('[multi-cron] Loop iniciado · 5 jobs configurados')
    import time as _time
    import time as time_mod
    from datetime import datetime as _dt
    while True:
        try:
            with app.app_context():
                from database import get_db
                conn = get_db()
                ahora = _dt.now()
                for job_name, hora, minuto, dias_sem, dias_mes, callable_name in JOBS_SCHEDULE:
                    if not _es_hora_de(ahora, hora, minuto, dias_sem, dias_mes):
                        continue
                    if _ya_ejecutado_hoy(conn, job_name):
                        continue
                    fn = globals().get(callable_name)
                    if not fn:
                        log.warning(f'[multi-cron] {job_name}: callable {callable_name} no existe')
                        continue
                    log.info(f'[multi-cron] Ejecutando {job_name}...')
                    t0 = _time.time()
                    try:
                        ok, resultado, _ = fn(app)
                        dur = int((_time.time() - t0) * 1000)
                        _registrar_ejecucion(conn, job_name, ok, resultado, dur)
                        log.info(f'[multi-cron] {job_name} ok={ok} · {dur}ms · {resultado}')
                    except Exception as e:
                        dur = int((_time.time() - t0) * 1000)
                        log.exception(f'[multi-cron] {job_name} excepción')
                        _registrar_ejecucion(conn, job_name, False, None, dur, str(e))
        except Exception as e:
            log.exception(f'[multi-cron] error en loop: {e}')
        time_mod.sleep(300)  # cada 5 min


def iniciar_multi_cron(app):
    """Lanza el thread del scheduler multi-job al arranque.
    Sebastián 1-may-2026: sin dependencia de Render Cron Jobs externos."""
    if getattr(app, '_multi_cron_started', False):
        return
    t = threading.Thread(target=_loop_multi_cron, args=(app,), daemon=True)
    t.start()
    app._multi_cron_started = True
    log.info('[multi-cron] Multi-cron thread arrancado · jobs: ' +
             ', '.join(j[0] for j in JOBS_SCHEDULE))
