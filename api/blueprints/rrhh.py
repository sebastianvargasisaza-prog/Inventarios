# blueprints/rrhh.py — extraído de index.py (Fase C)
import os
import json
import sqlite3
import hmac
import time
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, Response, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from config import DB_PATH, COMPRAS_USERS, ADMIN_USERS, CONTADORA_USERS, RRHH_USERS
from auth import _client_ip, _is_locked, _record_failure, _clear_attempts, _log_sec, sin_acceso_html
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

bp = Blueprint('rrhh', __name__)


@bp.route("/rrhh")
def rrhh_panel():
    if "compras_user" not in session:
        return redirect("/login?next=/rrhh")
    u = session.get("compras_user", "")
    if u not in RRHH_USERS:
        return Response(sin_acceso_html("Recursos Humanos"), mimetype="text/html")
    usuario = u.capitalize()
    return Response(RRHH_HTML.replace("{usuario}", usuario), mimetype="text/html")


@bp.route("/api/rrhh/dashboard")
def rrhh_dashboard():
    u = session.get("compras_user", "")
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM empleados WHERE estado='Activo'")
    headcount = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(salario_base),0) FROM empleados WHERE estado='Activo'")
    nomina_bruta = c.fetchone()[0]
    mes_actual = datetime.now().strftime("%Y-%m")
    c.execute("SELECT COALESCE(SUM(dias),0) FROM ausencias WHERE estado='Aprobada' AND fecha_inicio LIKE ?", (mes_actual+"%",))
    dias_ausentes = c.fetchone()[0]
    ausentismo_pct = round(dias_ausentes/(headcount*22)*100,1) if headcount>0 else 0
    c.execute("SELECT COUNT(*) FROM capacitaciones_empleados WHERE completado=0")
    caps_pendientes = c.fetchone()[0]
    c.execute("SELECT empresa, COUNT(*) FROM empleados WHERE estado='Activo' GROUP BY empresa ORDER BY 2 DESC")
    por_empresa = [{"empresa":r[0],"count":r[1]} for r in c.fetchall()]
    c.execute("SELECT area, COUNT(*) FROM empleados WHERE estado='Activo' GROUP BY area ORDER BY 2 DESC")
    por_area = [{"area":r[0],"count":r[1]} for r in c.fetchall()]
    alertas = []
    from datetime import date as ddate
    c.execute("SELECT id, nombre||' '||apellido, fecha_ingreso FROM empleados WHERE estado='Activo'")
    for emp in c.fetchall():
        if emp[2]:
            try:
                fi = ddate.fromisoformat(emp[2])
                if (ddate.today()-fi).days > 365:
                    c.execute("SELECT COALESCE(SUM(dias),0) FROM ausencias WHERE tipo='Vacaciones' AND estado='Aprobada' AND empleado_id=?", (emp[0],))
                    vac = c.fetchone()[0]
                    if vac < 15:
                        alertas.append({"tipo":"warn","msg":emp[1]+" tiene "+str(15-vac)+" dias de vacaciones pendientes"})
            except: pass
    c.execute("SELECT nombre||' '||apellido, fecha_fin_contrato FROM empleados WHERE tipo_contrato='Fijo' AND fecha_fin_contrato!='' AND estado='Activo'")
    for r in c.fetchall():
        if r[1]:
            try:
                fv = ddate.fromisoformat(r[1])
                d_days = (fv-ddate.today()).days
                if 0 < d_days <= 45:
                    alertas.append({"tipo":"danger","msg":"Contrato de "+r[0]+" vence en "+str(d_days)+" dias"})
            except: pass
    conn.close()
    return jsonify({"headcount":headcount,"nomina_bruta":nomina_bruta,"ausentismo_pct":ausentismo_pct,"caps_pendientes":caps_pendientes,"por_empresa":por_empresa,"por_area":por_area,"alertas":alertas})


