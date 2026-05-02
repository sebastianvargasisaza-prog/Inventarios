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
    """Envía email en thread separado. Nunca falla.

    Sebastián 1-may-2026 audit zero-error: el thread loguea el resultado
    real del envío. Antes silencioso · si SMTP fallaba nadie sabía.
    """
    if not destinos:
        return False
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from notificaciones import SistemaNotificaciones
        notif = SistemaNotificaciones()

        def _wrapped_send():
            try:
                resultado = notif._enviar_email(asunto, html, destinos)
                if resultado is False:
                    log.warning('[auto-plan-email] SMTP rechazó envio · asunto=%r destinos=%s',
                                asunto[:80], destinos)
                else:
                    log.info('[auto-plan-email] OK · asunto=%r destinos=%d',
                             asunto[:80], len(destinos))
            except Exception as _e:
                log.exception('[auto-plan-email] thread excepción asunto=%r: %s',
                              asunto[:80], _e)

        t = threading.Thread(target=_wrapped_send, daemon=True)
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
            except Exception as _e:
                log.warning('update emails_enviados fallo: %s', _e)

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
    """Lee auto_plan_cron_state.habilitado desde la DB. Default conservador:
    si la DB está temporalmente inaccesible, retorna False (no ejecutar)."""
    with app.app_context():
        try:
            from database import get_db
            r = get_db().execute(
                "SELECT habilitado FROM auto_plan_cron_state WHERE id=1"
            ).fetchone()
            return bool(r[0]) if r else False
        except Exception as e:
            log.warning('_cron_habilitado_en_db read fallo: %s · returning False', e)
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
            except Exception as _e:
                log.warning('update ultima_ejecucion_at fallo: %s', _e)
        except Exception as e:
            log.exception(f'[auto-plan-cron] excepción: {e}')
            try:
                with app.app_context():
                    from database import get_db
                    get_db().execute(
                        "UPDATE auto_plan_cron_state SET errores_consecutivos=errores_consecutivos+1 WHERE id=1"
                    )
                    get_db().commit()
            except Exception as _e:
                log.warning('update errores_consecutivos fallo: %s', _e)


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
    # ⭐ Calidad · L-V 12:00 · alerta si falta registro sistema agua hoy (COC-PRO-008)
    ('agua_recordatorio',    12,  0, [0,1,2,3,4], None,         'job_agua_recordatorio'),
    # ⭐ Calidad · diario 7:30 · alerta equipos próximos a vencer + vencidos (COC-PRO-012)
    ('equipos_vencimientos',  7, 30, None, None,                'job_equipos_vencimientos'),
    # ⭐ Aseguramiento · diario 8:00 · alerta desviaciones en plazos críticos (ASG-PRO-001)
    ('desv_plazos',           8,  0, None, None,                'job_desv_plazos'),
    # ⭐ Aseguramiento · diario 8:30 · alerta control de cambios en plazos vencidos (ASG-PRO-007)
    ('cambios_plazos',        8, 30, None, None,                'job_cambios_plazos'),
    # ⭐ Aseguramiento · diario 9:00 · alerta quejas sin triar/responder/cerrar (ASG-PRO-013)
    ('quejas_plazos',         9,  0, None, None,                'job_quejas_plazos'),
    # ⭐ Aseguramiento · diario 9:30 · alerta recalls sin clasificar/notificar (ASG-PRO-004)
    ('recalls_plazos',        9, 30, None, None,                'job_recalls_plazos'),
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


def _ya_ejecutado_hoy(conn, job_name, retry_si_fallo_horas=2):
    """¿Ya se ejecutó este job hoy?
    Sebastián 1-may-2026: si falló (ok=0), permitir retry pero solo si la
    última ejecución fue hace >2h (evita loop de 12 retries cada 5min que
    duplican datos cuando el fallo es post-commit parcial).

    Returns: True si ya hay éxito hoy, O si hubo fallo reciente (<2h).
    """
    try:
        # ¿Éxito hoy?
        row_ok = conn.execute("""
            SELECT 1 FROM cron_jobs_runs
            WHERE job_name = ? AND ok = 1
              AND date(ejecutado_at) = date('now')
            LIMIT 1
        """, (job_name,)).fetchone()
        if row_ok: return True
        # ¿Fallo reciente (<retry_si_fallo_horas)?
        row_fail = conn.execute("""
            SELECT 1 FROM cron_jobs_runs
            WHERE job_name = ? AND ok = 0
              AND ejecutado_at >= datetime('now', '-' || ? || ' hours')
            LIMIT 1
        """, (job_name, retry_si_fallo_horas)).fetchone()
        return bool(row_fail)
    except Exception as e:
        log.warning('_ya_ejecutado_hoy(%s) read fallo: %s · returning False', job_name, e)
        return False


