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
from database import db_connect
from flask import current_app

log = logging.getLogger('auto_plan_jobs')

# Hora del cron (Colombia America/Bogota)
HORA_CRON = 7   # 07:00
DIAS_CRON = (0, 1, 2, 3, 4)  # lunes a viernes


# ───────────────────────────────────────────────────────────────────────
# Email engine — usa SistemaNotificaciones existente del proyecto
# ───────────────────────────────────────────────────────────────────────

def _shopify_created_at_bogota(created_at_str):
    """SHOPIFY-FIX · 22-may-2026 · Bug #7 audit · convertir TZ Shopify→Bogotá.

    Shopify devuelve created_at en ISO UTC (ej '2026-05-22T03:30:00Z').
    Si hacemos [:10] sin convertir, venta de hoy 22:30 Bogotá queda guardada
    como AYER UTC (porque UTC ya pasó medianoche). Al filtrar `WHERE date >= N`
    esa venta cae fuera de ventana cuando NO debería.

    Solución: parsear ISO + convertir a TZ Bogotá (UTC-5) + extraer date.
    """
    if not created_at_str:
        return ''
    try:
        from datetime import datetime as _dt2, timezone as _tz, timedelta as _td2
        # ISO con Z o +00:00 · normalizar
        s = (created_at_str or '').replace('Z', '+00:00')
        dt = _dt2.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=_tz.utc)
        bogota = _tz(_td2(hours=-5))
        return dt.astimezone(bogota).strftime('%Y-%m-%d')
    except Exception:
        # Fallback: si parse falla, usar slice [:10] (legacy behavior)
        return (created_at_str or '')[:10]


def _enviar_email_async(asunto, html, destinos):
    """Envía email en thread separado. Nunca falla.

    Sebastián 1-may-2026 audit zero-error: el thread loguea el resultado
    real del envío. Antes silencioso · si SMTP fallaba nadie sabía.

    FIX · 22-may-2026 · Bug #5 audit Crons · check EMAIL_PASSWORD antes de thread
    · Antes: si pwd vacío, thread creado → notif._enviar_email loguea WARN y vuelve
    · Cada cron mensual creaba 5-10 threads que no servían · log noise + zombies
    · Ahora: short-circuit ANTES de crear thread si no hay pwd configurado
    """
    if not destinos:
        return False
    if not os.environ.get('EMAIL_PASSWORD'):
        log.debug('[auto-plan-email] skip · EMAIL_PASSWORD no configurado · asunto=%r', asunto[:60])
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
                  AND fecha_programada >= date('now', '-5 hours')
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
                        "UPDATE auto_plan_cron_state SET ultima_ejecucion_at=datetime('now', '-5 hours'), errores_consecutivos=0 WHERE id=1"
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
    # ⭐ Resumen ejecutivo nocturno · 19:00 todos los días · Sebastián +
    #   Alejandro reciben campana con resumen del día (OLA 3 IA 20-may-2026)
    ('resumen_ejecutivo_noche', 19, 0, None, None,                'job_resumen_ejecutivo_noche'),
    # ⭐ Compras N3 · reconciliar SOLs influencer >60d sin pago · diario 9:00
    ('reconciliar_influencer_60d', 9, 0, None, None,              'job_reconciliar_influencer_60d'),
    # Diarios
    ('sync_stock_shopify',    5, 30, None, None,                'job_sync_stock_shopify_diario'),
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
    # ⭐ Direccion Tecnica · diario 7:45 · alerta INVIMA + SGD próximos a vencer
    ('tecnica_vencimientos',  7, 45, None, None,                'job_tecnica_vencimientos'),
    # ⭐ Planta · diario 7:50 · marca VENCIDO en lotes con fecha_venc pasada (INVIMA)
    ('marcar_vencidos',       7, 50, None, None,                'job_marcar_vencidos'),
    # Sebastián 21-may-2026 · auto-reparar fórmulas con material_id huérfano.
    # Causa raíz: cuando se unifican MPs, formula_items.material_id puede
    # quedar apuntando a un código viejo sin lotes. El error "Hay 0g" cuando
    # SÍ hay stock viene de aquí. Cron diario 4:00 AM repara automático.
    ('auto_reparar_huerfanas',4,  0, None, None,                'job_auto_reparar_huerfanas'),
    # ⭐ Auto-normalizar abbreviaturas en fórmulas · 4:30 AM (después huérfanas)
    # SAP → Sodium Ascorbyl Phosphate · HA → Hyaluronic Acid · etc.
    ('auto_normalizar_formulas', 4, 30, None, None,             'job_auto_normalizar_formulas'),
    # PQR SLA · Ley 1755/2015 CO · diario 8:15 AM
    ('pqr_sla_vencido',       8, 15, None, None,                'job_pqr_sla_vencido'),
    # MEE drift sync · cache vs SUM(movimientos_mee) · diario 3:00 AM
    # Hasta migrar a stock=SUM canonical, este cron repara drift silencioso
    ('mee_drift_sync',        3,  0, None, None,                'job_mee_drift_sync'),
    # ⭐ Mailbox factura proveedor IMAP · diario 7:15 AM
    # Lee inbox compras@hhagroup.co, extrae adjuntos (PDF/JPG/PNG), guarda
    # como factura_proveedor en pagos_oc · matching automático con OC.
    # SOLO corre si IMAP_HOST + IMAP_USER + IMAP_PASSWORD configurados.
    ('mailbox_factura_proveedor', 7, 15, None, None,            'job_mailbox_factura_proveedor'),
    # ⭐ Zero-Error · diario 8:00 · validación profunda matemática (8 checks)
    ('validacion_profunda',   8,  0, None, None,                'job_validacion_profunda'),
    # ⭐ Animus · L-V 8:00am · asignar 5 SKUs para conteo fisico a Daniela
    ('animus_conteo_diario',  8,  0, [0,1,2,3,4], None,         'job_animus_conteo_diario'),
    # ⭐ Aseguramiento · diario 8:00 · alerta desviaciones en plazos críticos (ASG-PRO-001)
    ('desv_plazos',           8,  0, None, None,                'job_desv_plazos'),
    # ⭐ Aseguramiento · diario 8:30 · alerta control de cambios en plazos vencidos (ASG-PRO-007)
    ('cambios_plazos',        8, 30, None, None,                'job_cambios_plazos'),
    # ⭐ Aseguramiento · diario 9:00 · alerta quejas sin triar/responder/cerrar (ASG-PRO-013)
    ('quejas_plazos',         9,  0, None, None,                'job_quejas_plazos'),
    # ⭐ Aseguramiento · diario 9:30 · alerta recalls sin clasificar/notificar (ASG-PRO-004)
    ('recalls_plazos',        9, 30, None, None,                'job_recalls_plazos'),
    # ⭐ CEO · LUNES 7:30 · executive brief con health snapshot + KPIs semanales
    ('weekly_executive',      7, 30, [0],  None,                'job_weekly_executive_email'),
    # ⭐ CEO · DÍA 1 8:00 · reporte financiero mensual · P&L + MoM + tops
    ('monthly_financial',     8,  0, None, [1],                 'job_monthly_financial_summary'),
    # ⭐ Planta · diario 6:30am · detector de drift inventario MP/MEE (cero sesgo continuo)
    ('drift_detector_inv',    6, 30, None, None,                'job_drift_detector_inventario'),
    # ⭐ Watcher · zero-error sprint día 4 · pega health/critical-paths cada hora
    # Si algún check status=='critical' → mail a EMAIL_GERENCIA.
    # Schedule: cada hora a :07 (offset para no chocar con :00 jobs).
    # Cada hora usa job_name distinto (watcher_health_HH) porque el dedup
    # `_ya_ejecutado_hoy` agrupa por job_name. Todas llaman al mismo callable.
] + [
    (f'watcher_health_{h:02d}', h, 7, None, None, 'job_watcher_health')
    for h in range(24)
]


def _es_hora_de(ahora, hora, minuto, dias_sem, dias_mes):
    """¿La fecha 'ahora' coincide con el schedule? (ventana 5 min unidireccional).

    FIX · 22-may-2026 · Bug #2 audit Crons.
    Antes: `abs(ahora.minute - minuto) > 5` → ventana de 10 min (5 antes + 5 después).
    Si minuto=0, matcheaba a 12:00 y 12:55 (hour=11) o 12:00 y 12:05 → doble disparo.
    Ahora: solo después del horario configurado · ventana 0..4 min · single trigger.
    Para minuto=0: matchea 12:00, 12:01, 12:02, 12:03, 12:04 (todos hour=12). OK.
    """
    if dias_sem is not None and ahora.weekday() not in dias_sem:
        return False
    if dias_mes is not None and ahora.day not in dias_mes:
        return False
    if ahora.hour != hora:
        return False
    delta = ahora.minute - minuto
    if delta < 0 or delta > 4:
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
              AND date(ejecutado_at) = date('now', '-5 hours')
            LIMIT 1
        """, (job_name,)).fetchone()
        if row_ok: return True
        # ¿Fallo reciente (<retry_si_fallo_horas)?
        row_fail = conn.execute("""
            SELECT 1 FROM cron_jobs_runs
            WHERE job_name = ? AND ok = 0
              AND ejecutado_at >= datetime('now', '-5 hours', '-' || ? || ' hours')
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
        # FIX · 22-may-2026 · Bug #10 audit Crons · PG date multi-arg fail
        # · Antes: datetime('now','-5 hours','-N hours') multi-arg NO funciona PG
        # · Locks huérfanos quedaban permanentes en PG · cron bloqueado por siempre
        # · Ahora: cutoff calculado en Python · pasado como param
        from datetime import datetime as _dt2, timedelta as _td2
        cutoff = (_dt2.now() - _td2(hours=ttl_horas + 5)).strftime('%Y-%m-%d %H:%M:%S')
        bog_now = (_dt2.now() - _td2(hours=5)).strftime('%Y-%m-%d %H:%M:%S')
        # Limpiar locks vencidos antes de intentar reclamar (PG-safe)
        conn.execute("DELETE FROM cron_locks WHERE locked_at < ?", (cutoff,))
        cur = conn.execute(
            "INSERT INTO cron_locks (job_name, locked_at, locked_by) "
            "VALUES (?, ?, 'multi-cron') "
            "ON CONFLICT(job_name) DO NOTHING",
            (job_name, bog_now),
        )
        conn.commit()
        # cur.rowcount no funciona uniformly entre PG y SQLite con ON CONFLICT
        # · verificar con SELECT post-INSERT
        row = conn.execute(
            "SELECT locked_at, locked_by FROM cron_locks WHERE job_name=?",
            (job_name,),
        ).fetchone()
        return bool(row and row[1] == 'multi-cron' and row[0] == bog_now)
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
            VALUES (?, datetime('now', '-5 hours'), ?, ?, ?, ?)
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
                    VALUES (?, 1, datetime('now', '-5 hours'), ?)
                    ON CONFLICT(job_name) DO UPDATE SET
                      errores_consecutivos = errores_consecutivos + 1,
                      ultimo_error_at = datetime('now', '-5 hours'),
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
                        conn.execute("UPDATE cron_jobs_health SET notificado_at=datetime('now', '-5 hours') WHERE job_name=?",
                                       (job_name,))
        except Exception as _e:
            log.warning('cron_jobs_health update %s fallo: %s', job_name, _e)
        conn.commit()
    except Exception as e:
        log.warning(f'[multi-cron] no se pudo registrar {job_name}: {e}')


