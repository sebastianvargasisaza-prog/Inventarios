# === backend: endpoint corregir-cantidad ===
pp = 'api/blueprints/programacion.py'
a = open(pp, encoding='utf-8').read()
ep = '''@bp.route('/api/programacion/programar/<int:pid>/corregir-cantidad', methods=['POST'])
def corregir_cantidad_produccion(pid):
    """Admin · corrige la cantidad_kg de una producción que YA descontó (cantidad equivocada): revierte el
    descuento viejo + actualiza kg + re-descuenta al nuevo valor. NO borra la producción. Sebastián 30-jun."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    if user not in ADMIN_USERS:
        return jsonify({'error': 'Solo admin puede corregir cantidades'}), 403
    d = request.get_json(silent=True) or {}
    try:
        new_kg = float(d.get('cantidad_kg') or 0)
    except (TypeError, ValueError):
        new_kg = 0
    if new_kg <= 0:
        return jsonify({'error': 'cantidad invalida (kg > 0)'}), 400
    conn = get_db()
    c = conn.cursor()
    row = c.execute("SELECT COALESCE(cantidad_kg,0), COALESCE(inventario_descontado_at,'') "
                    "FROM produccion_programada WHERE id=?", (pid,)).fetchone()
    if not row:
        return jsonify({'error': 'produccion no existe'}), 404
    _old_kg = row[0]
    # 1) revertir el descuento viejo (si descontó) · re-acredita la MP al kardex (canónico)
    if row[1]:
        try:
            _rr = prog_revertir_completado(pid)
            _code = _rr[1] if isinstance(_rr, tuple) else 200
            if _code not in (200, 400, 409):
                return jsonify({'error': 'no se pudo revertir el descuento viejo', 'codigo': 'REVERT_FALLO'}), 500
        except Exception as e:
            return jsonify({'error': 'fallo la reversion: ' + str(e)[:120]}), 500
    # 2) actualizar la cantidad (queda Fijo)
    c.execute("UPDATE produccion_programada SET cantidad_kg=?, origen='eos_plan' WHERE id=?", (new_kg, pid))
    # 3) re-descontar al nuevo valor
    try:
        _descontar_mp_produccion(c, pid, user, forzar=True)
    except Exception as e:
        conn.rollback()
        _m = str(getattr(e, 'mensaje', None) or e)[:150]
        return jsonify({'error': 'No se pudo descontar al nuevo valor: ' + _m,
                        'codigo': getattr(e, 'codigo', '')}), 409
    try:
        from audit_helpers import audit_log as _al
        _al(c, usuario=user, accion='CORREGIR_CANTIDAD_PRODUCCION', tabla='produccion_programada', registro_id=pid,
            antes={'cantidad_kg': _old_kg}, despues={'cantidad_kg': new_kg})
    except Exception:
        pass
    conn.commit()
    return jsonify({'ok': True, 'cantidad_kg': new_kg})


@bp.route('/api/planta/fabricacion/crear-iniciar', methods=['POST'])'''
anchor = "@bp.route('/api/planta/fabricacion/crear-iniciar', methods=['POST'])"
assert a.count(anchor) == 1, a.count(anchor)
open(pp, 'w', encoding='utf-8').write(a.replace(anchor, ep, 1))
print('endpoint corregir-cantidad · OK')

# === frontend: botón ✏️ corregir + función ===
p = 'api/templates_py/dashboard_html.py'
b = open(p, encoding='utf-8').read()
def rep(o, n, l):
    assert b.count(o) == 1, (l, b.count(o)); return b.replace(o, n, 1)
# botón: eliminar → corregir cantidad
b = rep('<button onclick=\"eliminarFabVivo('+chr(39)+'+o.produccion_id+'+chr(39)+')\" title=\"Eliminar y revertir el descuento de MP - para corregir una cantidad equivocada\" style=\"background:#fee2e2;color:#dc2626;border:1px solid #fca5a5;border-radius:5px;padding:4px 8px;font-size:10px;font-weight:700;cursor:pointer;margin-right:5px\">&#128465;</button>',
        '<button onclick=\"corregirCantidadFab('+chr(39)+'+o.produccion_id+'+chr(39)+')\" title=\"Corregir la cantidad (revierte y re-descuenta la MP) - para arreglar una cantidad equivocada\" style=\"background:#ede9fe;color:#6d28d9;border:1px solid #c4b5fd;border-radius:5px;padding:4px 8px;font-size:10px;font-weight:700;cursor:pointer;margin-right:5px\">&#9999;&#65039;</button>',
        'btn')
# función: eliminarFabVivo → corregirCantidadFab
b = rep("      window.eliminarFabVivo=async function(pid){\n"
        "        if(!confirm('\\u00bfEliminar esta producci\\u00f3n y REVERTIR el descuento de MP?\\nUsala para las que quedaron con cantidad equivocada - despu\\u00e9s la registr\\u00e1s de nuevo bien.'))return;\n"
        "        var t=await _csrfFab();\n"
        "        var r=await fetch('/api/plan/proximas/'+pid,{method:'DELETE',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':t},body:JSON.stringify({force:true})});\n"
        "        var j=await r.json();\n"
        "        if(!r.ok){ alert('Error: '+(j.error||r.status)); return; }\n"
        "        alert('\\u2713 Eliminada - MP revertida al inventario. Ahora registrala de nuevo con la cantidad correcta.');\n"
        "        if(window.cargarEnCurso) window.cargarEnCurso();\n"
        "      };\n",
        "      window.corregirCantidadFab=async function(pid){\n"
        "        var v=prompt('Nueva cantidad en KG (ej: 80 = 80.000 g):\\nRevierte el descuento viejo y descuenta la nueva cantidad de MP.');\n"
        "        if(v===null)return; var kg=parseFloat(v);\n"
        "        if(!(kg>0)){ alert('Cantidad inv\\u00e1lida'); return; }\n"
        "        var t=await _csrfFab();\n"
        "        var r=await fetch('/api/programacion/programar/'+pid+'/corregir-cantidad',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':t},body:JSON.stringify({cantidad_kg:kg})});\n"
        "        var j=await r.json();\n"
        "        if(!r.ok){ alert('Error: '+(j.error||r.status)); return; }\n"
        "        alert('\\u2713 Cantidad corregida a '+kg+' kg - MP ajustada.');\n"
        "        if(window.cargarEnCurso) window.cargarEnCurso();\n"
        "      };\n",
        'fn')
open(p, 'w', encoding='utf-8').write(b)
print('botón ✏️ + corregirCantidadFab · OK')