def _adquirir_lock_cron(conn, job_name, ttl_horas=2):
    """Reserva atómica del derecho a ejecutar un cron job (anti race entre workers).

    Antes: dos workers podían pasar `_ya_ejecutado_hoy=False` en paralelo y
    ejecutar el job dos veces (duplicando datos · creando SCs duplicadas).

    Ahora: INSERT OR IGNORE en cron_locks con UNIQUE(job_name) garantiza
    atomicidad. Locks viejos (>ttl_horas) se limpian automáticamente para
    cubrir el caso de un crash sin _liberar_lock_cron.

    Returns: True si reclamó el lock (este worker debe ejecutar), False si
    otro worker ya lo tiene activo.
    """
    try:
        # Limpiar locks vencidos antes de intentar reclamar
        conn.execute("""
            DELETE FROM cron_locks
            WHERE locked_at < datetime('now', '-' || ? || ' hours')
        """, (ttl_horas,))
        cur = conn.execute("""
            INSERT OR IGNORE INTO cron_locks (job_name, locked_at, locked_by)
            VALUES (?, datetime('now'), 'multi-cron')
        """, (job_name,))
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        log.warning('_adquirir_lock_cron(%s) fallo: %s', job_name, e)
        return False


def _liberar_lock_cron(conn, job_name):
    """Libera el lock de un job. Idempotente."""
    try:
        conn.execute("DELETE FROM cron_locks WHERE job_name = ?", (job_name,))
        conn.commit()
    except Exception as e:
        log.warning('_liberar_lock_cron(%s) fallo: %s', job_name, e)


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
                        except Exception as _e:
                            log.info('parse notificado_at fallo (%s): %s', notif_old, _e)
                    if notificar:
                        log.warning(f'[multi-cron] {job_name}: {row[0]} errores consecutivos · notificando')
                        conn.execute("UPDATE cron_jobs_health SET notificado_at=datetime('now') WHERE job_name=?",
                                       (job_name,))
        except Exception as _e:
            log.warning('cron_jobs_health update %s fallo: %s', job_name, _e)
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
    """DEPRECATED 1-may-2026 (Calendar-first): NO inserta nada.
    En la arquitectura nueva, Calendar es la única fuente de verdad y
    la DB solo recibe filas cuando el usuario clickea ▶ Iniciar (Calendar)
    desde Operación Live. Este helper queda como stub no-op para no
    romper crons legacy que aún lo invoquen.

    Devuelve (0, 0) siempre.
    """
    return 0, 0