def job_sync_stock_shopify_diario(app):
    """Sync Shopify stock (inventory_quantity) → tabla stock_pt.

    Sebastian 12-may-2026: 'quisiera un sync automatico diario asi sabemos
    realidades'. Antes el stock solo se actualizaba al clickear el boton
    '🔄 Sync Shopify' en el panel · ahora corre diario 5:30am Colombia.

    Replica logica del endpoint /api/programacion/sync-stock-shopify:
      - Pull products.json paginado (Link header rel=next).
      - Marca snapshots SHOPIFY-* anteriores como Ajustado.
      - INSERT por variant con stock>0 con lote_produccion='SHOPIFY-<hoy>'.

    Inventory_quantity de Shopify = ON HAND (incluye committed). Fix futuro
    para usar AVAILABLE pendiente (requiere segunda llamada a inventory_levels).
    """
    with app.app_context():
        from database import get_db
        import urllib.request as _ur
        import urllib.error as _uerr
        import json as _json
        from datetime import datetime as _dt

        conn = get_db()

        def _cfg(clave):
            r = conn.execute("SELECT valor FROM animus_config WHERE clave=?", (clave,)).fetchone()
            return r[0] if r else None

        token = _cfg('shopify_token')
        shop = _cfg('shopify_shop')
        if not token or not shop:
            return False, {'error': 'Shopify no configurado en animus_config'}, 1

        sku_map = {}
        for row in conn.execute(
            "SELECT sku, producto_nombre FROM sku_producto_map WHERE activo=1"
        ).fetchall():
            sku_map[str(row[0] or '').strip().upper()] = str(row[1] or '').strip()

        all_variants = []
        url = 'https://' + shop + '/admin/api/2024-01/products.json?limit=250&fields=id,title,variants'
        while url:
            req = _ur.Request(url, headers={'X-Shopify-Access-Token': token})
            try:
                with _ur.urlopen(req, timeout=20) as r:
                    data = _json.loads(r.read())
                    link_header = r.headers.get('Link', '')
            except _uerr.HTTPError as e:
                body = e.read().decode('utf-8', errors='replace')[:200]
                return False, {'error': f'Shopify HTTP {e.code} — {body}'}, 1
            except Exception as e:
                return False, {'error': f'Error red Shopify: {e}'}, 1

            for product in data.get('products', []):
                title = str(product.get('title', '') or '').strip()
                for variant in product.get('variants', []):
                    sku_raw = str(variant.get('sku', '') or '').strip().upper()
                    qty = int(variant.get('inventory_quantity', 0) or 0)
                    iid = variant.get('inventory_item_id')  # para fix D Available
                    all_variants.append({
                        'sku': sku_raw, 'titulo': title,
                        'inv_qty': qty, 'inv_item_id': iid,
                    })

            next_url = None
            for part in link_header.split(','):
                if 'rel="next"' in part:
                    s = part.find('<') + 1
                    e2 = part.find('>')
                    if s > 0 and e2 > s:
                        next_url = part[s:e2].strip()
            url = next_url

        if not all_variants:
            return False, {'error': 'Shopify no devolvio productos'}, 1

        # Sebastián 12-may-2026 · fix D: AVAILABLE en lugar de ON HAND.
        # Reusa helper _fetch_shopify_available del blueprint programacion.
        try:
            from blueprints.programacion import _fetch_shopify_available
        except Exception:
            try:
                from .programacion import _fetch_shopify_available
            except Exception:
                _fetch_shopify_available = None

        avail_map = {}
        if _fetch_shopify_available is not None:
            inv_item_ids = [v.get('inv_item_id') for v in all_variants if v.get('inv_item_id')]
            try:
                avail_map = _fetch_shopify_available(token, shop, inv_item_ids) or {}
            except Exception:
                avail_map = {}
        used_available = bool(avail_map)

        conn.execute("UPDATE stock_pt SET estado='Ajustado' WHERE lote_produccion LIKE 'SHOPIFY-%'")
        synced = 0
        skipped = 0
        today = _dt.now().strftime('%Y-%m-%d')
        for v in all_variants:
            sku = v['sku']
            iid = v.get('inv_item_id')
            if iid and iid in avail_map:
                qty = max(int(avail_map[iid]), 0)
                fuente = 'Available'
            else:
                qty = int(v['inv_qty'] or 0)
                fuente = 'On hand'
            if not sku:
                skipped += 1
                continue
            # SHOPIFY-FIX · 22-may-2026 · Bug #4 audit · NO skipear SKU agotado
            # · Antes: qty<=0 → skip · _velocidad lookup vía sku_producto_map se rompía
            # · Ahora: insert qty=0 con estado='Agotado' · señal "existe pero sin stock"
            producto = sku_map.get(sku)
            if not producto:
                prefix = sku.split('-')[0] if '-' in sku else sku[:6]
                producto = sku_map.get(prefix) or v['titulo']
            estado_pt = 'Disponible' if qty > 0 else 'Agotado'
            qty_safe = max(qty, 0)
            conn.execute(
                "INSERT INTO stock_pt (sku,descripcion,lote_produccion,fecha_produccion,unidades_inicial,unidades_disponible,precio_base,empresa,estado,observaciones) VALUES (?,?,?,?,?,?,0,'ANIMUS',?,?)",
                (sku, producto, 'SHOPIFY-' + today, today, qty_safe, qty_safe, estado_pt, f'Sync Shopify CRON ({fuente})')
            )
            synced += 1

        conn.commit()
        return True, {
            'synced': synced,
            'skipped_zero': skipped,
            'total_variantes': len(all_variants),
            'usado_available': used_available,
        }, 0


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
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,datetime('now', '-5 hours'))
            """, (str(o["id"]), o.get("name",""), o.get("email",""),
                  float(o.get("total_price",0)), o.get("currency","COP"),
                  o.get("fulfillment_status",""), o.get("financial_status",""),
                  items_sku, total_uds,
                  addr.get("city",""), addr.get("country_code","CO"),
                  _shopify_created_at_bogota(o.get("created_at",""))))
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
                  AND date(fecha) >= date('now', '-5 hours', '-30 days')
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
                # Fix #5 · 21-may-2026 · categoria='Material de Empaque'
                # (antes 'Servicios' → invisible en tab Planta de Catalina).
                # La serigrafía/tampografía D-20 es decoración de envase ·
                # conceptualmente material de empaque · debe aparecer junto
                # a las MPs y empaques que Catalina maneja en Planta.
                c.execute("""
                    INSERT INTO solicitudes_compra
                      (numero, fecha, estado, solicitante, urgencia, observaciones,
                       area, empresa, categoria, tipo, fecha_requerida, valor)
                    VALUES (?, ?, 'Pendiente', 'cron-d20-auto', 'Alta', ?, 'Produccion',
                            'Espagiria', 'Material de Empaque', 'Servicio decoracion', ?, ?)
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
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,datetime('now', '-5 hours'))
                    """, (str(o["id"]), o.get("name",""), o.get("email",""),
                          float(o.get("total_price",0)), o.get("currency","COP"),
                          o.get("fulfillment_status",""), o.get("financial_status",""),
                          items_sku, total_uds,
                          addr.get("city",""), addr.get("country_code","CO"),
                          _shopify_created_at_bogota(o.get("created_at",""))))
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
                      AND date(l.fecha) >= date('now', '-5 hours')
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
                  SET bloqueado_at = datetime('now', '-5 hours'),
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
                c.execute("UPDATE auto_plan_cron_state SET habilitado=1, notas='Self-heal auto-enable', activado_por='self-heal', activado_at=datetime('now', '-5 hours') WHERE id=1")
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
                      AND date(l.fecha) >= date('now', '-5 hours')
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
            # FIX · 22-may-2026 · Bug #7 audit Crons · 30→90d preservar patrón mensual
            # · Antes: cron_jobs_runs borrado a 30d perdía contexto auto_sc_mensual
            # · Ahora: 90d retención · permite detectar fallos crónicos mensuales
            # · date multi-arg solo SQLite · usar timedelta Python para PG-compat
            from datetime import datetime as _dt2, timedelta as _td2
            _cutoff_runs = (_dt2.now() - _td2(days=90, hours=5)).strftime('%Y-%m-%d')
            n_runs = c.execute(
                "DELETE FROM cron_jobs_runs WHERE date(ejecutado_at) < ?",
                (_cutoff_runs,),
            ).rowcount
        except Exception as e:
            log.warning('cleanup cron_jobs_runs fallo: %s', e)
            errores.append(f'cron_jobs_runs:{e}')
        try:
            n_apr = c.execute("DELETE FROM auto_plan_runs WHERE date(ejecutado_at) < date('now', '-5 hours', '-90 days')").rowcount
        except Exception as e:
            log.warning('cleanup auto_plan_runs fallo: %s', e)
            errores.append(f'auto_plan_runs:{e}')
        try:
            n_aal = c.execute("DELETE FROM auto_asignacion_log WHERE date(ejecutado_at) < date('now', '-5 hours', '-90 days')").rowcount
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
                WHERE date(fecha) = date('now', '-5 hours')
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
                  AND date(fecha_proxima) <= date('now', '-5 hours', '+30 days')
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


def job_tecnica_vencimientos(app):
    """Direccion Tecnica · diario 7:45 · alerta INVIMA + SGD próximos a vencer.

    Sebastian 2-may-2026: el director técnico necesita saber con tiempo
    qué registros INVIMA y qué SOPs hay que renovar/revisar.

    INVIMA tiering:
      - vencidos (días < 0)  → CRÍTICO · INVIMA tiene poder de decomiso
      - urgentes (≤30d)      → URGENTE · empezar trámite renovación
      - próximos (31-90d)    → preventivo · planear

    SGD tiering (revisión periódica):
      - vencidos (días < 0)  → CRÍTICO · auditoría INVIMA puede observar
      - urgentes (≤7d)
      - próximos (8-30d)

    Idempotente: solo notifica si hay algo crítico/urgente, o muchos próximos.
    """
    with app.app_context():
        from database import get_db
        from datetime import date as _date
        conn = get_db(); c = conn.cursor()
        hoy = _date.today()

        # ─── INVIMA ─────────────────────────────────────────────────────
        try:
            inv_rows = c.execute("""
                SELECT id, producto, num_registro, fecha_vencimiento
                  FROM registros_invima
                 WHERE LOWER(COALESCE(estado,'')) = 'vigente'
                   AND COALESCE(fecha_vencimiento,'') != ''
                   AND date(fecha_vencimiento) <= date('now', '-5 hours', '+90 days')
                 ORDER BY fecha_vencimiento ASC
                 LIMIT 200
            """).fetchall()
        except Exception as e:
            log.warning('tecnica_vencimientos INVIMA read fallo: %s', e)
            inv_rows = []

        inv_vencidos, inv_urgentes, inv_proximos = [], [], []
        for inv_id, prod, num, fv in inv_rows:
            try:
                f = _date.fromisoformat(fv[:10])
                dias = (f - hoy).days
            except Exception:
                continue
            entry = {'id': inv_id, 'producto': prod or '',
                     'num_registro': num or '', 'dias': dias, 'fecha': fv}
            if dias < 0:
                inv_vencidos.append(entry)
            elif dias <= 30:
                inv_urgentes.append(entry)
            else:
                inv_proximos.append(entry)

        # ─── SGD ────────────────────────────────────────────────────────
        try:
            sgd_rows = c.execute("""
                SELECT id, tipo, codigo, nombre, fecha_proxima_revision,
                       responsable_revision
                  FROM documentos_sgd
                 WHERE LOWER(COALESCE(estado,'')) = 'vigente'
                   AND COALESCE(fecha_proxima_revision,'') != ''
                   AND date(fecha_proxima_revision) <= date('now', '-5 hours', '+30 days')
                 ORDER BY fecha_proxima_revision ASC
                 LIMIT 200
            """).fetchall()
        except Exception as e:
            log.warning('tecnica_vencimientos SGD read fallo: %s', e)
            sgd_rows = []

        sgd_vencidos, sgd_urgentes, sgd_proximos = [], [], []
        for sgd_id, tipo, cod, nom, fpr, resp in sgd_rows:
            try:
                f = _date.fromisoformat(fpr[:10])
                dias = (f - hoy).days
            except Exception:
                continue
            entry = {'id': sgd_id, 'tipo': tipo or 'SOP', 'codigo': cod or '',
                     'nombre': nom or '', 'dias': dias,
                     'responsable': (resp or '').strip()}
            if dias < 0:
                sgd_vencidos.append(entry)
            elif dias <= 7:
                sgd_urgentes.append(entry)
            else:
                sgd_proximos.append(entry)

        # ─── Decisión de notificar ─────────────────────────────────────
        criticos = inv_vencidos or inv_urgentes or sgd_vencidos or sgd_urgentes
        muchos_prox = (len(inv_proximos) >= 3) or (len(sgd_proximos) >= 5)
        if not (criticos or muchos_prox):
            return True, {'mensaje': 'Sin alertas tecnica · todo dentro de margen'}, 0

        # ─── Construir mensaje ─────────────────────────────────────────
        lines = []
        if inv_vencidos:
            lines.append(f'⛔ INVIMA VENCIDOS: {len(inv_vencidos)}')
            for v in inv_vencidos[:5]:
                lines.append(f'  · {v["producto"]} ({v["num_registro"] or "—"}) hace {abs(v["dias"])}d')
        if inv_urgentes:
            lines.append(f'⏰ INVIMA ≤30d: {len(inv_urgentes)}')
            for u in inv_urgentes[:5]:
                lines.append(f'  · {u["producto"]} en {u["dias"]}d ({u["fecha"]})')
        if inv_proximos:
            lines.append(f'📅 INVIMA 31-90d: {len(inv_proximos)}')
        if sgd_vencidos:
            lines.append(f'⛔ SGD VENCIDOS: {len(sgd_vencidos)}')
            for v in sgd_vencidos[:5]:
                lines.append(f'  · {v["tipo"]} {v["codigo"]} · {v["nombre"][:40]} · hace {abs(v["dias"])}d')
        if sgd_urgentes:
            lines.append(f'⏰ SGD ≤7d: {len(sgd_urgentes)}')
        if sgd_proximos:
            lines.append(f'📅 SGD 8-30d: {len(sgd_proximos)}')

        if inv_vencidos or sgd_vencidos:
            titulo = f'⛔ Tecnica · {len(inv_vencidos)+len(sgd_vencidos)} VENCIDOS sin renovar'
        elif inv_urgentes or sgd_urgentes:
            titulo = f'⏰ Tecnica · {len(inv_urgentes)+len(sgd_urgentes)} venceran pronto'
        else:
            titulo = f'📅 Tecnica · {len(inv_proximos)+len(sgd_proximos)} en horizonte'

        # Destinatarios: TECNICA_USERS + responsables especificos de SGDs
        destinatarios = {'sebastian', 'alejandro', 'hernando', 'miguel'}
        for s in sgd_vencidos + sgd_urgentes:
            if s.get('responsable'):
                destinatarios.add(s['responsable'].lower().strip())

        try:
            from blueprints.notif import push_notif_multi
            push_notif_multi(
                list(destinatarios), 'tecnica', titulo,
                body='\n'.join(lines),
                link='/tecnica', remitente='cron-tecnica',
                importante=bool(inv_vencidos or sgd_vencidos),
            )
        except Exception as e:
            log.warning('tecnica_vencimientos push_notif fallo: %s', e)

        return True, {
            'invima_vencidos': len(inv_vencidos),
            'invima_urgentes_30d': len(inv_urgentes),
            'invima_proximos_90d': len(inv_proximos),
            'sgd_vencidos': len(sgd_vencidos),
            'sgd_urgentes_7d': len(sgd_urgentes),
            'sgd_proximos_30d': len(sgd_proximos),
            'destinatarios': len(destinatarios),
        }, 0


def job_animus_conteo_diario(app):
    """Animus · L-V 8am · asigna 5 SKUs para conteo fisico a Daniela.

    Sebastian 3-may-2026: la asistente nunca cuadra inventario fisico vs
    Shopify. Solucion: conteo ciclico rotativo + ecuacion contable.
    Algoritmo prioridad: dias_sin_contar DESC + volatilidad (mov 7d) DESC.

    Idempotente: si ya hay asignaciones pendientes hoy, no duplica.
    """
    with app.app_context():
        from database import get_db
        conn = get_db(); c = conn.cursor()
        try:
            # ¿Ya hay pendientes hoy?
            pend = c.execute("""
                SELECT COUNT(*) FROM animus_conteos_asignados
                 WHERE fecha_asignado = date('now', '-5 hours') AND estado = 'pendiente'
            """).fetchone()
            if pend and pend[0] > 0:
                return True, {'mensaje': f'Ya hay {pend[0]} asignaciones pendientes hoy'}, 0

            # Ranking SKUs (mismo algoritmo que el endpoint asignar-hoy)
            n = 5
            candidatos = c.execute("""
                WITH baseline_skus AS (
                    SELECT sku FROM animus_inventario_baseline
                ),
                ultimo_conteo AS (
                    SELECT sku, MAX(fecha_asignado) as ult
                      FROM animus_conteos_asignados
                     WHERE estado = 'contado'
                     GROUP BY sku
                ),
                volatilidad AS (
                    SELECT sku, COUNT(*) as movs
                      FROM animus_inventario_movimientos
                     WHERE fecha >= date('now', '-5 hours', '-7 day')
                     GROUP BY sku
                )
                SELECT b.sku,
                       COALESCE(julianday('now') - julianday(uc.ult), 999) as dias_sin_contar,
                       COALESCE(v.movs, 0) as movs_7d
                  FROM baseline_skus b
                  LEFT JOIN ultimo_conteo uc ON uc.sku = b.sku
                  LEFT JOIN volatilidad v ON v.sku = b.sku
                  ORDER BY dias_sin_contar DESC, movs_7d DESC
                  LIMIT ?
            """, (n,)).fetchall()
            if not candidatos:
                return True, {'mensaje': 'Sin SKUs con baseline · pedirle a Daniela que cargue baseline primero'}, 0
            asignados = []
            for r in candidatos:
                c.execute("""INSERT INTO animus_conteos_asignados
                             (sku, asignado_a, estado) VALUES (?, 'daniela', 'pendiente')""",
                          (r[0],))
                asignados.append(r[0])
            conn.commit()
        except Exception as e:
            log.exception('animus_conteo_diario read fallo: %s', e)
            return False, {'error': str(e)[:200]}, 0

        # Notif in-app a Daniela
        try:
            from blueprints.notif import push_notif
            push_notif(
                'daniela', 'animus',
                f'📊 Conteo del día · {len(asignados)} SKUs',
                body='SKUs asignados hoy: ' + ', '.join(asignados) +
                     '\n\nVe a /animus → Inventario Físico → Conteos pendientes',
                link='/animus#tab-invfis',
                remitente='cron-animus',
            )
        except Exception as e:
            log.warning('animus_conteo_diario push_notif fallo: %s', e)

        # Email a Daniela (best-effort · si SMTP no configurado, log warning)
        try:
            from config import USER_EMAILS
            email_dest = USER_EMAILS.get('daniela', '').strip()
            if email_dest:
                from notificaciones import SistemaNotificaciones
                sn = SistemaNotificaciones()
                if sn.email_remitente and sn.contraseña:
                    asunto = f'📊 Conteo del día · {len(asignados)} SKUs · Animus'
                    body = (
                        '<h2 style="color:#0c4a6e;font-family:Segoe UI,sans-serif;">'
                        '📊 Tu conteo de hoy en Animus</h2>'
                        '<p>Hola Daniela 👋</p>'
                        '<p>Hoy tienes que contar fisicamente <b>'
                        + str(len(asignados)) + ' SKUs</b>:</p>'
                        '<ul style="font-family:monospace;background:#f1f5f9;padding:12px 24px;border-radius:8px;">'
                        + ''.join('<li><b>' + s + '</b></li>' for s in asignados)
                        + '</ul>'
                        '<p>Entra a <a href="https://eossuite.com/animus" '
                        'style="color:#10b981;font-weight:700;">eossuite.com/animus</a> '
                        '→ pestaña <b>Inventario Físico</b> → seccion <b>Conteos pendientes</b>.</p>'
                        '<p style="color:#64748b;font-size:13px;">Para cada SKU veras el desglose '
                        '(baseline + entradas - ventas Shopify - salidas) y podras anotar la cantidad '
                        'fisica. Si hay diferencia, te pedira motivo.</p>'
                        '<hr><p style="color:#94a3b8;font-size:11px;">Sistema EOS · cron-animus '
                        '· generado ' + datetime.now().strftime('%Y-%m-%d %H:%M') + '</p>'
                    )
                    sn._enviar_email(asunto, body, destinatarios=[email_dest])
        except Exception as e:
            log.warning('animus_conteo_diario email fallo: %s', e)

        return True, {'asignados': len(asignados), 'skus': asignados}, 0


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
                  AND date(fecha_deteccion) <= date('now', '-5 hours', '-1 day')
                LIMIT 30
            """).fetchall()
            sin_invest = c.execute("""
                SELECT codigo, clasificacion, descripcion FROM desviaciones
                WHERE estado IN ('clasificada')
                  AND date(fecha_deteccion) <= date('now', '-5 hours', '-5 days')
                LIMIT 30
            """).fetchall()
            capa_vencido = c.execute("""
                SELECT codigo, capa_responsable, capa_fecha_limite FROM desviaciones
                WHERE estado IN ('capa_propuesto','capa_implementado')
                  AND capa_fecha_limite IS NOT NULL
                  AND date(capa_fecha_limite) < date('now', '-5 hours')
                LIMIT 30
            """).fetchall()
            # INVIMA-FIX · 21-may-2026 · también capa_acciones (otra tabla)
            # Antes solo monitoreaba desviaciones.capa_fecha_limite
            # · capa_acciones.fecha_compromiso quedaba invisible (creadas
            # via /api/calidad/capa endpoint).
            try:
                capa_acc_vencido = c.execute("""
                    SELECT id, responsable, fecha_compromiso, descripcion
                    FROM capa_acciones
                    WHERE estado IN ('Pendiente','En curso','Ejecutada')
                      AND fecha_compromiso IS NOT NULL AND fecha_compromiso != ''
                      AND date(fecha_compromiso) < date('now', '-5 hours')
                    LIMIT 30
                """).fetchall()
            except Exception:
                capa_acc_vencido = []
        except Exception as e:
            log.warning('desv_plazos read fallo: %s', e)
            return False, {'error': str(e)[:200]}, 0

        if not sin_clasif and not sin_invest and not capa_vencido and not capa_acc_vencido:
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
                partes.append(f'⛔ {len(capa_vencido)} CAPA-DESV VENCIDO')
                for r in capa_vencido[:3]: partes.append(f'  · {r[0]}: resp {r[1]} · venció {r[2]}')
            if capa_acc_vencido:
                partes.append(f'⛔ {len(capa_acc_vencido)} CAPA-ACC VENCIDO')
                for r in capa_acc_vencido[:3]: partes.append(f'  · CAPA-{r[0]}: resp {r[1]} · venció {r[2]}')
            push_notif_multi(
                destinatarios, 'capa',
                f'⚠ Desviaciones en plazo vencido (ASG-PRO-001)',
                body='\n'.join(partes),
                link='/aseguramiento', remitente='cron-desv',
                importante=bool(capa_vencido or capa_acc_vencido or len(sin_clasif) >= 3),
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
                  AND date(fecha_solicitud) <= date('now', '-5 hours', '-5 days')
                LIMIT 30
            """).fetchall()
            invima_pendiente = c.execute("""
                SELECT codigo, titulo, aprobado_at FROM control_cambios
                WHERE estado IN ('aprobado','en_implementacion')
                  AND requiere_invima=1
                  AND notificacion_invima_at IS NULL
                  AND date(aprobado_at) <= date('now', '-5 hours', '-3 days')
                LIMIT 30
            """).fetchall()
            sin_implementar = c.execute("""
                SELECT codigo, titulo, responsable_implementacion, fecha_implementacion_propuesta
                FROM control_cambios
                WHERE estado IN ('aprobado','en_implementacion')
                  AND date(aprobado_at) <= date('now', '-5 hours', '-30 days')
                  AND (requiere_invima=0 OR notificacion_invima_at IS NOT NULL)
                LIMIT 30
            """).fetchall()
            sin_cerrar = c.execute("""
                SELECT codigo, titulo, implementado_por, implementado_at
                FROM control_cambios
                WHERE estado='implementado'
                  AND date(implementado_at) <= date('now', '-5 hours', '-15 days')
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
                  AND date(fecha_recepcion) <= date('now', '-5 hours', '-1 day')
                LIMIT 30
            """).fetchall()
            criticas_lentas = c.execute("""
                SELECT codigo, cliente_nombre, tipo_queja FROM quejas_clientes
                WHERE estado IN ('en_triaje','en_investigacion')
                  AND (severidad='critica' OR impacto_salud=1)
                  AND date(fecha_recepcion) <= date('now', '-5 hours', '-2 day')
                LIMIT 30
            """).fetchall()
            sin_responder = c.execute("""
                SELECT codigo, cliente_nombre, severidad FROM quejas_clientes
                WHERE estado IN ('en_triaje','en_investigacion')
                  AND (severidad IS NULL OR severidad NOT IN ('critica'))
                  AND impacto_salud=0
                  AND date(fecha_recepcion) <= date('now', '-5 hours', '-7 day')
                LIMIT 30
            """).fetchall()
            sin_cerrar = c.execute("""
                SELECT codigo, cliente_nombre, respondido_at FROM quejas_clientes
                WHERE estado='respondida'
                  AND date(respondido_at) <= date('now', '-5 hours', '-14 day')
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
                  AND datetime(creado_en) <= datetime('now', '-5 hours', '-12 hours')
                LIMIT 30
            """).fetchall()
            clase_I_sin_invima = c.execute("""
                SELECT codigo, producto FROM recalls
                WHERE clase_recall='clase_I'
                  AND notificacion_invima_at IS NULL
                  AND estado NOT IN ('cerrado','cancelado')
                  AND datetime(clasificado_at) <= datetime('now', '-5 hours', '-1 day')
                LIMIT 30
            """).fetchall()
            sin_invima_5d = c.execute("""
                SELECT codigo, producto, clase_recall FROM recalls
                WHERE clase_recall IN ('clase_II','clase_III')
                  AND notificacion_invima_at IS NULL
                  AND estado NOT IN ('cerrado','cancelado')
                  AND date(clasificado_at) <= date('now', '-5 hours', '-5 day')
                LIMIT 30
            """).fetchall()
            sin_recolectar_30d = c.execute("""
                SELECT codigo, producto, cantidad_recolectada, cantidad_distribuida
                FROM recalls
                WHERE estado IN ('distribuidores_notificados','en_recoleccion')
                  AND date(notificacion_invima_at) <= date('now', '-5 hours', '-30 day')
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


def _build_weekly_executive_html(snapshot, kpis):
    """Construye el HTML del email semanal ejecutivo.

    snapshot: dict con secciones de /api/admin/health-detailed
    kpis: dict con KPIs financieros + operacionales agregados de la semana.
    """
    fecha_str = datetime.now().strftime('%A %d-%b-%Y')
    overall = snapshot.get('overall', 'ok')
    overall_color = {'ok': '#15803d', 'warning': '#d97706', 'error': '#dc2626'}.get(overall, '#64748b')
    overall_icon = {'ok': '🟢', 'warning': '🟡', 'error': '🔴'}.get(overall, '⚪')

    # ── Sección Operacional crítica ──
    sections = snapshot.get('sections', {})
    accion_rows = []
    PRIORITY = [
        ('invima', 'Registros INVIMA'),
        ('recalls', 'Recalls activos'),
        ('hallazgos_vencidos', 'Hallazgos vencidos'),
        ('cuarentena', 'Lotes en cuarentena'),
        ('liberacion_pt', 'Liberación PT pendiente'),
        ('caja', 'Caja vs commitments'),
    ]
    for key, label in PRIORITY:
        sec = sections.get(key, {})
        st = sec.get('status', 'ok')
        if st == 'ok':
            continue
        color = '#dc2626' if st == 'error' else '#d97706'
        hint = sec.get('hint', '')
        # Resumen breve de la sección
        bullets = []
        for k, v in sec.items():
            if k in ('status', 'hint', 'detail'):
                continue
            if isinstance(v, (int, float)) and v == 0:
                continue
            bullets.append(f"{k}: <b>{v}</b>")
        bullets_html = ' · '.join(bullets[:4]) or '(sin datos)'
        accion_rows.append(f"""
        <tr><td style="padding:10px 14px;border-left:4px solid {color};background:#fef2f2;font-size:13px">
          <b style="color:{color}">{label}</b><br>
          <span style="color:#475569;font-size:12px">{bullets_html}</span>
          {f'<div style="margin-top:6px;color:{color};font-size:12px">→ {hint}</div>' if hint else ''}
        </td></tr>""")
    accion_html = ''.join(accion_rows) or (
        '<tr><td style="padding:14px;color:#15803d;font-size:13px">✓ Sin acciones críticas pendientes</td></tr>'
    )

    # ── KPIs ejecutivos ──
    kpi_html = ''
    for k, v in kpis.items():
        kpi_html += f"""
        <td style="padding:14px;text-align:center;border-right:1px solid #e5e7eb">
          <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.5px">{k}</div>
          <div style="font-size:22px;font-weight:700;color:#0f172a;margin-top:4px">{v}</div>
        </td>"""

    # ── Salas planta ──
    salas = sections.get('salas', {})
    salas_html = ''
    for estado, count in salas.items():
        if estado == 'status':
            continue
        emoji = {'libre': '🟢', 'ocupada': '🔵', 'sucia': '🟡', 'limpiando': '🧽'}.get(estado, '⚪')
        salas_html += f'<span style="margin-right:14px;font-size:13px">{emoji} {estado}: <b>{count}</b></span>'

    return f"""<!DOCTYPE html>
<html><body style="font-family:-apple-system,'Segoe UI',Roboto,sans-serif;background:#f3f4f6;padding:20px;color:#1f2937;margin:0">
  <div style="max-width:680px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 12px rgba(0,0,0,.08)">

    <!-- Header -->
    <div style="background:linear-gradient(135deg,#0f172a,#1e293b);color:#fff;padding:24px 28px">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <div>
          <h1 style="margin:0;font-size:20px;font-weight:700">📊 Executive Brief · {fecha_str}</h1>
          <div style="margin-top:4px;font-size:12px;color:#94a3b8">HHA Group · semana entrante</div>
        </div>
        <div style="background:{overall_color};color:#fff;padding:8px 14px;border-radius:6px;font-size:13px;font-weight:700">
          {overall_icon} {overall.upper()}
        </div>
      </div>
    </div>

    <!-- KPIs ejecutivos -->
    <div style="padding:0">
      <table style="width:100%;border-collapse:collapse;border-bottom:1px solid #e5e7eb">
        <tr>{kpi_html}</tr>
      </table>
    </div>

    <!-- Acciones críticas -->
    <div style="padding:20px 28px">
      <h2 style="margin:0 0 14px 0;font-size:15px;color:#0f172a;border-bottom:2px solid #0f172a;padding-bottom:6px">
        🎯 Tu atención esta semana
      </h2>
      <table style="width:100%;border-collapse:collapse">
        {accion_html}
      </table>
    </div>

    <!-- Salas planta -->
    <div style="padding:14px 28px;background:#f8fafc;border-top:1px solid #e5e7eb">
      <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px">
        🏭 Estado planta (ahora)
      </div>
      <div>{salas_html or '(sin datos)'}</div>
    </div>

    <!-- Footer -->
    <div style="padding:16px 28px;background:#0f172a;color:#94a3b8;font-size:11px;text-align:center">
      Cockpit completo: <a href="https://app.eossuite.com/admin/system-health" style="color:#7ACFCC;text-decoration:none">app.eossuite.com/admin/system-health</a><br>
      <span style="color:#64748b">Generado por cron · weekly_executive · cada lunes 7:30am COT</span>
    </div>
  </div>
</body></html>"""


def _calcular_kpis_semanales(conn):
    """KPIs agregados de la última semana para el email ejecutivo."""
    kpis = {}
    try:
        c = conn.cursor()
        # Pedidos B2B emitidos última semana
        r = c.execute("""SELECT COUNT(*), COALESCE(SUM(valor_total),0)
                         FROM pedidos
                         WHERE fecha >= date('now', '-5 hours', '-7 days')""").fetchone()
        kpis['Pedidos 7d'] = f"{r[0] or 0}"
        kpis['Ventas 7d'] = f"${(r[1] or 0)/1_000_000:.1f}M"
    except Exception:
        kpis['Pedidos 7d'] = '—'; kpis['Ventas 7d'] = '—'
    try:
        # OCs creadas última semana
        n_oc = c.execute("""SELECT COUNT(*) FROM ordenes_compra
                            WHERE fecha >= date('now', '-5 hours', '-7 days')""").fetchone()[0]
        kpis['OCs 7d'] = f"{n_oc or 0}"
    except Exception:
        kpis['OCs 7d'] = '—'
    try:
        # Producciones completadas semana
        n_prod = c.execute("""SELECT COUNT(*) FROM produccion_programada
                              WHERE fin_real_at IS NOT NULL
                                AND fin_real_at >= datetime('now', '-5 hours', '-7 days')""").fetchone()[0]
        kpis['Prod 7d'] = f"{n_prod or 0}"
    except Exception:
        kpis['Prod 7d'] = '—'
    try:
        # Audit log entries 7d (señal de actividad regulatoria)
        n_audit = c.execute("""SELECT COUNT(*) FROM audit_log
                               WHERE fecha >= datetime('now', '-5 hours', '-7 days')""").fetchone()[0]
        kpis['Audit 7d'] = f"{n_audit or 0}"
    except Exception:
        kpis['Audit 7d'] = '—'
    return kpis


def _capturar_health_snapshot(app):
    """Llama internamente a /api/admin/health-detailed y retorna el dict.

    Reusa la lógica del endpoint sin pasar por HTTP — más rápido y sin
    necesidad de auth.
    """
    try:
        import time as _time
        tc = app.test_client()
        with tc.session_transaction() as sess:
            sess['compras_user'] = 'sebastian'
            sess['login_time'] = _time.time()  # evita timeout de 8h en before_request
        r = tc.get('/api/admin/health-detailed')
        if r.status_code == 200:
            return r.get_json()
        log.warning('health snapshot retorna %s · body=%s',
                     r.status_code, r.get_data(as_text=True)[:200])
    except Exception as e:
        log.warning('health snapshot exception: %s', e)
    return {'overall': 'error', 'sections': {},
            'snapshot_error': True}


def job_weekly_executive_email(app):
    """Cron lunes 7:30am · email ejecutivo a Sebastián con health + KPIs.

    Hace que el dashboard de salud sea PROACTIVO en vez de reactivo. El CEO
    no necesita abrir /admin/system-health · llega a su inbox.
    """
    with app.app_context():
        from database import get_db
        try:
            snapshot = _capturar_health_snapshot(app)
            conn = get_db()
            kpis = _calcular_kpis_semanales(conn)
            html = _build_weekly_executive_html(snapshot, kpis)
            from config import USER_EMAILS
            destino = USER_EMAILS.get('sebastian', '').strip()
            if not destino:
                log.warning('weekly_executive_email · EMAIL_SEBASTIAN no configurado')
                return False, {'error': 'EMAIL_SEBASTIAN no configurado'}, 0
            overall = snapshot.get('overall', 'ok')
            icon = {'ok': '🟢', 'warning': '🟡', 'error': '🔴'}.get(overall, '⚪')
            asunto = f"{icon} Executive Brief HHA · {datetime.now().strftime('%d-%b-%Y')}"
            _enviar_email_async(asunto, html, [destino])
            return True, {
                'destino': destino, 'overall': overall,
                'kpis': kpis,
                'secciones_warning_or_error': sum(
                    1 for s in snapshot.get('sections', {}).values()
                    if isinstance(s, dict) and s.get('status') in ('warning', 'error')
                ),
            }, 0
        except Exception as e:
            log.exception('weekly_executive_email fallo: %s', e)
            return False, {'error': str(e)[:300]}, 0


def _calcular_pnl_mensual(conn, periodo):
    """Calcula P&L de un período YYYY-MM.

    Retorna dict con: ingresos_total, egresos_total, margen, egresos_por_categoria,
    mes_anterior_ingresos (para MoM), mom_pct.
    """
    c = conn.cursor()
    pnl = {'periodo': periodo}
    # Ingresos
    try:
        ing = c.execute("""SELECT COALESCE(SUM(monto),0) FROM flujo_ingresos
                           WHERE periodo=?""", (periodo,)).fetchone()[0]
        pnl['ingresos_total'] = float(ing or 0)
    except Exception:
        pnl['ingresos_total'] = 0.0
    # Egresos
    try:
        eg = c.execute("""SELECT COALESCE(SUM(monto),0) FROM flujo_egresos
                          WHERE periodo=?""", (periodo,)).fetchone()[0]
        pnl['egresos_total'] = float(eg or 0)
    except Exception:
        pnl['egresos_total'] = 0.0
    # Margen
    pnl['margen'] = pnl['ingresos_total'] - pnl['egresos_total']
    pnl['margen_pct'] = (pnl['margen'] / pnl['ingresos_total'] * 100) if pnl['ingresos_total'] > 0 else 0
    # Egresos por categoría (top 5)
    try:
        cats = c.execute("""SELECT COALESCE(categoria,'Otro'), SUM(monto)
                            FROM flujo_egresos WHERE periodo=?
                            GROUP BY categoria ORDER BY 2 DESC LIMIT 5""",
                          (periodo,)).fetchall()
        pnl['egresos_por_categoria'] = [
            {'categoria': r[0], 'monto': float(r[1] or 0)} for r in cats
        ]
    except Exception:
        pnl['egresos_por_categoria'] = []
    # MoM: ingresos mes anterior
    try:
        from datetime import datetime as _dt
        y, m = periodo.split('-')
        anio_a = int(y); mes_a = int(m) - 1
        if mes_a == 0:
            mes_a = 12; anio_a -= 1
        periodo_prev = f"{anio_a:04d}-{mes_a:02d}"
        ing_prev = c.execute("""SELECT COALESCE(SUM(monto),0) FROM flujo_ingresos
                                WHERE periodo=?""", (periodo_prev,)).fetchone()[0]
        pnl['mes_anterior'] = periodo_prev
        pnl['mes_anterior_ingresos'] = float(ing_prev or 0)
        if pnl['mes_anterior_ingresos'] > 0:
            pnl['mom_pct'] = (pnl['ingresos_total'] - pnl['mes_anterior_ingresos']) / pnl['mes_anterior_ingresos'] * 100
        else:
            pnl['mom_pct'] = None
    except Exception:
        pnl['mes_anterior'] = None
        pnl['mes_anterior_ingresos'] = 0.0
        pnl['mom_pct'] = None
    return pnl


def _calcular_tops_mes(conn, periodo):
    """Top 5 clientes y top 5 proveedores del mes."""
    c = conn.cursor()
    tops = {}
    # Top clientes (pedidos del mes)
    try:
        rows = c.execute("""
            SELECT COALESCE(cl.nombre, 'Sin cliente') as cliente,
                   COUNT(p.id) as n_pedidos,
                   COALESCE(SUM(p.valor_total), 0) as total
            FROM pedidos p
              LEFT JOIN clientes cl ON cl.id = p.cliente_id
            WHERE strftime('%Y-%m', p.fecha) = ?
            GROUP BY cliente
            ORDER BY total DESC LIMIT 5
        """, (periodo,)).fetchall()
        tops['clientes'] = [
            {'nombre': r[0], 'pedidos': r[1], 'total': float(r[2] or 0)}
            for r in rows
        ]
    except Exception:
        tops['clientes'] = []
    # Top proveedores (OCs del mes)
    try:
        rows = c.execute("""
            SELECT COALESCE(proveedor, 'Sin proveedor'),
                   COUNT(*) as n_ocs,
                   COALESCE(SUM(valor_total), 0) as total
            FROM ordenes_compra
            WHERE strftime('%Y-%m', fecha) = ?
              AND estado != 'Rechazada'
            GROUP BY proveedor
            ORDER BY total DESC LIMIT 5
        """, (periodo,)).fetchall()
        tops['proveedores'] = [
            {'nombre': r[0], 'ocs': r[1], 'total': float(r[2] or 0)}
            for r in rows
        ]
    except Exception:
        tops['proveedores'] = []
    return tops


def _calcular_operativos_mes(conn, periodo):
    """Producciones completadas + lotes liberados/rechazados del mes."""
    c = conn.cursor()
    op = {}
    try:
        op['producciones_completadas'] = c.execute("""
            SELECT COUNT(*) FROM produccion_programada
            WHERE fin_real_at IS NOT NULL
              AND strftime('%Y-%m', fin_real_at) = ?
        """, (periodo,)).fetchone()[0] or 0
    except Exception:
        op['producciones_completadas'] = 0
    try:
        op['lotes_liberados'] = c.execute("""
            SELECT COUNT(*) FROM cola_liberacion
            WHERE estado='liberado'
              AND strftime('%Y-%m', aprobado_at) = ?
        """, (periodo,)).fetchone()[0] or 0
    except Exception:
        op['lotes_liberados'] = 0
    try:
        op['lotes_rechazados'] = c.execute("""
            SELECT COUNT(*) FROM cola_liberacion
            WHERE estado='rechazado'
              AND strftime('%Y-%m', aprobado_at) = ?
        """, (periodo,)).fetchone()[0] or 0
    except Exception:
        op['lotes_rechazados'] = 0
    try:
        op['facturas_emitidas'] = c.execute("""
            SELECT COUNT(*) FROM facturas
            WHERE strftime('%Y-%m', fecha_emision) = ?
              AND estado != 'Anulada'
        """, (periodo,)).fetchone()[0] or 0
    except Exception:
        op['facturas_emitidas'] = 0
    return op


def _build_monthly_financial_html(pnl, tops, operativos, caja_actual):
    """HTML del email mensual financiero ejecutivo."""
    periodo = pnl['periodo']
    # Formatear fecha amigable
    try:
        from datetime import datetime as _dt
        meses_es = ['enero','febrero','marzo','abril','mayo','junio',
                    'julio','agosto','septiembre','octubre','noviembre','diciembre']
        y, m = periodo.split('-')
        periodo_label = f"{meses_es[int(m)-1]} {y}"
    except Exception:
        periodo_label = periodo

    # MoM badge
    mom = pnl.get('mom_pct')
    if mom is None:
        mom_html = '<span style="color:#94a3b8">—</span>'
    elif mom >= 0:
        mom_html = f'<span style="color:#15803d;font-weight:700">▲ {mom:+.1f}%</span>'
    else:
        mom_html = f'<span style="color:#dc2626;font-weight:700">▼ {mom:.1f}%</span>'

    # Margen color
    margen_color = '#15803d' if pnl['margen'] >= 0 else '#dc2626'

    # Categorías egresos
    cat_rows = ''
    for cat in pnl.get('egresos_por_categoria', []):
        pct = (cat['monto'] / pnl['egresos_total'] * 100) if pnl['egresos_total'] > 0 else 0
        cat_rows += f"""
        <tr>
          <td style="padding:8px 12px;font-size:12px;border-bottom:1px solid #e5e7eb">{cat['categoria']}</td>
          <td style="padding:8px 12px;font-size:12px;text-align:right;border-bottom:1px solid #e5e7eb">${cat['monto']/1_000_000:.1f}M</td>
          <td style="padding:8px 12px;font-size:11px;color:#64748b;text-align:right;border-bottom:1px solid #e5e7eb">{pct:.0f}%</td>
        </tr>"""
    if not cat_rows:
        cat_rows = '<tr><td colspan="3" style="padding:14px;color:#94a3b8;font-size:12px;text-align:center">Sin egresos en el período</td></tr>'

    # Top clientes
    cli_rows = ''
    for c in tops.get('clientes', []):
        cli_rows += f"""
        <tr>
          <td style="padding:6px 12px;font-size:12px;border-bottom:1px solid #f1f5f9">{c['nombre'][:35]}</td>
          <td style="padding:6px 12px;font-size:11px;color:#64748b;text-align:right;border-bottom:1px solid #f1f5f9">{c['pedidos']} ped.</td>
          <td style="padding:6px 12px;font-size:12px;text-align:right;border-bottom:1px solid #f1f5f9"><b>${c['total']/1_000_000:.1f}M</b></td>
        </tr>"""
    if not cli_rows:
        cli_rows = '<tr><td colspan="3" style="padding:12px;color:#94a3b8;font-size:11px;text-align:center">Sin pedidos</td></tr>'

    # Top proveedores
    prov_rows = ''
    for p in tops.get('proveedores', []):
        prov_rows += f"""
        <tr>
          <td style="padding:6px 12px;font-size:12px;border-bottom:1px solid #f1f5f9">{p['nombre'][:35]}</td>
          <td style="padding:6px 12px;font-size:11px;color:#64748b;text-align:right;border-bottom:1px solid #f1f5f9">{p['ocs']} OCs</td>
          <td style="padding:6px 12px;font-size:12px;text-align:right;border-bottom:1px solid #f1f5f9"><b>${p['total']/1_000_000:.1f}M</b></td>
        </tr>"""
    if not prov_rows:
        prov_rows = '<tr><td colspan="3" style="padding:12px;color:#94a3b8;font-size:11px;text-align:center">Sin OCs</td></tr>'

    return f"""<!DOCTYPE html>
<html><body style="font-family:-apple-system,'Segoe UI',Roboto,sans-serif;background:#f3f4f6;padding:20px;color:#1f2937;margin:0">
  <div style="max-width:680px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 12px rgba(0,0,0,.08)">

    <!-- Header -->
    <div style="background:linear-gradient(135deg,#0f766e,#134e4a);color:#fff;padding:24px 28px">
      <h1 style="margin:0;font-size:22px">📈 Reporte Mensual · {periodo_label}</h1>
      <div style="margin-top:6px;font-size:12px;color:#a7f3d0">HHA Group · P&amp;L + tendencias del mes</div>
    </div>

    <!-- P&L grid -->
    <div style="padding:0">
      <table style="width:100%;border-collapse:collapse;border-bottom:1px solid #e5e7eb">
        <tr>
          <td style="padding:18px;text-align:center;border-right:1px solid #e5e7eb;background:#f0fdf4">
            <div style="font-size:11px;color:#166534;text-transform:uppercase;letter-spacing:.5px">Ingresos</div>
            <div style="font-size:24px;font-weight:700;color:#15803d;margin-top:4px">${pnl['ingresos_total']/1_000_000:.1f}M</div>
            <div style="font-size:11px;margin-top:4px">vs mes ant: {mom_html}</div>
          </td>
          <td style="padding:18px;text-align:center;border-right:1px solid #e5e7eb;background:#fef2f2">
            <div style="font-size:11px;color:#991b1b;text-transform:uppercase;letter-spacing:.5px">Egresos</div>
            <div style="font-size:24px;font-weight:700;color:#dc2626;margin-top:4px">${pnl['egresos_total']/1_000_000:.1f}M</div>
            <div style="font-size:11px;color:#94a3b8;margin-top:4px">salida total</div>
          </td>
          <td style="padding:18px;text-align:center">
            <div style="font-size:11px;color:#475569;text-transform:uppercase;letter-spacing:.5px">Margen</div>
            <div style="font-size:24px;font-weight:700;color:{margen_color};margin-top:4px">${pnl['margen']/1_000_000:.1f}M</div>
            <div style="font-size:11px;color:#64748b;margin-top:4px">{pnl['margen_pct']:.1f}%</div>
          </td>
        </tr>
      </table>
    </div>

    <!-- Egresos por categoría -->
    <div style="padding:20px 28px">
      <h2 style="margin:0 0 12px 0;font-size:14px;color:#0f172a;border-bottom:2px solid #0f172a;padding-bottom:6px">
        💸 Egresos por categoría
      </h2>
      <table style="width:100%;border-collapse:collapse">
        <thead>
          <tr style="background:#f8fafc">
            <th style="padding:8px 12px;text-align:left;font-size:10px;color:#64748b;text-transform:uppercase">Categoría</th>
            <th style="padding:8px 12px;text-align:right;font-size:10px;color:#64748b;text-transform:uppercase">Monto</th>
            <th style="padding:8px 12px;text-align:right;font-size:10px;color:#64748b;text-transform:uppercase">%</th>
          </tr>
        </thead>
        <tbody>{cat_rows}</tbody>
      </table>
    </div>

    <!-- Top clientes -->
    <div style="padding:0 28px 20px 28px">
      <h2 style="margin:0 0 12px 0;font-size:14px;color:#0f172a;border-bottom:2px solid #0f172a;padding-bottom:6px">
        🏆 Top 5 clientes del mes
      </h2>
      <table style="width:100%;border-collapse:collapse">
        <tbody>{cli_rows}</tbody>
      </table>
    </div>

    <!-- Top proveedores -->
    <div style="padding:0 28px 20px 28px">
      <h2 style="margin:0 0 12px 0;font-size:14px;color:#0f172a;border-bottom:2px solid #0f172a;padding-bottom:6px">
        🚚 Top 5 proveedores del mes
      </h2>
      <table style="width:100%;border-collapse:collapse">
        <tbody>{prov_rows}</tbody>
      </table>
    </div>

    <!-- Operativos -->
    <div style="padding:14px 28px;background:#f8fafc;border-top:1px solid #e5e7eb">
      <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px">
        ⚙️ Operativos del mes
      </div>
      <div style="display:flex;flex-wrap:wrap;gap:18px;font-size:12px">
        <span>🏭 Producciones: <b>{operativos['producciones_completadas']}</b></span>
        <span>✅ Lotes liberados: <b>{operativos['lotes_liberados']}</b></span>
        <span>❌ Lotes rechazados: <b style="color:#dc2626">{operativos['lotes_rechazados']}</b></span>
        <span>🧾 Facturas: <b>{operativos['facturas_emitidas']}</b></span>
      </div>
      {f'<div style="margin-top:10px;font-size:12px">💰 Caja actual: <b>${caja_actual/1_000_000:.1f}M</b></div>' if caja_actual else ''}
    </div>

    <!-- Footer -->
    <div style="padding:16px 28px;background:#0f172a;color:#94a3b8;font-size:11px;text-align:center">
      Detalle completo: <a href="https://app.eossuite.com/financiero" style="color:#7ACFCC;text-decoration:none">app.eossuite.com/financiero</a><br>
      <span style="color:#64748b">Generado por cron · monthly_financial · cada día 1 a las 8am COT</span>
    </div>
  </div>
</body></html>"""


def job_monthly_financial_summary(app):
    """Cron día 1 de cada mes 8am · reporte financiero mensual a Sebastián.

    P&L del mes anterior + MoM + tops clientes/proveedores + operativos.
    Cierra el ciclo de visibilidad ejecutiva (semanal: salud · mensual: $$$).
    """
    with app.app_context():
        from database import get_db
        from datetime import datetime as _dt
        try:
            # Período = mes ANTERIOR (estamos el día 1, miramos el mes que cerró)
            hoy = _dt.now()
            anio = hoy.year
            mes = hoy.month - 1
            if mes == 0:
                mes = 12; anio -= 1
            periodo = f"{anio:04d}-{mes:02d}"

            conn = get_db()
            pnl = _calcular_pnl_mensual(conn, periodo)
            tops = _calcular_tops_mes(conn, periodo)
            operativos = _calcular_operativos_mes(conn, periodo)
            # Caja del último input
            caja_actual = 0.0
            try:
                r = conn.execute("""SELECT saldo_caja FROM gerencia_inputs
                                    ORDER BY periodo DESC LIMIT 1""").fetchone()
                if r:
                    caja_actual = float(r[0] or 0)
            except Exception:
                pass

            html = _build_monthly_financial_html(pnl, tops, operativos, caja_actual)

            from config import USER_EMAILS
            destino = USER_EMAILS.get('sebastian', '').strip()
            if not destino:
                log.warning('monthly_financial_summary · EMAIL_SEBASTIAN no configurado')
                return False, {'error': 'EMAIL_SEBASTIAN no configurado',
                                'periodo': periodo}, 0
            margen_icon = '🟢' if pnl['margen'] >= 0 else '🔴'
            asunto = (f"{margen_icon} Reporte Mensual HHA · {periodo} · "
                      f"Margen ${pnl['margen']/1_000_000:.1f}M ({pnl['margen_pct']:.1f}%)")
            _enviar_email_async(asunto, html, [destino])
            return True, {
                'destino': destino, 'periodo': periodo,
                'ingresos': pnl['ingresos_total'],
                'egresos': pnl['egresos_total'],
                'margen': pnl['margen'],
                'margen_pct': round(pnl['margen_pct'], 1),
                'mom_pct': pnl.get('mom_pct'),
                'top_clientes_count': len(tops.get('clientes', [])),
                'top_proveedores_count': len(tops.get('proveedores', [])),
                'caja_actual': caja_actual,
            }, 0
        except Exception as e:
            log.exception('monthly_financial_summary fallo: %s', e)
            return False, {'error': str(e)[:300]}, 0


def job_drift_detector_inventario(app):
    """Cron diario 6:30am · detecta drift en inventario MP/MEE y alerta.

    CERO SESGO continuo: si los helpers se usan correctamente, drift=0
    siempre. Pero data legacy o bugs operacionales pueden introducir drift.
    Este cron detecta y alerta para que se investigue antes de que
    contamine cálculos de la IA o reportes.

    Detecta:
      - MPs con stock NEGATIVO (más salidas que entradas · imposible)
      - MEEs con drift entre maestro_mee.stock_actual y SUM(movimientos_mee)

    Si encuentra: push_notif al equipo de planta + audit_log + email a CEO
    si severidad critical (>1000g/und).
    """
    with app.app_context():
        from database import get_db
        from inventario_helpers import detect_drift_mp, detect_drift_mee
        try:
            conn = get_db()
            mp_neg = detect_drift_mp(conn)
            mee_drift = detect_drift_mee(conn)
            total = len(mp_neg) + len(mee_drift)
            if total == 0:
                return True, {'mensaje': 'Sin drift · cero sesgo OK'}, 0

            # Severidad crítica si hay stocks negativos o drift > 1000
            criticos = sum(1 for x in mp_neg if x.get('severidad') == 'critical')
            criticos += sum(1 for x in mee_drift if x.get('severidad') == 'critical')

            # Notif in-app a planta + sebastian
            try:
                from blueprints.notif import push_notif_multi
                partes = [f'🚨 Inventario · {total} item(s) con sesgo detectado']
                if mp_neg:
                    partes.append(f'  · {len(mp_neg)} MP con stock negativo')
                    for it in mp_neg[:3]:
                        partes.append(f"    {it['codigo_mp']}: {it['stock_g']:.0f}g")
                if mee_drift:
                    partes.append(f'  · {len(mee_drift)} MEE con drift')
                    for it in mee_drift[:3]:
                        partes.append(f"    {it['codigo']}: drift {it['drift']:+.0f}")
                push_notif_multi(
                    ['sebastian', 'alejandro', 'controlcalidad.espagiria'],
                    'capa',
                    f'⚠️ CERO SESGO violado · {total} item(s) con drift',
                    body='\n'.join(partes),
                    link='/admin/audit-inventario',
                    remitente='cron-drift',
                    importante=(criticos > 0),
                )
            except Exception as e:
                log.warning('drift detector notif fallo: %s', e)

            # Audit log
            try:
                from audit_helpers import audit_log
                audit_log(conn.cursor(), usuario='sistema',
                          accion='DRIFT_INVENTARIO_DETECTADO',
                          tabla=None, registro_id=None,
                          despues={'mp_negativos': len(mp_neg),
                                    'mee_con_drift': len(mee_drift),
                                    'criticos': criticos},
                          detalle=f'Cron drift detector encontró {total} item(s) con sesgo')
                conn.commit()
            except Exception as e:
                log.warning('drift detector audit fallo: %s', e)

            return True, {
                'mp_negativos': len(mp_neg),
                'mee_con_drift': len(mee_drift),
                'total': total,
                'criticos': criticos,
                'top_mp': [it['codigo_mp'] for it in mp_neg[:5]],
                'top_mee': [it['codigo'] for it in mee_drift[:5]],
            }, 0
        except Exception as e:
            log.exception('drift_detector_inventario fallo: %s', e)
            return False, {'error': str(e)[:300]}, 0


def _db_autoheal_check(app):
    """Auto-healing de la BD · Sebastián 16-may-2026.

    Chequea la integridad de la BD; si está corrupta ('malformed' /
    'disk I/O error'), la restaura automáticamente del backup más
    reciente · sin intervención manual. Cooldown de 2h para no
    restaurar en cadena si el problema (disco) persiste.

    Devuelve dict con el resultado para incluir en el reporte watcher.
    """
    from config import DB_PATH
    import time as _time
    corrupta = False
    detalle = ''
    try:
        cx = db_connect(timeout=5.0)
        try:
            row = cx.execute('PRAGMA quick_check').fetchone()
            if row and str(row[0]).lower() != 'ok':
                corrupta = True
                detalle = str(row[0])[:120]
        finally:
            cx.close()
    except sqlite3.DatabaseError as e:
        m = str(e).lower()
        if any(p in m for p in ('malformed', 'corrupt', 'disk i/o',
                                 'i/o error', 'not a database')):
            corrupta = True
            detalle = str(e)[:120]
    except Exception as e:
        log.warning('autoheal quick_check no concluyente: %s', e)

    if not corrupta:
        return {'bd': 'ok'}

    log.error('AUTOHEAL · BD corrupta detectada: %s', detalle)
    marker = DB_PATH + '.autoheal-ts'
    ahora = _time.time()
    # Cooldown · si ya se restauró hace <2h, NO repetir · solo alertar.
    # Si el marker es ilegible/corrupto → asumir cooldown ACTIVO (fail-safe):
    # mejor alertar de más que entrar en un loop de restores en cadena.
    if os.path.exists(marker):
        try:
            with open(marker) as f:
                last = float((f.read() or '0').strip() or 0)
        except Exception:
            last = ahora  # ilegible → tratar como restore recién hecho
        if ahora - last < 2 * 3600:
            log.error('AUTOHEAL · restore reciente (<2h) · no repito · alerto')
            return {'bd': 'corrupta', 'accion': 'cooldown', 'detalle': detalle,
                    'mensaje': 'BD corrupta y ya restaurada hace <2h · '
                               'el disco de Render sigue fallando · escalar'}

    # Escribir el marker ANTES de restaurar. Si se escribiera DESPUÉS y esa
    # escritura fallara (disco lleno · el mismo fallo que corrompió la BD),
    # el cooldown nunca se activaría y el autoheal restauraría en cadena
    # cada hora. Escribir antes garantiza el cooldown aunque el restore
    # falle (en ese caso alerta en vez de loopear). Escritura atómica.
    try:
        _tmp_marker = marker + '.tmp'
        with open(_tmp_marker, 'w') as f:
            f.write(str(ahora))
        os.replace(_tmp_marker, marker)
    except Exception as e:
        log.warning('AUTOHEAL · no se pudo escribir marker de cooldown: %s', e)

    # Restaurar · invocar emergency-restore internamente
    resultado = {'bd': 'corrupta', 'detalle': detalle}
    try:
        from blueprints.admin import admin_emergency_restore
        from config import ADMIN_USERS as _ADMIN
        with app.test_request_context('/api/admin/emergency-restore',
                                       method='POST', json={'confirm': True}):
            from flask import session as _s
            _s['compras_user'] = next(iter(_ADMIN), 'sebastian')
            resp = admin_emergency_restore()
        if isinstance(resp, tuple):
            payload = resp[0].get_json() if hasattr(resp[0], 'get_json') else {}
            code = resp[1]
        else:
            payload = resp.get_json() if hasattr(resp, 'get_json') else {}
            code = getattr(resp, 'status_code', 200)
        resultado['accion'] = 'restaurado'
        resultado['http'] = code
        resultado['restore'] = payload
        log.error('AUTOHEAL · BD restaurada · code=%s · %s', code, str(payload)[:300])
    except Exception as e:
        log.exception('AUTOHEAL · fallo restaurando: %s', e)
        resultado['accion'] = 'error_restaurando'
        resultado['error'] = str(e)[:200]
    return resultado


def job_watcher_health(app):
    """Watcher hourly · ejecuta /api/admin/health/critical-paths internamente
    y manda mail a EMAIL_GERENCIA si status='critical'.

    Sebastián 7-may-2026 (zero-error sprint día 4): el Watcher detecta
    bugs en prod antes que los descubra el usuario. Se ejecuta cada
    hora a :07 (24 entries en JOBS_SCHEDULE con dedup separado).

    Sebastián 16-may-2026: ANTES de chequear paths, corre el auto-healing
    de la BD · si está corrupta se restaura sola del backup.

    Returns: (ok, resumen_dict, _)
    """
    with app.app_context():
        # Auto-healing de BD · primero, porque si la BD está corrupta
        # el resto del watcher no puede consultar nada.
        autoheal = {}
        try:
            autoheal = _db_autoheal_check(app)
        except Exception as e:
            log.exception('autoheal fallo: %s', e)
            autoheal = {'error': str(e)[:200]}
        try:
            # Ejecutar el endpoint internamente (sin HTTP request).
            # Replica la lógica del endpoint admin_health_critical_paths
            # pero sin requerir admin session.
            from blueprints.admin import admin_health_critical_paths
            from flask import session as _s
            with app.test_request_context('/api/admin/health/critical-paths'):
                _s['compras_user'] = 'sistema_watcher'
                _s['_admin_override_for_watcher'] = True
                # Bypass del _require_admin para invocar la función pura
                # · crear admin context manualmente
                from config import ADMIN_USERS as _ADMIN
                _s['compras_user'] = next(iter(_ADMIN), 'sebastian')
                resp = admin_health_critical_paths()
            # resp es Response de Flask · extraer json
            if isinstance(resp, tuple):
                payload, status_code = resp[0].get_json(), resp[1]
            else:
                payload, status_code = resp.get_json(), resp.status_code
            crit_count = (payload or {}).get('critical_count', 0)
            if crit_count > 0:
                # Dedup · solo mandar mail si el set de críticos CAMBIÓ o
                # pasaron >24h. Antes mandaba el MISMO mail cada hora.
                failing = [c['name'] for c in payload.get('checks', [])
                           if c.get('status') == 'critical']
                mail_sent = False
                if _watcher_should_email(failing):
                    _enviar_mail_watcher(payload)
                    mail_sent = True
                return True, {
                    'status': payload.get('status'),
                    'critical_count': crit_count,
                    'warn_count': payload.get('warn_count', 0),
                    'mail_sent': mail_sent,
                    'autoheal': autoheal,
                    'failing_checks': failing,
                }, 0
            # Sin críticos · limpiar el marcador para que un crítico futuro
            # mande mail de inmediato.
            _watcher_clear_email_marker()
            return True, {
                'status': payload.get('status', 'unknown'),
                'critical_count': 0,
                'warn_count': payload.get('warn_count', 0),
                'mail_sent': False,
                'autoheal': autoheal,
            }, 0
        except Exception as e:
            log.exception('watcher_health fallo: %s', e)
            return False, {'error': str(e)[:300]}, 0


def _watcher_should_email(crit_names):
    """Dedup del mail del watcher. Devuelve True solo si el set de checks
    críticos cambió respecto al último mail enviado, o si pasaron >24h.

    Antes el watcher mandaba el MISMO mail cada hora · un crítico persistente
    (ej. last_calendar_sync) generaba ~24 correos/día. Ahora: mail al aparecer
    un crítico nuevo, y a lo sumo un recordatorio diario si persiste."""
    import time as _t
    from config import DB_PATH
    marker = DB_PATH + '.watcher-crit'
    sig = '|'.join(sorted(crit_names))
    ahora = _t.time()
    last_sig, last_ts = '', 0.0
    try:
        if os.path.exists(marker):
            with open(marker) as f:
                raw = (f.read() or '').strip()
            parts = raw.rsplit('::', 1)
            last_sig = parts[0]
            last_ts = float(parts[1]) if len(parts) == 2 else 0.0
    except Exception:
        last_sig, last_ts = '', 0.0
    if sig == last_sig and (ahora - last_ts) <= 24 * 3600:
        return False  # mismo problema, hace <24h · no re-enviar
    try:
        tmp = marker + '.tmp'
        with open(tmp, 'w') as f:
            f.write(f"{sig}::{ahora}")
        os.replace(tmp, marker)
    except Exception:
        pass
    return True


def _watcher_clear_email_marker():
    """Borra el marcador de dedup · tras resolverse los críticos, el próximo
    crítico nuevo debe mandar mail de inmediato."""
    try:
        from config import DB_PATH
        marker = DB_PATH + '.watcher-crit'
        if os.path.exists(marker):
            os.remove(marker)
    except Exception:
        pass


def _enviar_mail_watcher(payload):
    """Manda mail a EMAIL_GERENCIA con los críticos detectados."""
    # ── Correo del watcher DESACTIVADO · Sebastián 17-may-2026 ─────────────
    # "elimina que me lleguen esos mensajes". El watcher SIGUE corriendo:
    # ejecuta los chequeos y el auto-healing de la BD igual. El estado se
    # ve en /admin. Solo se cortó el correo. Reactivar = quitar este return.
    return
    try:
        from notificaciones import SistemaNotificaciones
        import os as _os
        sn = SistemaNotificaciones()
        if not (sn.email_remitente and sn.contraseña):
            log.warning('watcher: sin SMTP config · skip mail')
            return
        gerencia_raw = _os.environ.get('EMAIL_GERENCIA', '').strip()
        if gerencia_raw:
            destinatarios = [e.strip() for e in gerencia_raw.split(',')
                             if e.strip() and '@' in e.strip()]
        else:
            destinatarios = [sn.email_remitente]
        crits = [c for c in payload.get('checks', [])
                 if c.get('status') == 'critical']
        items_html = ''.join([
            f"<li><strong>{c['name']}</strong>: {c['detail']}</li>"
            for c in crits
        ])
        body = f"""<html><body style="font-family:Arial,sans-serif">
        <h2 style="color:#c62828">⚠ Watcher detectó {len(crits)} check(s) crítico(s)</h2>
        <p>Sistema EOS Inventarios · health check hourly.</p>
        <ul>{items_html}</ul>
        <p>Acción sugerida: revisar <a href="https://app.eossuite.com/admin">/admin</a>
        para ver el estado completo.</p>
        <p style="color:#666;font-size:11px">
          Total checks: {payload.get('total_checks')} ·
          Críticos: {payload.get('critical_count')} ·
          Warnings: {payload.get('warn_count')} ·
          OK: {payload.get('ok_count')}
        </p>
        </body></html>"""
        sn.enviar_en_background(
            sn._enviar_email,
            asunto=f"[EOS] Watcher: {len(crits)} check(s) críticos en producción",
            body=body,
            destinatarios=destinatarios,
        )
        log.info(f'watcher: mail enviado a {len(destinatarios)} destinatarios')
    except Exception as e:
        log.warning(f'watcher mail fallo (best-effort): {e}')


def job_validacion_profunda(app):
    """Cron diario 8:00 · ejecuta validacion-profunda y notifica hallazgos.

    Sebastián 8-may-2026 zero-error TIER 1: detección continua. Cada día
    corre los 8 checks matemáticos. Si hay hallazgos NUEVOS de severidad
    alta o media, notifica a Sebastián + responsables.

    Idempotente: si los hallazgos son los mismos que ayer, NO re-notifica
    (anti-spam). Solo notifica deltas.
    """
    with app.app_context():
        try:
            from blueprints.admin import validacion_profunda
            from flask import session as _s
            from config import ADMIN_USERS as _ADMIN
            with app.test_request_context('/api/admin/validacion-profunda'):
                _s['compras_user'] = next(iter(_ADMIN), 'sebastian')
                resp = validacion_profunda()
            if isinstance(resp, tuple):
                payload, status = resp[0].get_json(), resp[1]
            else:
                payload, status = resp.get_json(), resp.status_code

            if status != 200 or not payload.get('ok'):
                return False, {'error': 'validacion-profunda fallo',
                                'status': status}, 0

            score = payload.get('score_real', 0)
            veredicto = payload.get('veredicto_real', '')
            resumen = payload.get('resumen', {})
            alta = resumen.get('alta', 0)
            media = resumen.get('media', 0)

            # Si todo OK · no notificar (anti-spam)
            if alta == 0 and media == 0:
                return True, {'mensaje': 'Validación profunda PERFECTA · sin hallazgos',
                               'score_real': score}, 0

            # Hay hallazgos · notificar al ÁREA RESPONSABLE
            try:
                from blueprints.notif import push_notif_multi
                hallazgos = payload.get('hallazgos', [])
                tipos_alta = list(set(h['tipo'] for h in hallazgos
                                       if h.get('severidad') == 'alta'))
                tipos_media = list(set(h['tipo'] for h in hallazgos
                                        if h.get('severidad') == 'media'))

                # Mapa de tipo → responsable (notif proactiva por área)
                AREA_POR_TIPO = {
                    'MP_NOMBRE_DUPLICADO': ['aseguramiento.espagiria'],
                    'MP_INCI_DUPLICADO': ['aseguramiento.espagiria'],
                    'MP_CODIGO_INCONSISTENTE': ['aseguramiento.espagiria'],
                    'FORMULA_USA_MP_ARCHIVADA': ['tecnica.espagiria', 'sebastian'],
                    'FORMULA_SIN_PRODUCCIONES': ['tecnica.espagiria'],
                    'DESCUENTO_DRIFT_PRODUCCION': ['controlcalidad.espagiria',
                                                     'mayerlin', 'luis'],
                    'TRAZABILIDAD_MOV_SIN_OPERADOR': ['controlcalidad.espagiria'],
                    'TRAZABILIDAD_LOTE_VIVO_SIN_FV': ['controlcalidad.espagiria',
                                                       'tecnica.espagiria'],
                }
                destinatarios_area = set(['sebastian'])  # sebastián siempre
                for h in hallazgos:
                    if h.get('severidad') not in ('alta', 'media'):
                        continue
                    for d in AREA_POR_TIPO.get(h.get('tipo', ''), []):
                        destinatarios_area.add(d)

                titulo = f'🔍 Validación profunda: {veredicto} · score {score}/100'
                cuerpo = []
                if alta > 0:
                    cuerpo.append(f'⚠ {alta} hallazgo(s) ALTA: ' +
                                   ', '.join(tipos_alta[:5]))
                if media > 0:
                    cuerpo.append(f'• {media} hallazgo(s) MEDIA: ' +
                                   ', '.join(tipos_media[:5]))
                cuerpo.append('')
                cuerpo.append(f'Notificado a: {", ".join(sorted(destinatarios_area))}')
                cuerpo.append('Ver detalle: /admin/realidad-cero-error')

                push_notif_multi(
                    sorted(destinatarios_area),
                    'capa', titulo,
                    body='\n'.join(cuerpo),
                    link='/admin/realidad-cero-error',
                    remitente='cron-validacion-profunda',
                    importante=(alta > 0),
                )
            except Exception as e:
                log.warning('validacion_profunda notif fallo: %s', e)

            # Audit log
            try:
                from database import get_db
                from audit_helpers import audit_log
                conn = get_db(); c = conn.cursor()
                audit_log(c, usuario='sistema',
                          accion='VALIDACION_PROFUNDA_DIARIA',
                          tabla=None, registro_id=None,
                          despues={
                              'score_real': score,
                              'veredicto': veredicto,
                              'alta': alta, 'media': media,
                              'tipos_alta': tipos_alta[:10],
                              'tipos_media': tipos_media[:10],
                          },
                          detalle=(f'Validación profunda: {veredicto} · '
                                   f'{alta} alta · {media} media'))
                conn.commit()
            except Exception as e:
                log.warning('validacion_profunda audit fallo: %s', e)

            # Persistir histórico zero-error (gráfica temporal)
            try:
                import json as _json_h
                from database import get_db
                conn_h = get_db(); ch = conn_h.cursor()
                ch.execute("""
                    INSERT INTO audit_zero_error_runs
                      (score_real, veredicto_real, alta, media, baja,
                       detalles_json, origen)
                    VALUES (?, ?, ?, ?, ?, ?, 'cron')
                """, (score, veredicto, alta, media,
                       resumen.get('baja', 0),
                       _json_h.dumps({
                           'tipos_alta': tipos_alta[:20],
                           'tipos_media': tipos_media[:20],
                       })))
                conn_h.commit()
            except Exception as e:
                log.warning('validacion_profunda historial fallo: %s', e)

            return True, {
                'score_real': score,
                'veredicto': veredicto,
                'alta': alta, 'media': media,
            }, 0

        except Exception as e:
            log.exception('validacion_profunda fallo: %s', e)
            return False, {'error': str(e)[:300]}, 0


def job_marcar_vencidos(app):
    """Cron diario 7:50 · marca estado_lote='VENCIDO' en lotes con
    fecha_vencimiento pasada que todavía figuran como VIGENTE.

    Sebastián 8-may-2026 (zero-error FASE A): MPs vencidas con
    estado VIGENTE son violación regulatoria INVIMA · pueden colarse
    en producción si nadie las marca. Antes era acción manual desde
    panel auditoría · ahora corre automático.

    Lógica:
      UPDATE movimientos
      SET estado_lote='VENCIDO'
      WHERE fecha_vencimiento < date('now', '-5 hours')
        AND UPPER(COALESCE(estado_lote,'')) = 'VIGENTE'

    Idempotente: si no hay vencidos, no hace nada. Si los hay,
    audit_log + push_notif a planta/aseguramiento.

    Returns: (ok, {actualizados, top_5_codigos, top_5_lotes}, _)
    """
    with app.app_context():
        from database import get_db
        conn = get_db(); c = conn.cursor()
        try:
            # Detectar primero (para sabermos qué cambió y notificar)
            rows = c.execute("""
                SELECT material_id, lote, fecha_vencimiento, COUNT(*) AS movs
                FROM movimientos
                WHERE fecha_vencimiento IS NOT NULL
                  AND TRIM(fecha_vencimiento) != ''
                  AND date(fecha_vencimiento) < date('now', '-5 hours')
                  AND UPPER(COALESCE(estado_lote,'')) = 'VIGENTE'
                GROUP BY material_id, lote, fecha_vencimiento
                ORDER BY fecha_vencimiento ASC
                LIMIT 200
            """).fetchall()

            if not rows:
                return True, {'mensaje': 'Sin lotes vencidos pendientes · OK'}, 0

            # Marcar VENCIDO en batch (un solo UPDATE para todo)
            res = c.execute("""
                UPDATE movimientos
                SET estado_lote = 'VENCIDO'
                WHERE fecha_vencimiento IS NOT NULL
                  AND TRIM(fecha_vencimiento) != ''
                  AND date(fecha_vencimiento) < date('now', '-5 hours')
                  AND UPPER(COALESCE(estado_lote,'')) = 'VIGENTE'
            """)
            actualizados = res.rowcount

            # Audit log (best-effort · no romper si falla)
            try:
                from audit_helpers import audit_log
                detalles = [
                    {'material_id': r[0], 'lote': r[1],
                     'fecha_venc': r[2], 'movs': r[3]}
                    for r in rows[:50]
                ]
                audit_log(
                    c, usuario='sistema',
                    accion='MARCAR_LOTES_VENCIDOS_AUTO',
                    tabla='movimientos', registro_id='cron',
                    despues={
                        'total_movs_actualizados': actualizados,
                        'lotes_afectados': len(rows),
                        'detalles': detalles,
                    },
                    detalle=(f'Cron diario marcó VENCIDO en {len(rows)} '
                             f'lotes · {actualizados} movimientos'),
                )
            except Exception as e:
                log.warning('marcar_vencidos audit fallo: %s', e)

            conn.commit()

            # Push notif a planta/aseguramiento (best-effort)
            try:
                from blueprints.notif import push_notif_multi
                top_lines = []
                for r in rows[:5]:
                    top_lines.append(f"  · {r[0]} lote {r[1] or '-'} (venc {r[2]})")
                push_notif_multi(
                    ['controlcalidad.espagiria',
                     'aseguramiento.espagiria',
                     'mayerlin',  # dispensación
                     'sebastian'],
                    'capa',
                    f'⛔ {len(rows)} lote(s) marcados VENCIDO automático',
                    body=('Cron diario detectó lotes con fecha_venc pasada '
                          'que seguían VIGENTE. Ya están bloqueados.\n\n'
                          'Top 5:\n' + '\n'.join(top_lines)),
                    link='/admin/limpieza-cero-error',
                    remitente='cron-vencidos',
                    importante=True,
                )
            except Exception as e:
                log.warning('marcar_vencidos push_notif fallo: %s', e)

            return True, {
                'actualizados': actualizados,
                'lotes_afectados': len(rows),
                'top_codigos': [r[0] for r in rows[:5]],
                'top_lotes': [r[1] for r in rows[:5]],
            }, 0

        except Exception as e:
            conn.rollback()
            log.exception('marcar_vencidos fallo: %s', e)
            return False, {'error': str(e)[:300]}, 0


def job_mailbox_factura_proveedor(app):
    """Sebastián 22-may-2026 · cron diario 7:15 AM · IMAP inbox compras.

    Lee inbox compras@hhagroup.co (env IMAP_HOST/IMAP_USER/IMAP_PASSWORD),
    descarga adjuntos PDF/JPG/PNG, intenta matching por:
      1. Asunto contiene OC-2026-NNNN (regex)
      2. Body contiene número de OC
      3. NIT del remitente coincide con proveedor

    Si match → INSERT pagos_oc con comprobante_imagen=base64(adjunto)
    Si no → guarda en bandeja_facturas_huerfanas para revisión manual

    SOLO corre si IMAP_HOST + IMAP_USER + IMAP_PASSWORD configurados.
    Sin esas envs · retorna early sin error · no log noise.
    """
    import os as _os, imaplib, email as _email, re as _re, base64 as _b64
    host = _os.environ.get('IMAP_HOST', '').strip()
    user = _os.environ.get('IMAP_USER', '').strip()
    pwd  = _os.environ.get('IMAP_PASSWORD', '').strip()
    if not (host and user and pwd):
        log.debug('[mailbox-factura] skip · IMAP_* env vars no configurados')
        return True, {'skipped': True, 'razon': 'IMAP env vars no configurados'}, 0

    with app.app_context():
        from database import get_db as _gdb
        conn = _gdb(); c = conn.cursor()
        try:
            imap = imaplib.IMAP4_SSL(host)
            imap.login(user, pwd)
            imap.select('INBOX')
            # Buscar UNSEEN últimos 7 días
            from datetime import datetime as _dt2, timedelta as _td2
            since = (_dt2.now() - _td2(days=7)).strftime('%d-%b-%Y')
            _, data = imap.search(None, f'(UNSEEN SINCE "{since}")')
            ids = data[0].split() if data and data[0] else []
            procesadas = 0
            matched = 0
            huerfanas = 0
            re_oc = _re.compile(r'\bOC-\d{4}-\d{4}\b', _re.I)
            for msg_id in ids[:50]:  # tope 50 por run
                _, msg_data = imap.fetch(msg_id, '(RFC822)')
                if not msg_data or not msg_data[0]:
                    continue
                msg = _email.message_from_bytes(msg_data[0][1])
                from_addr = msg.get('From', '')
                subject = (msg.get('Subject', '') or '')
                # Match OC en asunto o body
                oc_match = re_oc.search(subject)
                body_text = ''
                for part in msg.walk():
                    if part.get_content_type() == 'text/plain':
                        try:
                            body_text = part.get_payload(decode=True).decode('utf-8', 'replace')
                            if not oc_match:
                                oc_match = re_oc.search(body_text)
                            break
                        except Exception:
                            pass
                numero_oc = oc_match.group(0).upper() if oc_match else None
                # Extraer adjuntos
                for part in msg.walk():
                    fn = part.get_filename()
                    if not fn:
                        continue
                    ct = part.get_content_type()
                    if ct not in ('application/pdf', 'image/jpeg', 'image/png', 'image/jpg'):
                        continue
                    try:
                        payload = part.get_payload(decode=True)
                        b64 = 'data:' + ct + ';base64,' + _b64.b64encode(payload).decode('ascii')
                    except Exception:
                        continue
                    procesadas += 1
                    if numero_oc:
                        # Verificar OC existe
                        _row_oc = c.execute(
                            "SELECT 1 FROM ordenes_compra WHERE numero_oc=?",
                            (numero_oc,),
                        ).fetchone()
                        if _row_oc:
                            # INSERT pagos_oc · pago provisional sin monto · admin completa
                            try:
                                c.execute(
                                    """INSERT INTO pagos_oc
                                       (numero_oc, fecha, monto, medio, referencia,
                                        comprobante_imagen, numero_factura_proveedor,
                                        creado_por, observaciones)
                                       VALUES (?, datetime('now','-5 hours'), 0,
                                               'PENDIENTE', '', ?, ?,
                                               'cron-mailbox',
                                               'Adjunto auto-detectado · revisar monto')""",
                                    (numero_oc, b64[:5_000_000], fn),  # limit 5MB
                                )
                                matched += 1
                            except Exception as _e:
                                log.warning('[mailbox] insert pagos_oc fallo: %s', _e)
                                huerfanas += 1
                        else:
                            huerfanas += 1
                    else:
                        huerfanas += 1
                # Marcar mail como Seen
                try:
                    imap.store(msg_id, '+FLAGS', '\\Seen')
                except Exception:
                    pass
            conn.commit()
            try:
                imap.logout()
            except Exception:
                pass
            return True, {
                'mails_procesados': len(ids),
                'adjuntos_procesados': procesadas,
                'matched_a_oc': matched,
                'huerfanas': huerfanas,
            }, 0
        except Exception as e:
            log.warning('[mailbox-factura] fallo: %s', e)
            return False, {'error': str(e)[:200]}, 0


def job_mee_drift_sync(app):
    """Sebastián 21-may-2026 · cron diario 3:00 AM · sync MEE cache vs movimientos.

    `maestro_mee.stock_actual` es cache derivable. Antes había riesgo de drift
    cuando UPDATE de cache fallaba pero INSERT movimiento sí · este cron
    detecta drift > 0.5g y resincroniza desde SUM(movimientos_mee).
    """
    with app.app_context():
        from database import get_db as _gdb
        conn = _gdb(); c = conn.cursor()
        try:
            rows = c.execute(
                "SELECT codigo, COALESCE(stock_actual,0) FROM maestro_mee "
                "WHERE COALESCE(estado,'Activo')='Activo'",
            ).fetchall()
        except Exception as e:
            return False, {'error': str(e)[:200]}, 0
        drift_count = 0
        drift_codes = []
        for cod, cache_val in rows:
            try:
                sum_row = c.execute(
                    """SELECT COALESCE(SUM(CASE
                           WHEN tipo='Entrada' THEN cantidad
                           WHEN tipo='Salida'  THEN -cantidad
                           WHEN tipo='Ajuste'  THEN cantidad
                           ELSE 0 END), 0)
                       FROM movimientos_mee WHERE mee_codigo=? AND COALESCE(anulado,0)=0""",
                    (cod,),
                ).fetchone()
                real = max(float(sum_row[0] or 0), 0)
                cache_f = float(cache_val or 0)
                if abs(real - cache_f) > 0.5:
                    c.execute(
                        "UPDATE maestro_mee SET stock_actual=? WHERE codigo=?",
                        (real, cod),
                    )
                    # INVIMA-FIX · 22-may-2026 · Bug #3 audit Crons · audit_log obligatorio
                    # · Antes: drift "reparado" silente sin huella · viola CLAUDE.md
                    try:
                        from audit_helpers import audit_log as _alog
                        _alog(c, usuario='cron-mee-drift', accion='MEE_DRIFT_RESYNC',
                              tabla='maestro_mee', registro_id=cod,
                              antes={'stock_actual': cache_f},
                              despues={'stock_actual': real, 'delta': real - cache_f})
                    except Exception:
                        pass
                    drift_count += 1
                    if len(drift_codes) < 10:
                        drift_codes.append({'codigo': cod, 'cache': cache_f, 'real': real})
            except Exception:
                continue
        try:
            conn.commit()
        except Exception:
            pass
        log.info('[mee_drift_sync] reparados=%d', drift_count)
        return True, {'reparados': drift_count, 'top_drift': drift_codes}, 0


def job_pqr_sla_vencido(app):
    """Sebastián 21-may-2026 · cron diario 8:15 AM · PQR vencidos SLA.

    Ley 1755/2015 CO · responder PQR en plazos legales.
    Notif a Calidad + Sebastián con PQRs cuyo sla_vence_at_utc < ahora.
    """
    with app.app_context():
        from database import get_db as _gdb
        conn = _gdb(); c = conn.cursor()
        # SEC-FIX · 22-may-2026 · estado real es 'en_revision' (no 'en_progreso')
        # · Bug #5 audit Despachos · cron filtraba estado inexistente · alertas
        #   legales Ley 1755/2015 NUNCA llegaban a tiempo cuando Calidad ponía
        #   PQR en revisión.
        try:
            rows = c.execute(
                """SELECT id, cliente_nombre, tipo, titulo, sla_vence_at_utc
                   FROM portal_pqr
                   WHERE estado IN ('abierto','en_revision')
                     AND sla_vence_at_utc IS NOT NULL
                     AND sla_vence_at_utc != ''
                     AND datetime(sla_vence_at_utc) < datetime('now','utc')
                   ORDER BY sla_vence_at_utc ASC LIMIT 50""",
            ).fetchall()
        except Exception as e:
            return False, {'error': f'query fallo: {e}'}, 0
        if not rows:
            return True, {'mensaje': 'Sin PQR SLA vencidos'}, 0
        try:
            from blueprints.notif import push_notif_multi
            from config import CALIDAD_USERS as _CU
            destinatarios = list({'sebastian'} | set(_CU))
            partes = [f'⚠ {len(rows)} PQR con SLA VENCIDO (Ley 1755/2015):']
            for r in rows[:10]:
                partes.append(f'  · {r[2].upper()} #{r[0]} · {r[1]} · {(r[3] or "")[:60]} · venció {r[4]}')
            push_notif_multi(
                destinatarios, 'pqr',
                f'🚨 {len(rows)} PQR con SLA legal vencido',
                body='\n'.join(partes),
                link='/admin/portal/pqr',
                remitente='cron-pqr-sla',
                importante=True,
            )
        except Exception as _e:
            log.warning('pqr_sla notif fallo: %s', _e)
        return True, {'pqr_vencidos': len(rows)}, 0


def _generar_codigo_mp_siguiente(c):
    """SHOPIFY-FIX · 22-may-2026 · generar próximo código MP00NNNN.

    Lee MAX(numero) de los códigos MP00xxxxx existentes y devuelve el siguiente.
    """
    try:
        row = c.execute(
            """SELECT MAX(CAST(SUBSTR(codigo_mp, 3) AS INTEGER))
               FROM maestro_mps
               WHERE codigo_mp LIKE 'MP%' AND LENGTH(codigo_mp) >= 6"""
        ).fetchone()
        max_n = int(row[0] or 0) if row else 0
    except Exception:
        max_n = 0
    return f'MP{max_n + 1:05d}'


def job_auto_normalizar_formulas(app):
    """Sebastián 22-may-2026 · cron diario 4:30 AM (post auto_reparar_huerfanas).

    Detecta materiales en formula_items con nombre/código que NO matchea
    con maestro_mps · usa mp_aliases para auto-normalizar.

    FLUJO 22-may-2026 actualizado · Sebastián: 'quedamos en que las ibas a crear':
      1. Para cada alias detectado en formula_items:
         a) Si NO existe MP con ese INCI → CREAR MP automáticamente
         b) UPDATE formula_items para vincular al MP nuevo/existente
      2. Notif resumen a Sebastián con count creados + normalizados
    """
    with app.app_context():
        from database import get_db as _gdb
        conn = _gdb(); c = conn.cursor()

        # Aliases cargados
        aliases_dict = {}
        try:
            for al, inci in c.execute(
                "SELECT alias, nombre_inci_canonical FROM mp_aliases WHERE COALESCE(activo,1)=1"
            ).fetchall():
                aliases_dict[al.lower().strip()] = inci
        except Exception:
            return False, {'error': 'mp_aliases tabla no existe · mig 158 no aplicada'}, 0

        # MPs por nombre (INCI + nombre_comercial) · ambos campos pueden contener
        # la abreviatura histórica (caso MP00169 con nombre_inci='SAP').
        # FIX · 22-may-2026 noche · antes solo indexaba nombre_inci · si MP existente
        # tenía la abreviatura en nombre_inci, el cron no la detectaba y CREABA DUPLICADO.
        mp_por_nombre = {}  # lower(nombre) -> (codigo_mp, nombre_actual)
        try:
            for cod, inci, com, activo in c.execute(
                """SELECT codigo_mp, COALESCE(nombre_inci,''),
                          COALESCE(nombre_comercial,''), COALESCE(activo,1)
                   FROM maestro_mps"""
            ).fetchall():
                if not activo:
                    continue
                if inci:
                    mp_por_nombre.setdefault(inci.lower().strip(), (cod, inci))
                if com:
                    mp_por_nombre.setdefault(com.lower().strip(), (cod, com))
        except Exception:
            pass

        # Materiales únicos en formula_items
        rows_form = c.execute(
            """SELECT DISTINCT material_id, material_nombre FROM formula_items
               WHERE COALESCE(material_nombre,'')!=''"""
        ).fetchall()

        normalizados = 0
        mps_creados = []     # MPs creados automáticamente
        mps_renombrados = [] # MPs existentes renombrados de abreviatura a INCI canonical
        sin_alias = []       # casos sin alias conocido · skip
        for mat_id, mat_nom in rows_form:
            nom_lower = (mat_nom or '').lower().strip()
            alias_inci = aliases_dict.get(nom_lower)
            if not alias_inci:
                continue  # no es abreviatura conocida · skip silente
            alias_lower = alias_inci.lower().strip()
            mp_match = mp_por_nombre.get(alias_lower)
            if not mp_match:
                # Match parcial INCI canonical (p.ej. alias 'HA' -> 'Hyaluronic Acid'
                # y existe MP 'Hyaluronic Acid Low Molecular Weight')
                for k, v in mp_por_nombre.items():
                    if alias_lower in k:
                        mp_match = v
                        break
            # FIX · 22-may-2026 noche · RENOMBRAR antes de CREAR · evita duplicados.
            # · Caso MP00169 SAP: MP existente activa cuyo nombre_inci='SAP' (abreviatura).
            # · Antes este cron creaba un MP nuevo con 'Sodium Ascorbyl Phosphate' al lado.
            # · Ahora: si encontramos un MP existente cuyo nombre coincida con la abreviatura
            #   literal, lo renombramos al INCI canonical.
            if not mp_match:
                mp_match_abrev = mp_por_nombre.get(nom_lower)
                if mp_match_abrev:
                    cod_exist, nom_exist = mp_match_abrev
                    try:
                        c.execute(
                            """UPDATE maestro_mps
                               SET nombre_inci=?, nombre_comercial=?
                               WHERE codigo_mp=?""",
                            (alias_inci, alias_inci, cod_exist),
                        )
                        try:
                            from audit_helpers import audit_log as _alog
                            _alog(c, usuario='cron-normalizar-formulas',
                                  accion='AUTO_RENOMBRAR_MP_DESDE_ALIAS',
                                  tabla='maestro_mps', registro_id=cod_exist,
                                  antes={'nombre_inci_o_comercial': nom_exist},
                                  despues={'nombre_inci': alias_inci,
                                           'nombre_comercial': alias_inci,
                                           'razon': f'renombrar desde abreviatura {mat_nom} a INCI canonical (zero-error · evita duplicar MP)'})
                        except Exception:
                            pass
                        mp_match = (cod_exist, alias_inci)
                        mp_por_nombre[alias_lower] = mp_match  # actualizar mapa para iteraciones
                        mps_renombrados.append({
                            'codigo_mp': cod_exist,
                            'alias_origen': nom_exist,
                            'nombre_inci': alias_inci,
                        })
                    except Exception as e:
                        log.warning('[normalizar-formulas] renombrar MP %s fallo: %s',
                                    cod_exist, e)
            # CREAR MP automáticamente solo si no existe ni canonical ni abreviado
            # · Sebastián: 'quedamos en que las ibas a crear'
            if not mp_match:
                try:
                    cod_new = _generar_codigo_mp_siguiente(c)
                    c.execute(
                        """INSERT INTO maestro_mps
                           (codigo_mp, nombre_inci, nombre_comercial, tipo,
                            tipo_material, proveedor, stock_minimo,
                            precio_referencia, activo)
                           VALUES (?, ?, ?, 'Sin clasificar', 'MP',
                                   '(por asignar)', 0, 0, 1)""",
                        (cod_new, alias_inci, alias_inci),
                    )
                    try:
                        from audit_helpers import audit_log as _alog
                        _alog(c, usuario='cron-normalizar-formulas',
                              accion='AUTO_CREAR_MP_DESDE_ALIAS',
                              tabla='maestro_mps', registro_id=cod_new,
                              despues={'codigo_mp': cod_new,
                                       'nombre_inci': alias_inci,
                                       'razon': f'auto-creado por abbreviatura {mat_nom} en fórmula',
                                       'observacion': 'completar proveedor + precio + stock_minimo'})
                    except Exception:
                        pass
                    # Registrar para próxima iteración + reporte
                    mp_por_nombre[alias_lower] = (cod_new, alias_inci)
                    mp_match = (cod_new, alias_inci)
                    mps_creados.append({
                        'codigo_mp': cod_new,
                        'alias_origen': mat_nom,
                        'nombre_inci': alias_inci,
                    })
                except Exception as e:
                    log.warning('[normalizar-formulas] crear MP %s fallo: %s',
                                alias_inci, e)
                    continue
            cod_new, nom_new = mp_match
            try:
                c.execute(
                    """UPDATE formula_items
                       SET material_id=?, material_nombre=?
                       WHERE COALESCE(material_id,'')=? AND material_nombre=?""",
                    (cod_new, nom_new, mat_id or '', mat_nom),
                )
                if c.rowcount > 0:
                    normalizados += c.rowcount
                    try:
                        from audit_helpers import audit_log as _alog
                        _alog(c, usuario='cron-normalizar-formulas',
                              accion='AUTO_NORMALIZAR_FORMULA_MP',
                              tabla='formula_items',
                              registro_id=f'{mat_id}/{mat_nom}',
                              antes={'material_id': mat_id, 'material_nombre': mat_nom},
                              despues={'material_id': cod_new, 'material_nombre': nom_new})
                    except Exception:
                        pass
            except Exception as e:
                log.warning('[normalizar-formulas] %s/%s fallo: %s', mat_id, mat_nom, e)
        try:
            conn.commit()
        except Exception:
            pass

        # Notif a Sebastián con resumen
        if mps_creados or mps_renombrados or normalizados:
            try:
                from blueprints.notif import push_notif
                from config import ADMIN_USERS
                cuerpo_parts = []
                if mps_renombrados:
                    sample = ', '.join(
                        f"{m['codigo_mp']}:{m['alias_origen']}→{m['nombre_inci']}"
                        for m in mps_renombrados[:5]
                    )
                    cuerpo_parts.append(
                        f'♻️ {len(mps_renombrados)} MPs renombrados (abreviatura→INCI): {sample}'
                        + ('...' if len(mps_renombrados) > 5 else '')
                    )
                if mps_creados:
                    sample = ', '.join(f"{m['alias_origen']}→{m['nombre_inci']}" for m in mps_creados[:5])
                    cuerpo_parts.append(
                        f'✅ {len(mps_creados)} MPs creados automáticamente: {sample}'
                        + ('...' if len(mps_creados) > 5 else '')
                    )
                if normalizados:
                    cuerpo_parts.append(f'🔧 {normalizados} fórmulas normalizadas')
                if mps_creados:
                    cuerpo_parts.append('Completá proveedor + precio + stock_minimo en cada MP nuevo.')
                cuerpo = ' · '.join(cuerpo_parts)
                for u in (ADMIN_USERS or set()):
                    try:
                        push_notif(destinatario=u, tipo='normalizar_formulas_ok',
                                   titulo='🔧 Fórmulas normalizadas + MPs creados/renombrados',
                                   cuerpo=cuerpo,
                                   link='/dashboard#inventario',
                                   remitente='cron-normalizar-formulas',
                                   importante=bool(mps_creados or mps_renombrados))
                    except Exception:
                        pass
            except Exception:
                pass

        return True, {
            'normalizados': normalizados,
            'mps_creados': len(mps_creados),
            'mps_creados_detalle': mps_creados[:30],
            'mps_renombrados': len(mps_renombrados),
            'mps_renombrados_detalle': mps_renombrados[:30],
            'aliases_cargados': len(aliases_dict),
            'mps_disponibles_por_nombre': len(mp_por_nombre),
        }, 0


def job_auto_reparar_huerfanas(app):
    """Sebastián 21-may-2026 · cron diario 4:00 AM.

    Detecta fórmulas con `formula_items.material_id` huérfano (apunta a un
    código que no tiene lotes en movimientos) y las repara automáticamente
    apuntándolas al MP correcto (mismo nombre/INCI · con stock real).

    Causa raíz: cuando se unifican MPs duplicados, las fórmulas que tenían
    el código viejo quedan huérfanas → "Stock insuficiente · hay 0g".
    Antes había que correr el repair manualmente desde UI.
    """
    with app.app_context():
        from database import get_db as _gdb
        conn = _gdb(); c = conn.cursor()
        try:
            rows = c.execute("""
                SELECT DISTINCT fi.material_id, fi.material_nombre
                FROM formula_items fi
                WHERE fi.material_id IS NOT NULL AND fi.material_id != ''
                  AND NOT EXISTS (
                    SELECT 1 FROM movimientos m
                    WHERE m.material_id = fi.material_id
                  )
            """).fetchall()
            huerfanos = [(r[0], r[1] or '') for r in rows]
        except Exception as e:
            log.exception('auto_reparar_huerfanas detectar fallo')
            return False, {'error': str(e)[:200]}, 0
        if not huerfanos:
            return True, {'huerfanos': 0, 'reparados': 0}, 0
        reparados = 0
        log.info('[auto_reparar_huerfanas] detectados %d codigos huerfanos', len(huerfanos))
        for cod_huerfano, nombre_huerfano in huerfanos:
            if not nombre_huerfano:
                continue
            try:
                # SEC-FIX · 21-may-2026 · ORDER BY determinístico (antes era random)
                # + audit_log obligatorio (modifica data INVIMA-regulada)
                # ORDER BY (stock DESC, codigo_mp ASC) garantiza mismo resultado
                # entre corridas · audit_log permite reconstruir cambios.
                cand = c.execute("""
                    SELECT m.codigo_mp, m.nombre_comercial,
                           (SELECT COALESCE(SUM(CASE WHEN mv.tipo='Entrada' THEN mv.cantidad ELSE -mv.cantidad END), 0)
                            FROM movimientos mv WHERE mv.material_id = m.codigo_mp) AS stock_g
                    FROM maestro_mps m
                    WHERE COALESCE(m.activo,1)=1
                      AND m.codigo_mp != ?
                      AND (
                        LOWER(m.nombre_comercial) = LOWER(?)
                        OR LOWER(m.nombre_inci) = LOWER(?)
                      )
                      AND EXISTS (
                        SELECT 1 FROM movimientos mv2 WHERE mv2.material_id = m.codigo_mp
                      )
                    ORDER BY stock_g DESC, m.codigo_mp ASC
                    LIMIT 1
                """, (cod_huerfano, nombre_huerfano, nombre_huerfano)).fetchone()
                if cand:
                    c.execute("""
                        UPDATE formula_items SET material_id=?, material_nombre=?
                        WHERE material_id=?
                    """, (cand[0], cand[1] or nombre_huerfano, cod_huerfano))
                    reparados += 1
                    log.info('[auto_reparar_huerfanas] %s -> %s (%s · stock=%s)',
                             cod_huerfano, cand[0], nombre_huerfano, cand[2])
                    # audit_log INVIMA-required
                    try:
                        from audit_helpers import audit_log as _audit
                        _audit(c, usuario='cron-auto-repair',
                              accion='REPARAR_HUERFANO_FORMULA',
                              tabla='formula_items',
                              registro_id=cod_huerfano,
                              antes={'material_id': cod_huerfano, 'nombre': nombre_huerfano},
                              despues={'material_id': cand[0], 'nombre': cand[1] or nombre_huerfano, 'stock_disponible': float(cand[2] or 0)})
                    except Exception as _ae:
                        log.warning('[auto_reparar_huerfanas] audit fallo: %s', _ae)
            except Exception as e:
                log.warning('[auto_reparar_huerfanas] %s fallo: %s', cod_huerfano, e)
                continue
        try:
            conn.commit()
        except Exception:
            try: conn.rollback()
            except Exception: pass
        return True, {
            'huerfanos_detectados': len(huerfanos),
            'reparados_auto': reparados,
            'pendientes_manual': len(huerfanos) - reparados,
        }, 0


def _loop_multi_cron(app):
    """Loop cada 5 min revisa schedule de jobs y ejecuta los que apliquen.

    Sebastián 1-may-2026 audit zero-error: incorporar lock distribuido
    `cron_locks` para prevenir doble ejecución cuando hay >1 worker.
    """
    log.info(f'[multi-cron] Loop iniciado · {len(JOBS_SCHEDULE)} jobs configurados')
    import time as _time
    import time as time_mod
    from datetime import datetime as _dt
    while True:
        try:
            # FIX · 22-may-2026 · Bug #9 audit Crons · NO reusar conn entre jobs
            # · Antes: app_context global · 30 jobs compartían conn · PG tx 5min abierta
            # · Ahora: app_context para SELECT schedule sólo · cada job tiene su context
            with app.app_context():
                from database import get_db
                conn = get_db()
                ahora = _dt.now()
                # BUG-14 fix · 19-may-2026 audit Planta PERFECTA: jobs
                # NO idempotentes (insertan producciones, mandan emails)
                # no deben re-ejecutarse a las 2h tras fallo · subir a 24h
                # mitiga duplicación hasta que cada paso sea idempotente.
                # FIX · 22-may-2026 · Bug #1 audit Crons · jobs NO idempotentes
                # · Antes: solo lunes_7am_workflow · resto retry 2h → SCs duplicadas
                # · Ahora: TODOS los jobs que insertan/mutan datos críticos a 24h
                _RETRY_24H_JOBS = {
                    'lunes_7am_workflow',
                    'auto_sc_mensual', 'auto_sc_mee_mensual', 'auto_sc_urgente_lun',
                    'auto_d20',                     # crea SCs decoración
                    'reconciliar_influencer_60d',   # UPDATE masivo
                    'marcar_vencidos',              # notif + UPDATE estado_lote
                    'auto_reparar_huerfanas',       # UPDATE formula_items
                    'auto_normalizar_formulas',     # UPDATE formula_items
                    'mee_drift_sync',               # UPDATE stock_actual
                }
                for job_name, hora, minuto, dias_sem, dias_mes, callable_name in JOBS_SCHEDULE:
                    if not _es_hora_de(ahora, hora, minuto, dias_sem, dias_mes):
                        continue
                    _retry_h = 24 if job_name in _RETRY_24H_JOBS else 2
                    if _ya_ejecutado_hoy(conn, job_name, retry_si_fallo_horas=_retry_h):
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


def job_resumen_ejecutivo_noche(app):
    """OLA 3 IA · 20-may-2026 · resumen del día a 19:00.

    Compara plan vs realidad del día. Detecta anomalías. Manda campana
    in-app a Sebastián + Alejandro con el highlight del día. Si hay
    ANTHROPIC_API_KEY, redacta con Claude · sin key usa template fijo.
    """
    with app.app_context():
        from database import get_db
        conn = get_db(); c = conn.cursor()
        try:
            hoy = c.execute("SELECT date('now','-5 hours')").fetchone()[0]
        except Exception:
            from datetime import date as _d
            hoy = _d.today().isoformat()
        # Stats del día
        try:
            row = c.execute(
                """SELECT
                   SUM(CASE WHEN date(fecha_programada)=? THEN 1 ELSE 0 END) as planeadas,
                   SUM(CASE WHEN date(fecha_programada)=? AND inicio_real_at IS NOT NULL THEN 1 ELSE 0 END) as iniciadas,
                   SUM(CASE WHEN date(fecha_programada)=? AND fin_real_at IS NOT NULL THEN 1 ELSE 0 END) as terminadas,
                   SUM(CASE WHEN date(fecha_programada)=? AND LOWER(COALESCE(estado,''))='cancelado' THEN 1 ELSE 0 END) as canceladas,
                   COALESCE(SUM(CASE WHEN date(fecha_programada)=? AND fin_real_at IS NOT NULL
                                       THEN COALESCE(kg_real,cantidad_kg,0) ELSE 0 END),0) as kg_real
                   FROM produccion_programada""",
                (hoy, hoy, hoy, hoy, hoy),
            ).fetchone()
            planeadas, iniciadas, terminadas, canceladas, kg_real = row
        except Exception as e:
            return False, {'error': f'stats fallo: {e}'}, ''
        # Andon abiertas + salas sucias
        try:
            andon_abiertas = c.execute(
                "SELECT COUNT(*) FROM andon_alertas WHERE estado IN ('abierta','en_atencion')",
            ).fetchone()[0]
        except Exception:
            andon_abiertas = 0
        try:
            salas_sucias = c.execute(
                "SELECT COUNT(*) FROM areas_planta WHERE COALESCE(activo,1)=1 "
                "AND tipo='produccion' AND estado='sucia'",
            ).fetchone()[0]
        except Exception:
            salas_sucias = 0
        # Render mensaje
        cum_pct = round((terminadas / planeadas * 100) if planeadas else 0, 0)
        emoji = '✅' if cum_pct >= 80 else ('⚠️' if cum_pct >= 50 else '🔴')
        cuerpo = (
            f'{emoji} {hoy} · Cumplimiento {cum_pct}% '
            f'({terminadas}/{planeadas} producciones · {kg_real:.0f}kg). '
            f'En curso: {max(0, iniciadas - terminadas)}. '
            f'ANDON sin resolver: {andon_abiertas}. '
            f'Salas sucias: {salas_sucias}.'
        )
        if canceladas > 0:
            cuerpo += f' Canceladas: {canceladas}.'
        # Push a admins (sin email · directiva CLAUDE.md)
        try:
            from blueprints.notif import push_notif
            from config import ADMIN_USERS
            importante = (cum_pct < 50) or (andon_abiertas >= 3)
            for u in (ADMIN_USERS or set()):
                try:
                    push_notif(
                        destinatario=u,
                        tipo='resumen_ejecutivo_noche',
                        titulo=f'📊 Resumen planta · {hoy}',
                        body=cuerpo,
                        link='/dashboard#programacion',
                        remitente='sistema',
                        importante=importante,
                    )
                except Exception:
                    pass
        except Exception as e:
            log.warning('push resumen_ejecutivo fallo: %s', e)
        # audit
        try:
            c.execute(
                """INSERT INTO audit_log (usuario,accion,tabla,registro_id,detalle,ip,fecha)
                   VALUES ('sistema','RESUMEN_EJECUTIVO_NOCHE','_',?,?,'',datetime('now','-5 hours'))""",
                (hoy, cuerpo[:500]),
            )
            conn.commit()
        except Exception:
            pass
        return True, {
            'fecha': hoy, 'planeadas': planeadas, 'terminadas': terminadas,
            'iniciadas': iniciadas, 'canceladas': canceladas,
            'kg_real': kg_real, 'cumplimiento_pct': cum_pct,
            'andon_abiertas': andon_abiertas, 'salas_sucias': salas_sucias,
        }, cuerpo


def job_reconciliar_influencer_60d(app):
    """Sprint Compras N3 · 21-may-2026 · cron diario 9:00.

    Cierra SOLs influencer/CC en estado 'Aprobada' con más de 60 días
    sin pago (no se encontró pago en la tabla pagos_oc/oc-pago). Manda
    resumen a admins via push_notif. INV-1: solo toca categoría
    Influencer/Marketing Digital o Cuenta de Cobro.
    """
    with app.app_context():
        from database import get_db
        conn = get_db(); c = conn.cursor()
        # PG-FIX · 21-may-2026 · date('now','-5 hours','-60 days') con 3 args
        # rompe en PostgreSQL (pg_compat solo traduce mono-arg). Calculamos
        # cutoff en Python y lo pasamos como param literal.
        from datetime import datetime as _dtcron, timedelta as _tdcron
        _cutoff = (_dtcron.now() - _tdcron(days=60)).date().isoformat()
        try:
            rows = c.execute(
                """SELECT s.numero, s.solicitante, s.fecha, s.numero_oc,
                          COALESCE(s.valor,0)
                   FROM solicitudes_compra s
                   WHERE s.estado = 'Aprobada'
                     AND s.categoria IN ('Influencer/Marketing Digital','Cuenta de Cobro')
                     AND date(s.fecha) < ?
                   ORDER BY s.fecha ASC LIMIT 200""",
                (_cutoff,),
            ).fetchall()
        except Exception as e:
            return False, {'error': f'query fallo: {e}'}, ''
        cerradas = []
        for r in rows:
            numero, solicitante, fecha, oc, valor = r
            # ¿Tiene pago registrado en pagos_oc?
            pagado = False
            if oc:
                try:
                    p = c.execute(
                        "SELECT 1 FROM pagos_oc WHERE numero_oc=? LIMIT 1",
                        (oc,),
                    ).fetchone()
                    if p:
                        pagado = True
                except Exception:
                    pass
            if pagado:
                continue
            # Cerrar como Reconciliada
            try:
                c.execute(
                    "UPDATE solicitudes_compra SET estado='Reconciliada', "
                    "observaciones=COALESCE(observaciones,'') || "
                    "' · Auto-reconciliada >60d sin pago (cron 9:00)' "
                    "WHERE numero=?",
                    (numero,),
                )
                # FIX · 22-may-2026 · Bug #4 audit Crons · audit per-row (no _BULK_)
                # · Antes: 1 audit_log con registro_id='_BULK_' y count global
                # · Ahora: 1 audit_log per SOL · permite reconstruir quién cerró qué
                try:
                    from audit_helpers import audit_log as _alog
                    _alog(c, usuario='cron-reconciliar-influencer',
                          accion='AUTO_RECONCILIAR_60D',
                          tabla='solicitudes_compra', registro_id=numero,
                          antes={'estado': 'Aprobada'},
                          despues={'estado': 'Reconciliada',
                                   'razon': '>60d sin pago',
                                   'solicitante': solicitante, 'valor': valor})
                except Exception:
                    pass
                cerradas.append({'numero': numero, 'solicitante': solicitante,
                                 'fecha': fecha, 'valor': valor})
            except Exception:
                continue
        # Notif a admins si hay cierres
        if cerradas:
            try:
                from blueprints.notif import push_notif
                from config import ADMIN_USERS
                cuerpo = (
                    f'🧹 {len(cerradas)} SOL(s) influencer auto-cerradas '
                    f'(>60 días sin pago) · revisar lista en Compras → Influencers.'
                )
                for u in (ADMIN_USERS or set()):
                    try:
                        push_notif(
                            destinatario=u,
                            tipo='reconciliar_influencer',
                            titulo='🧹 Reconciliación influencers',
                            body=cuerpo,
                            link='/compras',
                            remitente='sistema',
                        )
                    except Exception:
                        pass
            except Exception:
                pass
        # Audit
        try:
            from datetime import datetime as _dt
            now = _dt.now().strftime('%Y-%m-%d %H:%M:%S')
            c.execute(
                "INSERT INTO audit_log (usuario, accion, tabla, registro_id, detalle, ip, fecha) "
                "VALUES ('sistema','RECONCILIAR_INFLUENCER_60D','solicitudes_compra','_BULK_',?,'',?)",
                (f'cerradas={len(cerradas)}', now),
            )
        except Exception:
            pass
        conn.commit()
        return True, {'cerradas': len(cerradas),
                      'detalle': cerradas[:20]}, f'{len(cerradas)} reconciliadas'


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