@bp.route("/api/rrhh/empleados", methods=["GET","POST"])
def rrhh_empleados():
    u = session.get("compras_user", "")
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == "POST":
        d = request.get_json(silent=True) or {}
        c.execute("SELECT COUNT(*) FROM empleados"); n = c.fetchone()[0]+1
        codigo = "EMP"+str(n).zfill(4)
        c.execute("INSERT INTO empleados (codigo,nombre,apellido,cedula,cargo,area,empresa,tipo_contrato,fecha_ingreso,estado,salario_base,eps,afp,arl,caja_compensacion,email,telefono,nivel_riesgo,observaciones) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                 (codigo,d.get("nombre",""),d.get("apellido",""),d.get("cedula",""),d.get("cargo",""),d.get("area",""),d.get("empresa","Espagiria"),d.get("tipo_contrato","Indefinido"),d.get("fecha_ingreso",""),"Activo",float(d.get("salario_base",0)),d.get("eps",""),d.get("afp",""),d.get("arl",""),d.get("caja",""),d.get("email",""),d.get("telefono",""),int(d.get("nivel_riesgo",1)),d.get("observaciones","")))
        conn.commit(); new_id=c.lastrowid; conn.close()
        return jsonify({"ok":True,"id":new_id,"codigo":codigo}),201
    c.execute("SELECT id,codigo,nombre,apellido,cargo,area,empresa,tipo_contrato,fecha_ingreso,estado,salario_base,email,telefono,eps,afp,nivel_riesgo FROM empleados ORDER BY empresa,nombre")
    rows=c.fetchall(); conn.close()
    return jsonify([{"id":r[0],"codigo":r[1],"nombre":r[2],"apellido":r[3],"cargo":r[4],"area":r[5],"empresa":r[6],"tipo_contrato":r[7],"fecha_ingreso":r[8],"estado":r[9],"salario_base":r[10],"email":r[11],"telefono":r[12],"eps":r[13],"afp":r[14],"nivel_riesgo":r[15]} for r in rows])


@bp.route("/api/rrhh/empleados/<int:eid>", methods=["GET","PUT"])
def rrhh_empleado_det(eid):
    u = session.get("compras_user", "")
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    if request.method == "PUT":
        d = request.get_json(silent=True) or {}
        c.execute("UPDATE empleados SET nombre=?,apellido=?,cargo=?,area=?,empresa=?,tipo_contrato=?,salario_base=?,eps=?,afp=?,arl=?,caja_compensacion=?,email=?,telefono=?,nivel_riesgo=?,observaciones=?,estado=? WHERE id=?",
                 (d.get("nombre",""),d.get("apellido",""),d.get("cargo",""),d.get("area",""),d.get("empresa",""),d.get("tipo_contrato",""),float(d.get("salario_base",0)),d.get("eps",""),d.get("afp",""),d.get("arl",""),d.get("caja",""),d.get("email",""),d.get("telefono",""),int(d.get("nivel_riesgo",1)),d.get("observaciones",""),d.get("estado","Activo"),eid))
        conn.commit(); conn.close(); return jsonify({"ok":True})
    c.execute("SELECT * FROM empleados WHERE id=?", (eid,))
    r=c.fetchone()
    if not r: conn.close(); return jsonify({"error":"not found"}),404
    cols=[d[0] for d in c.description]; conn.close()
    return jsonify(dict(zip(cols,r)))


@bp.route("/api/rrhh/nomina/<periodo>")
def rrhh_nomina(periodo):
    u = session.get("compras_user", "")
    SMMLV=1423500; AUX=202000
    conn=sqlite3.connect(DB_PATH); c=conn.cursor()
    c.execute("SELECT id,nombre,apellido,cargo,salario_base,empresa,area,nivel_riesgo FROM empleados WHERE estado='Activo' ORDER BY empresa,nombre")
    emps=c.fetchall()
    c.execute("SELECT empleado_id,dias_trabajados,horas_extras,valor_horas_extras,bonificaciones,otros_descuentos FROM nomina_registros WHERE periodo=?", (periodo,))
    ex={r[0]:r for r in c.fetchall()}; conn.close()
    result=[]
    arl_rates={1:0.00522,2:0.01044,3:0.02436,4:0.04350,5:0.06960}
    for e in emps:
        eid,nom,ape,cargo,sal,emp,area,riesgo=e
        xr=ex.get(eid)
        dias=xr[1] if xr else 30; he=xr[2] if xr else 0; vhe=xr[3] if xr else 0
        bonos=xr[4] if xr else 0; otros=xr[5] if xr else 0
        aux=AUX if sal<=2*SMMLV else 0
        desc_salud=round(sal*0.04); desc_pension=round(sal*0.04)
        neto=sal+aux+vhe+bonos-desc_salud-desc_pension-otros
        ap_s=round(sal*0.085); ap_p=round(sal*0.12)
        ap_arl=round(sal*arl_rates.get(riesgo,0.00522))
        ap_sena=round(sal*0.02); ap_icbf=round(sal*0.03); ap_caja=round(sal*0.04)
        ap_tot=ap_s+ap_p+ap_arl+ap_sena+ap_icbf+ap_caja
        result.append({"id":eid,"nombre":nom+" "+ape,"cargo":cargo,"empresa":emp,"area":area,"salario_base":sal,"dias_trabajados":dias,"aux_transporte":aux,"horas_extras":he,"valor_horas_extras":vhe,"bonificaciones":bonos,"desc_salud":desc_salud,"desc_pension":desc_pension,"otros_descuentos":otros,"neto":neto,"aportes_empleador":{"salud":ap_s,"pension":ap_p,"arl":ap_arl,"sena":ap_sena,"icbf":ap_icbf,"caja":ap_caja,"total":ap_tot}})
    return jsonify(result)


@bp.route("/api/rrhh/nomina/guardar", methods=["POST"])
def rrhh_nomina_guardar():
    u = session.get("compras_user", "")
    d=request.get_json(silent=True) or {}
    periodo=d.get("periodo",""); registros=d.get("registros",[])
    conn=sqlite3.connect(DB_PATH); c=conn.cursor()
    for r in registros:
        c.execute("INSERT OR REPLACE INTO nomina_registros (periodo,empleado_id,salario_base,dias_trabajados,horas_extras,valor_horas_extras,subsidio_transporte,bonificaciones,descuento_salud,descuento_pension,otros_descuentos,salario_neto,estado) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                 (periodo,r["id"],r["salario_base"],r.get("dias_trabajados",30),r.get("horas_extras",0),r.get("valor_horas_extras",0),r.get("aux_transporte",0),r.get("bonificaciones",0),r["desc_salud"],r["desc_pension"],r.get("otros_descuentos",0),r["neto"],"Generada"))
    conn.commit(); conn.close()
    return jsonify({"ok":True,"periodo":periodo,"registros":len(registros)})


@bp.route("/api/rrhh/ausencias", methods=["GET","POST"])
def rrhh_ausencias():
    u = session.get("compras_user", "")
    conn=sqlite3.connect(DB_PATH); c=conn.cursor()
    if request.method=="POST":
        d=request.get_json(silent=True) or {}
        c.execute("INSERT INTO ausencias (empleado_id,tipo,fecha_inicio,fecha_fin,dias,estado,observaciones) VALUES (?,?,?,?,?,'Pendiente',?)",
                 (int(d.get("empleado_id",0)),d.get("tipo","Vacaciones"),d.get("fecha_inicio",""),d.get("fecha_fin",""),int(d.get("dias",0)),d.get("observaciones","")))
        conn.commit(); conn.close(); return jsonify({"ok":True}),201
    c.execute("SELECT a.id,e.nombre||' '||e.apellido,a.tipo,a.fecha_inicio,a.fecha_fin,a.dias,a.estado,a.observaciones,a.aprobado_por FROM ausencias a JOIN empleados e ON a.empleado_id=e.id ORDER BY a.creado_en DESC LIMIT 200")
    rows=c.fetchall(); conn.close()
    return jsonify([{"id":r[0],"empleado":r[1],"tipo":r[2],"fecha_inicio":r[3],"fecha_fin":r[4],"dias":r[5],"estado":r[6],"observaciones":r[7],"aprobado_por":r[8]} for r in rows])


@bp.route("/api/rrhh/ausencias/<int:aid>", methods=["PATCH"])
def rrhh_ausencia_upd(aid):
    u = session.get("compras_user", "")
    d=request.get_json(silent=True) or {}
    conn=sqlite3.connect(DB_PATH); c=conn.cursor()
    c.execute("UPDATE ausencias SET estado=?,aprobado_por=? WHERE id=?", (d.get("estado",""),session.get("compras_user",""),aid))
    conn.commit(); conn.close(); return jsonify({"ok":True})


@bp.route("/api/rrhh/capacitaciones", methods=["GET","POST"])
def rrhh_caps():
    u = session.get("compras_user", "")
    conn=sqlite3.connect(DB_PATH); c=conn.cursor()
    if request.method=="POST":
        d=request.get_json(silent=True) or {}
        c.execute("INSERT INTO capacitaciones (nombre,tipo,fecha,duracion_horas,instructor,empresa,obligatoria) VALUES (?,?,?,?,?,?,?)",
                 (d.get("nombre",""),d.get("tipo","BPM"),d.get("fecha",""),float(d.get("duracion_horas",1)),d.get("instructor",""),d.get("empresa","Espagiria"),1 if d.get("obligatoria") else 0))
        cap_id=c.lastrowid
        c.execute("SELECT id FROM empleados WHERE estado='Activo'")
        for emp in c.fetchall():
            try: c.execute("INSERT OR IGNORE INTO capacitaciones_empleados (capacitacion_id,empleado_id,completado) VALUES (?,?,0)", (cap_id,emp[0]))
            except: pass
        conn.commit(); conn.close(); return jsonify({"ok":True,"id":cap_id}),201
    c.execute("SELECT c.id,c.nombre,c.tipo,c.fecha,c.duracion_horas,c.instructor,c.obligatoria,COUNT(ce.id),COALESCE(SUM(ce.completado),0) FROM capacitaciones c LEFT JOIN capacitaciones_empleados ce ON c.id=ce.capacitacion_id GROUP BY c.id ORDER BY c.fecha DESC")
    rows=c.fetchall(); conn.close()
    return jsonify([{"id":r[0],"nombre":r[1],"tipo":r[2],"fecha":r[3],"horas":r[4],"instructor":r[5],"obligatoria":r[6],"total":r[7],"completados":r[8]} for r in rows])


@bp.route("/api/rrhh/evaluaciones", methods=["GET","POST"])
def rrhh_evals():
    u = session.get("compras_user", "")
    conn=sqlite3.connect(DB_PATH); c=conn.cursor()
    if request.method=="POST":
        d=request.get_json(silent=True) or {}
        scores=[float(d.get(k,0)) for k in ["calidad","asistencia","actitud","conocimiento","productividad"]]
        total=round(sum(scores)/5,1)
        c.execute("INSERT INTO evaluaciones (empleado_id,periodo,evaluador,puntaje_total,puntaje_calidad,puntaje_asistencia,puntaje_actitud,puntaje_conocimiento,puntaje_productividad,comentarios,estado) VALUES (?,?,?,?,?,?,?,?,?,?,'Publicada')",
                 (int(d.get("empleado_id",0)),d.get("periodo",""),session.get("compras_user",""),total,scores[0],scores[1],scores[2],scores[3],scores[4],d.get("comentarios","")))
        conn.commit(); conn.close(); return jsonify({"ok":True}),201
    periodo=request.args.get("periodo","")
    q="SELECT ev.id,e.nombre||' '||e.apellido,e.cargo,ev.periodo,ev.evaluador,ev.puntaje_total,ev.puntaje_calidad,ev.puntaje_asistencia,ev.puntaje_actitud,ev.puntaje_conocimiento,ev.puntaje_productividad,ev.comentarios FROM evaluaciones ev JOIN empleados e ON ev.empleado_id=e.id"
    if periodo: c.execute(q+" WHERE ev.periodo=? ORDER BY ev.puntaje_total DESC",(periodo,))
    else: c.execute(q+" ORDER BY ev.periodo DESC,ev.puntaje_total DESC LIMIT 50")
    rows=c.fetchall(); conn.close()
    return jsonify([{"id":r[0],"empleado":r[1],"cargo":r[2],"periodo":r[3],"evaluador":r[4],"total":r[5],"calidad":r[6],"asistencia":r[7],"actitud":r[8],"conocimiento":r[9],"productividad":r[10],"comentarios":r[11]} for r in rows])


@bp.route("/api/rrhh/sgsst", methods=["GET","POST"])
def rrhh_sgsst():
    u = session.get("compras_user", "")
    conn=sqlite3.connect(DB_PATH); c=conn.cursor()
    if request.method=="POST":
        d=request.get_json(silent=True) or {}
        c.execute("INSERT INTO sgsst_items (categoria,descripcion,frecuencia,responsable,proximo_vencimiento,estado) VALUES (?,?,?,?,?,'Pendiente')",
                 (d.get("categoria",""),d.get("descripcion",""),d.get("frecuencia","Anual"),d.get("responsable",""),d.get("proximo_vencimiento","")))
        conn.commit(); conn.close(); return jsonify({"ok":True}),201
    c.execute("SELECT id,categoria,descripcion,frecuencia,ultimo_cumplimiento,proximo_vencimiento,responsable,estado FROM sgsst_items ORDER BY categoria,descripcion")
    rows=c.fetchall(); conn.close()
    return jsonify([{"id":r[0],"categoria":r[1],"descripcion":r[2],"frecuencia":r[3],"ultimo":r[4],"proximo":r[5],"responsable":r[6],"estado":r[7]} for r in rows])


@bp.route("/api/rrhh/sgsst/<int:sid>", methods=["PATCH"])
def rrhh_sgsst_upd(sid):
    u = session.get("compras_user", "")
    d=request.get_json(silent=True) or {}
    from datetime import date as ddate, timedelta
    conn=sqlite3.connect(DB_PATH); c=conn.cursor()
    c.execute("SELECT frecuencia FROM sgsst_items WHERE id=?", (sid,))
    row=c.fetchone(); hoy=ddate.today().isoformat()
    freq_days={"Mensual":30,"Trimestral":90,"Semestral":180,"Anual":365}
    prox=d.get("proximo_vencimiento","") or (ddate.today()+timedelta(days=freq_days.get(row[0] if row else "Anual",365))).isoformat()
    c.execute("UPDATE sgsst_items SET estado='Cumplido',ultimo_cumplimiento=?,proximo_vencimiento=? WHERE id=?", (hoy,prox,sid))
    conn.commit(); conn.close(); return jsonify({"ok":True})

# ═══════════════════════════════════════════════════════
#  CALIDAD BPM — Página + API
# ═══════════════════════════════════════════════════════