def job_auto_asignar_areas(app):
    """Cron diario 6:30: auto-asigna área + envasado + operarios para
    producciones que YA existen en DB sin asignación.

    Sebastián 1-may-2026 (refactor Calendar-first): el PASO 1 (sync Calendar→DB)
    se ELIMINÓ. La DB solo guarda lo que YA se inició/terminó. El cron solo
    completa asignaciones de filas DB ya creadas (manuales o desde
    iniciar_calendar). Calendar es la fuente de verdad para 'lo que toca'.
    """
    with app.app_context():
        from database import get_db
        from blueprints.programacion import _auto_asignar_produccion
        from datetime import datetime as _dt, timedelta as _td
        conn = get_db(); c = conn.cursor()
        fecha_hoy = _dt.now().date()
        # Ventana 14d (semana actual + próxima) · solo filas DB existentes
        fecha_inicio = fecha_hoy - _td(days=fecha_hoy.weekday())  # lunes esta semana
        fecha_fin = fecha_inicio + _td(days=14)

        # Solo auto-asignar producciones DB sin área/operarios (NO sync Calendar)
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
            'sync_deprecated': True,  # PASO 1 eliminado · Calendar-first
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

        # PASO 2: Auto-asignar IA a producciones DB existentes (Calendar-first)
        # Sebastián 1-may-2026: refactor · YA NO insertamos desde Calendar.
        # Calendar es la fuente de verdad. La DB solo recibe filas cuando el
        # usuario clickea ▶ Iniciar (Calendar) en Operación Live. Aquí solo
        # completamos asignaciones de filas que ya existen.
        sincronizadas = 0  # Mantenido en payload por compat (siempre 0 ahora)
        asignadas = 0
        try:
            from blueprints.programacion import _auto_asignar_produccion
            rows_sin_asignar = c.execute("""
                SELECT id FROM produccion_programada
                WHERE date(fecha_programada) BETWEEN ? AND ?
                  AND COALESCE(estado, 'programado') NOT IN ('completado', 'cancelado')
                  AND (area_id IS NULL
                       OR (operario_dispensacion_id IS NULL
                           AND operario_elaboracion_id IS NULL
                           AND operario_envasado_id IS NULL))
            """, (lunes_semana.isoformat(), viernes_semana.isoformat())).fetchall()
            for (pid,) in rows_sin_asignar:
                res = _auto_asignar_produccion(c, pid, 'cron-lunes-7am')
                if res.get('ok'): asignadas += 1
            resumen['pasos'].append(f'Auto-asignación IA: {asignadas}/{len(rows_sin_asignar)} filas DB asignadas (Calendar-first · NO sync)')
        except Exception as e:
            resumen['pasos'].append(f'Auto-asignación ERROR: {str(e)[:100]}')

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
    Sebastián 1-may-2026: 'que se ejecute perfecto · todo automático'.

    Skip si lunes_7am_workflow YA corrió con éxito hoy (ese workflow ya
    cubre auto-asignación · evita duplicados en logs).
    """
    with app.app_context():
        from database import get_db
        from datetime import datetime as _dt, timedelta as _td, date as _date
        from blueprints.programacion import (
            _crear_limpieza_post_produccion, _auto_asignar_produccion
        )
        conn = get_db(); c = conn.cursor()
        # Skip si lunes_7am corrió con éxito (solo lunes obviamente)
        if _dt.now().weekday() == 0 and _ya_ejecutado_hoy(conn, 'lunes_7am_workflow'):
            return True, {'skipped': True, 'razon': 'lunes_7am ya cubrió esto'}, 0
        acciones = []

        # 1) Habilitar cron si está deshabilitado
        try:
            r = c.execute("SELECT habilitado FROM auto_plan_cron_state WHERE id=1").fetchone()
            if r and not r[0]:
                c.execute("UPDATE auto_plan_cron_state SET habilitado=1, notas='Self-heal auto-enable', activado_por='self-heal', activado_at=datetime('now') WHERE id=1")
                acciones.append('cron habilitado')
        except Exception as _e:
            log.warning('self-heal habilitar cron fallo: %s', _e)

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
        except Exception as _e:
            log.warning('self-heal limpiezas fallo: %s', _e)

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
        except Exception as _e:
            log.warning('self-heal auto-asignar fallo: %s', _e)

        # 4) Reparar regla Mayerlin (audit zero-error 1-may-2026 round 2):
        # detectar producciones futuras con operario fija_en_dispensacion=1
        # asignado a roles ≠ dispensación · NULLearlas y dejar que la próxima
        # corrida del cron las re-asigne con la regla dura nueva.
        try:
            fecha_hoy = _dt.now().date()
            fecha_max = fecha_hoy + _td(days=14)
            fijos_ids = [r[0] for r in c.execute("""
                SELECT id FROM operarios_planta
                WHERE COALESCE(fija_en_dispensacion,0) = 1
                  AND COALESCE(activo,1) = 1
            """).fetchall()]
            n_reparadas = 0
            if fijos_ids:
                placeholders = ','.join('?' * len(fijos_ids))
                params = [fecha_hoy.isoformat(), fecha_max.isoformat()]
                params.extend(fijos_ids * 3)
                rows = c.execute(f"""
                    SELECT id, producto, fecha_programada FROM produccion_programada
                    WHERE date(fecha_programada) BETWEEN ? AND ?
                      AND COALESCE(estado, 'programado') NOT IN ('completado','cancelado')
                      AND (operario_elaboracion_id IN ({placeholders})
                        OR operario_envasado_id IN ({placeholders})
                        OR operario_acondicionamiento_id IN ({placeholders}))
                """, params).fetchall()
                from blueprints.programacion import _auto_asignar_operarios
                for pid, _prod, _fecha_iso in rows:
                    # NULL los 3 roles ≠ dispensacion (mantener disp si está OK)
                    c.execute("""
                        UPDATE produccion_programada SET
                          operario_elaboracion_id = NULL,
                          operario_envasado_id = NULL,
                          operario_acondicionamiento_id = NULL
                        WHERE id = ?
                    """, (pid,))
                    fecha_iso = (_fecha_iso or '')[:10] or fecha_hoy.isoformat()
                    try:
                        _auto_asignar_operarios(c, pid, fecha_iso, 'self-heal-mayerlin')
                        n_reparadas += 1
                    except Exception as _ee:
                        log.warning('self-heal reparar Mayerlin prod=%s fallo: %s', pid, _ee)
            if n_reparadas:
                acciones.append(f'reparadas regla-fija {n_reparadas} prods')
        except Exception as _e:
            log.warning('self-heal reparar regla fija fallo: %s', _e)

        conn.commit()
        return True, {'acciones': acciones, 'total': len(acciones)}, 0


def job_cleanup_logs(app):
    """Cleanup nocturno 2am: borra logs viejos para mantener DB ligera.
    cron_jobs_runs > 30d, auto_plan_runs > 90d, auto_asignacion_log > 90d."""
    with app.app_context():
        from database import get_db
        conn = get_db(); c = conn.cursor()
        n_runs = 0; n_apr = 0; n_aal = 0
        errores = []
        try:
            n_runs = c.execute("DELETE FROM cron_jobs_runs WHERE date(ejecutado_at) < date('now', '-30 days')").rowcount
        except Exception as e:
            log.warning('cleanup cron_jobs_runs fallo: %s', e)
            errores.append(f'cron_jobs_runs:{e}')
        try:
            n_apr = c.execute("DELETE FROM auto_plan_runs WHERE date(ejecutado_at) < date('now', '-90 days')").rowcount
        except Exception as e:
            log.warning('cleanup auto_plan_runs fallo: %s', e)
            errores.append(f'auto_plan_runs:{e}')
        try:
            n_aal = c.execute("DELETE FROM auto_asignacion_log WHERE date(ejecutado_at) < date('now', '-90 days')").rowcount
        except Exception as e:
            log.warning('cleanup auto_asignacion_log fallo: %s', e)
            errores.append(f'auto_asignacion_log:{e}')
        # VACUUM para reclamar espacio (ligero, sin lock)
        try:
            c.execute("PRAGMA incremental_vacuum")
        except Exception as e:
            log.info('incremental_vacuum no aplicable: %s', e)
        conn.commit()
        return True, {'cron_jobs_runs': n_runs, 'auto_plan_runs': n_apr,
                       'auto_asignacion_log': n_aal,
                       'errores': errores}, 0


def job_agua_recordatorio(app):
    """COC-PRO-008 · Si pasaron las 12 PM y NO hay registro del sistema de
    agua hoy → push notif a Calidad + email a Sebastián.

    Sebastián 1-may-2026: el control diario del sistema de agua es lo que
    INVIMA audita más exhaustivamente. Reemplaza Excel manual + WhatsApp.
    """
    with app.app_context():
        from database import get_db
        conn = get_db(); c = conn.cursor()
        try:
            row = c.execute("""
                SELECT 1 FROM calidad_sistema_agua
                WHERE date(fecha) = date('now')
                LIMIT 1
            """).fetchone()
        except Exception as e:
            log.warning('agua_recordatorio read fallo: %s', e)
            return False, {'error': str(e)[:200]}, 0
        if row:
            return True, {'mensaje': 'Registro de agua hoy presente · sin alerta'}, 0
        # No hay registro → notificar
        try:
            from blueprints.notif import push_notif_multi
            destinatarios = ['controlcalidad.espagiria','aseguramiento.espagiria',
                             'laura','miguel','yuliel','sebastian']
            push_notif_multi(
                destinatarios,
                'capa',
                '⚠ Falta registro del sistema de agua HOY',
                body='Son las 12:00 PM y aún no hay lectura registrada en /calidad → tab "Sistema de Agua" (COC-PRO-008).',
                link='/calidad', remitente='cron-agua', importante=True
            )
        except Exception as e:
            log.warning('agua_recordatorio push_notif fallo: %s', e)
        return True, {'mensaje': 'Alerta enviada · falta registro de agua hoy',
                       'destinatarios': 6}, 0


def job_equipos_vencimientos(app):
    """COC-PRO-012 · Diario 7:30 · alerta equipos vencidos + próximos 30d.

    Sebastián 1-may-2026: el sistema audita los 104 equipos del listado
    maestro vs eventos_planta y notifica a Calidad de:
    - Equipos VENCIDOS (calibración expirada) → bloqueo operativo
    - Equipos próximos a vencer en ≤30d → planear calibración

    Idempotente: si no hay vencidos ni próximos, no notifica.
    """
    with app.app_context():
        from database import get_db
        conn = get_db(); c = conn.cursor()
        try:
            # Equipos con fecha_proxima vencida o próxima 30d
            rows = c.execute("""
                SELECT ep.codigo, ep.nombre, ep.area_codigo,
                       MAX(ee.fecha_proxima) as fecha_proxima
                FROM equipos_planta ep
                LEFT JOIN equipos_eventos ee
                  ON ee.equipo_codigo = ep.codigo
                  AND ee.tipo_evento IN ('calibracion','verificacion_semestral')
                  AND ee.fecha_proxima IS NOT NULL
                WHERE COALESCE(ep.activo,1) = 1
                GROUP BY ep.codigo
                HAVING fecha_proxima IS NOT NULL
                  AND date(fecha_proxima) <= date('now', '+30 days')
                ORDER BY fecha_proxima ASC
                LIMIT 100
            """).fetchall()
        except Exception as e:
            log.warning('equipos_vencimientos read fallo: %s', e)
            return False, {'error': str(e)[:200]}, 0

        from datetime import date as _date
        hoy = _date.today()
        vencidos = []     # T-0 o atrás · CRÍTICO
        urgentes = []     # T-1 a T-7 · URGENTE
        proximos = []     # T-8 a T-30 · preventivo
        for cod, nom, area, prox in rows:
            try:
                f = _date.fromisoformat(prox)
                dias = (f - hoy).days
            except Exception:
                continue
            entry = {'codigo': cod, 'nombre': nom or '', 'area': area or '', 'dias': dias}
            if dias < 0:
                vencidos.append(entry)
            elif dias <= 7:
                urgentes.append(entry)
            else:
                proximos.append(entry)

        if not (vencidos or urgentes or proximos):
            return True, {'mensaje': 'Sin equipos vencidos ni próximos · sin alerta'}, 0

        # Notif tiered: vencidos o urgentes (≤7d) son críticos · próximos preventivos
        # Solo enviar push si hay algo crítico o muchos próximos
        if vencidos or urgentes or len(proximos) >= 3:
            try:
                from blueprints.notif import push_notif_multi
                destinatarios = ['controlcalidad.espagiria','aseguramiento.espagiria',
                                 'laura','miguel','yuliel','sebastian']
                if vencidos:
                    titulo = f'⛔ {len(vencidos)} equipos VENCIDOS · NO USAR'
                elif urgentes:
                    titulo = f'⏰ {len(urgentes)} equipos vencen ≤7d · agendar calibración YA'
                else:
                    titulo = f'📅 {len(proximos)} equipos próximos a vencer (8-30d)'
                cuerpo_lines = []
                for v in vencidos[:5]:
                    cuerpo_lines.append(f'⛔ {v["codigo"]} · vence hace {abs(v["dias"])}d')
                for u in urgentes[:5]:
                    cuerpo_lines.append(f'⏰ {u["codigo"]} · vence en {u["dias"]}d (T-7)')
                for p in proximos[:5]:
                    cuerpo_lines.append(f'📅 {p["codigo"]} · vence en {p["dias"]}d')
                push_notif_multi(
                    destinatarios, 'capa', titulo,
                    body='\n'.join(cuerpo_lines),
                    link='/calidad', remitente='cron-equipos',
                    importante=bool(vencidos or urgentes),
                )
            except Exception as e:
                log.warning('equipos_vencimientos push_notif fallo: %s', e)

        return True, {
            'vencidos': len(vencidos),
            'urgentes_7d': len(urgentes),
            'proximos_30d': len(proximos),
        }, 0


def job_desv_plazos(app):
    """ASG-PRO-001 · diario 8:00 · alerta desviaciones en plazo vencido.

    Plazos según ASG-PRO-001:
    - crítica sin clasificar > 1 día → alerta
    - cualquiera sin investigar > 5 días → alerta
    - CAPA vencido > 0 días → alerta crítica
    """
    with app.app_context():
        from database import get_db
        conn = get_db(); c = conn.cursor()
        try:
            sin_clasif = c.execute("""
                SELECT codigo, descripcion FROM desviaciones
                WHERE estado='detectada'
                  AND date(fecha_deteccion) <= date('now', '-1 day')
                LIMIT 30
            """).fetchall()
            sin_invest = c.execute("""
                SELECT codigo, clasificacion, descripcion FROM desviaciones
                WHERE estado IN ('clasificada')
                  AND date(fecha_deteccion) <= date('now', '-5 days')
                LIMIT 30
            """).fetchall()
            capa_vencido = c.execute("""
                SELECT codigo, capa_responsable, capa_fecha_limite FROM desviaciones
                WHERE estado IN ('capa_propuesto','capa_implementado')
                  AND capa_fecha_limite IS NOT NULL
                  AND date(capa_fecha_limite) < date('now')
                LIMIT 30
            """).fetchall()
        except Exception as e:
            log.warning('desv_plazos read fallo: %s', e)
            return False, {'error': str(e)[:200]}, 0

        if not sin_clasif and not sin_invest and not capa_vencido:
            return True, {'mensaje': 'Sin desviaciones en plazo vencido'}, 0

        try:
            from blueprints.notif import push_notif_multi
            destinatarios = ['controlcalidad.espagiria','aseguramiento.espagiria',
                             'laura','sebastian']
            partes = []
            if sin_clasif:
                partes.append(f'⏰ {len(sin_clasif)} sin clasificar (>1d)')
                for r in sin_clasif[:3]: partes.append(f'  · {r[0]}: {(r[1] or "")[:60]}')
            if sin_invest:
                partes.append(f'🔍 {len(sin_invest)} sin investigar (>5d)')
                for r in sin_invest[:3]: partes.append(f'  · {r[0]} ({r[1] or "?"}): {(r[2] or "")[:60]}')
            if capa_vencido:
                partes.append(f'⛔ {len(capa_vencido)} CAPA VENCIDO')
                for r in capa_vencido[:3]: partes.append(f'  · {r[0]}: resp {r[1]} · venció {r[2]}')
            push_notif_multi(
                destinatarios, 'capa',
                f'⚠ Desviaciones en plazo vencido (ASG-PRO-001)',
                body='\n'.join(partes),
                link='/aseguramiento', remitente='cron-desv',
                importante=bool(capa_vencido or len(sin_clasif) >= 3),
            )
        except Exception as e:
            log.warning('desv_plazos notif fallo: %s', e)
        return True, {
            'sin_clasificar_1d': len(sin_clasif),
            'sin_investigar_5d': len(sin_invest),
            'capa_vencido': len(capa_vencido),
        }, 0


def job_cambios_plazos(app):
    """ASG-PRO-007 · diario 8:30 · alerta control de cambios en plazo vencido.

    Plazos:
    - solicitado sin evaluar > 5 días → alerta
    - aprobado sin notificar INVIMA (cuando aplica) > 3 días → alerta crítica
    - aprobado/en_implementacion sin implementar > 30 días → alerta
    - implementado sin cerrar > 15 días → alerta (verificación efectividad pendiente)
    """
    with app.app_context():
        from database import get_db
        conn = get_db(); c = conn.cursor()
        try:
            sin_evaluar = c.execute("""
                SELECT codigo, titulo, solicitado_por FROM control_cambios
                WHERE estado='solicitado'
                  AND date(fecha_solicitud) <= date('now', '-5 days')
                LIMIT 30
            """).fetchall()
            invima_pendiente = c.execute("""
                SELECT codigo, titulo, aprobado_at FROM control_cambios
                WHERE estado IN ('aprobado','en_implementacion')
                  AND requiere_invima=1
                  AND notificacion_invima_at IS NULL
                  AND date(aprobado_at) <= date('now', '-3 days')
                LIMIT 30
            """).fetchall()
            sin_implementar = c.execute("""
                SELECT codigo, titulo, responsable_implementacion, fecha_implementacion_propuesta
                FROM control_cambios
                WHERE estado IN ('aprobado','en_implementacion')
                  AND date(aprobado_at) <= date('now', '-30 days')
                  AND (requiere_invima=0 OR notificacion_invima_at IS NOT NULL)
                LIMIT 30
            """).fetchall()
            sin_cerrar = c.execute("""
                SELECT codigo, titulo, implementado_por, implementado_at
                FROM control_cambios
                WHERE estado='implementado'
                  AND date(implementado_at) <= date('now', '-15 days')
                LIMIT 30
            """).fetchall()
        except Exception as e:
            log.warning('cambios_plazos read fallo: %s', e)
            return False, {'error': str(e)[:200]}, 0

        if not (sin_evaluar or invima_pendiente or sin_implementar or sin_cerrar):
            return True, {'mensaje': 'Sin cambios en plazo vencido'}, 0

        try:
            from blueprints.notif import push_notif_multi
            destinatarios = ['controlcalidad.espagiria','aseguramiento.espagiria',
                             'laura','sebastian']
            partes = []
            if sin_evaluar:
                partes.append(f'⏰ {len(sin_evaluar)} solicitudes sin evaluar (>5d)')
                for r in sin_evaluar[:3]: partes.append(f'  · {r[0]}: {(r[1] or "")[:60]} · sol {r[2]}')
            if invima_pendiente:
                partes.append(f'🚨 {len(invima_pendiente)} aprobados sin notificar INVIMA (>3d)')
                for r in invima_pendiente[:3]: partes.append(f'  · {r[0]}: {(r[1] or "")[:60]}')
            if sin_implementar:
                partes.append(f'🔧 {len(sin_implementar)} aprobados sin implementar (>30d)')
                for r in sin_implementar[:3]:
                    fec = r[3] or 'sin fecha'
                    partes.append(f'  · {r[0]}: resp {r[2] or "?"} · prop {fec}')
            if sin_cerrar:
                partes.append(f'✅ {len(sin_cerrar)} implementados sin cerrar (>15d)')
                for r in sin_cerrar[:3]: partes.append(f'  · {r[0]}: impl {r[3]}')
            push_notif_multi(
                destinatarios, 'capa',
                f'⚠ Control de cambios en plazo vencido (ASG-PRO-007)',
                body='\n'.join(partes),
                link='/aseguramiento', remitente='cron-cambios',
                importante=bool(invima_pendiente),
            )
        except Exception as e:
            log.warning('cambios_plazos notif fallo: %s', e)
        return True, {
            'sin_evaluar_5d': len(sin_evaluar),
            'invima_pendiente_3d': len(invima_pendiente),
            'sin_implementar_30d': len(sin_implementar),
            'sin_cerrar_15d': len(sin_cerrar),
        }, 0


def job_quejas_plazos(app):
    """ASG-PRO-013 · diario 9:00 · alerta quejas en plazo vencido.

    Plazos:
    - nuevas sin triar > 1 día → alerta
    - crítica/impacto_salud sin responder > 2 días → CRÍTICA
    - cualquiera sin responder > 7 días → alerta
    - respondidas sin cerrar > 14 días → alerta
    """
    with app.app_context():
        from database import get_db
        conn = get_db(); c = conn.cursor()
        try:
            sin_triar = c.execute("""
                SELECT codigo, cliente_nombre, tipo_queja FROM quejas_clientes
                WHERE estado='nueva'
                  AND date(fecha_recepcion) <= date('now', '-1 day')
                LIMIT 30
            """).fetchall()
            criticas_lentas = c.execute("""
                SELECT codigo, cliente_nombre, tipo_queja FROM quejas_clientes
                WHERE estado IN ('en_triaje','en_investigacion')
                  AND (severidad='critica' OR impacto_salud=1)
                  AND date(fecha_recepcion) <= date('now', '-2 day')
                LIMIT 30
            """).fetchall()
            sin_responder = c.execute("""
                SELECT codigo, cliente_nombre, severidad FROM quejas_clientes
                WHERE estado IN ('en_triaje','en_investigacion')
                  AND (severidad IS NULL OR severidad NOT IN ('critica'))
                  AND impacto_salud=0
                  AND date(fecha_recepcion) <= date('now', '-7 day')
                LIMIT 30
            """).fetchall()
            sin_cerrar = c.execute("""
                SELECT codigo, cliente_nombre, respondido_at FROM quejas_clientes
                WHERE estado='respondida'
                  AND date(respondido_at) <= date('now', '-14 day')
                LIMIT 30
            """).fetchall()
        except Exception as e:
            log.warning('quejas_plazos read fallo: %s', e)
            return False, {'error': str(e)[:200]}, 0

        if not (sin_triar or criticas_lentas or sin_responder or sin_cerrar):
            return True, {'mensaje': 'Sin quejas en plazo vencido'}, 0

        try:
            from blueprints.notif import push_notif_multi
            destinatarios = ['controlcalidad.espagiria','aseguramiento.espagiria',
                             'laura','sebastian']
            partes = []
            if sin_triar:
                partes.append(f'⏰ {len(sin_triar)} nuevas sin triar (>1d)')
                for r in sin_triar[:3]: partes.append(f'  · {r[0]}: {(r[1] or "")[:30]} · {r[2] or "?"}')
            if criticas_lentas:
                partes.append(f'🚨 {len(criticas_lentas)} CRÍTICAS sin responder (>2d)')
                for r in criticas_lentas[:3]: partes.append(f'  · {r[0]}: {(r[1] or "")[:30]} · {r[2] or "?"}')
            if sin_responder:
                partes.append(f'📞 {len(sin_responder)} sin responder (>7d)')
                for r in sin_responder[:3]: partes.append(f'  · {r[0]}: {(r[1] or "")[:30]}')
            if sin_cerrar:
                partes.append(f'✅ {len(sin_cerrar)} respondidas sin cerrar (>14d)')
                for r in sin_cerrar[:3]: partes.append(f'  · {r[0]}: {(r[1] or "")[:30]} · resp {r[2]}')
            push_notif_multi(
                destinatarios, 'capa',
                f'⚠ Quejas de cliente en plazo vencido (ASG-PRO-013)',
                body='\n'.join(partes),
                link='/aseguramiento', remitente='cron-quejas',
                importante=bool(criticas_lentas),
            )
        except Exception as e:
            log.warning('quejas_plazos notif fallo: %s', e)
        return True, {
            'sin_triar_1d': len(sin_triar),
            'criticas_lentas_2d': len(criticas_lentas),
            'sin_responder_7d': len(sin_responder),
            'sin_cerrar_14d': len(sin_cerrar),
        }, 0


def job_recalls_plazos(app):
    """ASG-PRO-004 · diario 9:30 · alerta recalls en plazo vencido.

    Plazos críticos (Resolución 2214/2021):
    - sin clasificar > 12h → CRÍTICA (todo recall debe clasificarse rápido)
    - Clase I sin INVIMA notificado > 1 día → SUPER CRÍTICA (regulatoria <24h)
    - cualquier clase sin INVIMA > 5 días → CRÍTICA
    - sin completar recolección > 30 días → alerta
    """
    with app.app_context():
        from database import get_db
        conn = get_db(); c = conn.cursor()
        try:
            sin_clasificar = c.execute("""
                SELECT codigo, producto, lotes_afectados FROM recalls
                WHERE estado='iniciado'
                  AND datetime(creado_en) <= datetime('now', '-12 hours')
                LIMIT 30
            """).fetchall()
            clase_I_sin_invima = c.execute("""
                SELECT codigo, producto FROM recalls
                WHERE clase_recall='clase_I'
                  AND notificacion_invima_at IS NULL
                  AND estado NOT IN ('cerrado','cancelado')
                  AND datetime(clasificado_at) <= datetime('now', '-1 day')
                LIMIT 30
            """).fetchall()
            sin_invima_5d = c.execute("""
                SELECT codigo, producto, clase_recall FROM recalls
                WHERE clase_recall IN ('clase_II','clase_III')
                  AND notificacion_invima_at IS NULL
                  AND estado NOT IN ('cerrado','cancelado')
                  AND date(clasificado_at) <= date('now', '-5 day')
                LIMIT 30
            """).fetchall()
            sin_recolectar_30d = c.execute("""
                SELECT codigo, producto, cantidad_recolectada, cantidad_distribuida
                FROM recalls
                WHERE estado IN ('distribuidores_notificados','en_recoleccion')
                  AND date(notificacion_invima_at) <= date('now', '-30 day')
                LIMIT 30
            """).fetchall()
        except Exception as e:
            log.warning('recalls_plazos read fallo: %s', e)
            return False, {'error': str(e)[:200]}, 0

        if not (sin_clasificar or clase_I_sin_invima or sin_invima_5d or sin_recolectar_30d):
            return True, {'mensaje': 'Sin recalls en plazo vencido'}, 0

        try:
            from blueprints.notif import push_notif_multi
            destinatarios = ['controlcalidad.espagiria','aseguramiento.espagiria',
                             'sebastian']
            partes = []
            if sin_clasificar:
                partes.append(f'⏰ {len(sin_clasificar)} recalls sin clasificar (>12h)')
                for r in sin_clasificar[:3]: partes.append(f'  · {r[0]}: {(r[1] or "")[:30]} / {(r[2] or "")[:30]}')
            if clase_I_sin_invima:
                partes.append(f'🚨🚨 {len(clase_I_sin_invima)} CLASE I SIN INVIMA NOTIFICADO (>24h regulatoria)')
                for r in clase_I_sin_invima[:3]: partes.append(f'  · {r[0]}: {(r[1] or "")[:40]}')
            if sin_invima_5d:
                partes.append(f'🚨 {len(sin_invima_5d)} recalls sin INVIMA notificado (>5d)')
                for r in sin_invima_5d[:3]: partes.append(f'  · {r[0]} ({r[2]}): {(r[1] or "")[:30]}')
            if sin_recolectar_30d:
                partes.append(f'📦 {len(sin_recolectar_30d)} sin completar recolección (>30d)')
                for r in sin_recolectar_30d[:3]:
                    pct = ''
                    if r[3]:
                        try: pct = f' ({int((r[2] or 0) / r[3] * 100)}%)'
                        except Exception: pass
                    partes.append(f'  · {r[0]}: {(r[1] or "")[:30]} · {(r[2] or 0)}/{(r[3] or "?")}{pct}')
            push_notif_multi(
                destinatarios, 'capa',
                f'🚨 RECALLS en plazo vencido (ASG-PRO-004)',
                body='\n'.join(partes),
                link='/aseguramiento', remitente='cron-recalls',
                importante=True,  # SIEMPRE importante para recalls
            )
        except Exception as e:
            log.warning('recalls_plazos notif fallo: %s', e)
        return True, {
            'sin_clasificar_12h': len(sin_clasificar),
            'clase_I_sin_invima_24h': len(clase_I_sin_invima),
            'sin_invima_5d': len(sin_invima_5d),
            'sin_recolectar_30d': len(sin_recolectar_30d),
        }, 0


def job_auto_sc_urgente(app):
    """Cron lunes 12:00: SCs urgentes."""
    with app.app_context():
        from database import get_db
        from blueprints.auto_plan import _calcular_auto_sc
        conn = get_db()
        plan = _calcular_auto_sc(conn, horizontes_dias=(14, 30), modo='urgente')
        return True, {'kpis': plan.get('kpis', {})}, 0


def _loop_multi_cron(app):
    """Loop cada 5 min revisa schedule de jobs y ejecuta los que apliquen.

    Sebastián 1-may-2026 audit zero-error: incorporar lock distribuido
    `cron_locks` para prevenir doble ejecución cuando hay >1 worker.
    """
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
                    if not _adquirir_lock_cron(conn, job_name):
                        log.info(f'[multi-cron] {job_name}: lock ocupado · otro worker ejecutando')
                        continue
                    fn = globals().get(callable_name)
                    if not fn:
                        log.warning(f'[multi-cron] {job_name}: callable {callable_name} no existe')
                        _liberar_lock_cron(conn, job_name)
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
                    finally:
                        _liberar_lock_cron(conn, job_name)
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
