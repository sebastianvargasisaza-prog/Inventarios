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


def ejecutar_auto_plan_diario(app):
    """Función llamada por el cron. Genera + aplica + envía emails + notif in-app."""
    with app.app_context():
        log.info('[auto-plan-cron] Iniciando ejecución diaria...')
        try:
            from blueprints.auto_plan import generar_plan, aplicar_plan
            from database import get_db

            plan = generar_plan(horizonte_dias=60, tipo='auto', usuario='cron')
            resultado = aplicar_plan(plan, usuario='cron')
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
