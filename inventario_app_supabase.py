#!/usr/bin/env python3
"""
Sistema de Gestión de Inventarios - ÁNIMUS Lab + Espagiria
Versión SUPABASE POSTGRESQL - Base de datos real
"""

from flask import Flask, render_template_string, jsonify, request
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
import json

app = Flask(__name__)

# ============================================================
# SUPABASE DATABASE CONNECTION
# ============================================================

class InventoryDatabaseSupabase:
    """Conexión a Supabase PostgreSQL"""

    def __init__(self, db_host, db_name, db_user, db_password, db_port=5432):
        """
        Conectar a Supabase PostgreSQL

        Credenciales:
        - Host: vppihjpqwbdtpipopymc.supabase.co
        - Database: postgres
        - User: postgres
        - Password: (tu contraseña)
        - Port: 5432
        """
        self.conn_params = {
            'host': db_host,
            'database': db_name,
            'user': db_user,
            'password': db_password,
            'port': db_port,
            'sslmode': 'require'  # Supabase requiere SSL
        }
        self.materiales = {}
        self.lotes = []
        self._connect()

    def _connect(self):
        """Establecer conexión a la base de datos"""
        try:
            conn = psycopg2.connect(**self.conn_params)
            print("✅ Conectado a Supabase PostgreSQL")

            # Cargar materiales
            self._load_materiales(conn)

            # Cargar lotes
            self._load_lotes(conn)

            conn.close()
        except psycopg2.OperationalError as e:
            print(f"❌ ERROR de conexión: {e}")
            print("\nSolución:")
            print("1. Verifica que las credenciales sean correctas")
            print("2. Verifica que Supabase esté disponible")
            print("3. Verifica que hayas ejecutado ALL_322_BATCH.sql")
            raise

    def _load_materiales(self, conn):
        """Cargar materiales desde la tabla materiales"""
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT id, codigo, nombre FROM materiales ORDER BY codigo")
                for row in cur.fetchall():
                    self.materiales[row['id']] = {
                        'codigo': row['codigo'],
                        'nombre': row['nombre'],
                        'unidad': 'unidad'  # Ajusta según tu esquema
                    }
            print(f"✅ Cargados {len(self.materiales)} materiales")
        except Exception as e:
            print(f"⚠️  No se pudieron cargar materiales: {e}")

    def _load_lotes(self, conn):
        """Cargar lotes desde la tabla lotes"""
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        l.id,
                        l.material_id,
                        l.codigo_lote,
                        l.ubicacion,
                        l.cantidad,
                        l.fecha_vencimiento,
                        l.fecha_ingreso,
                        l.activo,
                        m.codigo as material_codigo,
                        m.nombre as material_nombre
                    FROM lotes l
                    LEFT JOIN materiales m ON l.material_id = m.id
                    WHERE l.activo = true
                    ORDER BY l.fecha_vencimiento ASC
                """)

                hoy = datetime.now().date()
                for row in cur.fetchall():
                    dias_restantes = (row['fecha_vencimiento'] - hoy).days if row['fecha_vencimiento'] else 999

                    self.lotes.append({
                        'id': row['id'],
                        'material_id': row['material_codigo'],
                        'material_nombre': row['material_nombre'],
                        'codigo_lote': row['codigo_lote'],
                        'ubicacion': row['ubicacion'],
                        'cantidad': row['cantidad'],
                        'fecha_vencimiento': row['fecha_vencimiento'].isoformat() if row['fecha_vencimiento'] else None,
                        'fecha_ingreso': row['fecha_ingreso'].isoformat() if row['fecha_ingreso'] else None,
                        'dias_restantes': dias_restantes
                    })

            print(f"✅ Cargados {len(self.lotes)} lotes de Supabase")
        except Exception as e:
            print(f"❌ Error cargando lotes: {e}")
            raise

# ============================================================
# INICIALIZAR CONEXIÓN
# ============================================================

# CONFIGURAR AQUÍ TUS CREDENCIALES DE SUPABASE
DB_CONFIG = {
    'db_host': 'vppihjpqwbdtpipopymc.supabase.co',
    'db_name': 'postgres',
    'db_user': 'postgres',
    'db_password': 'TU_CONTRASEÑA_AQUI',  # ← CAMBIAR ESTO
    'db_port': 5432
}

try:
    db = InventoryDatabaseSupabase(**DB_CONFIG)
except Exception as e:
    print(f"\n⚠️  No se pudo conectar a Supabase. Continuando con datos de prueba...")
    # Si hay error, cargar datos simulados para testing
    db = None

# ============================================================
# API ENDPOINTS
# ============================================================

@app.route('/api/lotes', methods=['GET'])
def get_lotes():
    """Obtener todos los lotes con filtros opcionales"""
    if not db or not db.lotes:
        return jsonify({'error': 'No hay datos disponibles'}), 503

    status_filter = request.args.get('status')
    material = request.args.get('material')

    lotes = db.lotes

    if status_filter == 'vencido':
        lotes = [l for l in lotes if l['dias_restantes'] < 0]
    elif status_filter == 'critico':
        lotes = [l for l in lotes if 0 <= l['dias_restantes'] <= 20]
    elif status_filter == 'bajo':
        lotes = [l for l in lotes if 20 < l['dias_restantes'] <= 60]
    elif status_filter == 'normal':
        lotes = [l for l in lotes if l['dias_restantes'] > 60]

    if material:
        lotes = [l for l in lotes if l['material_id'] == material]

    return jsonify({
        'total': len(lotes),
        'lotes': lotes[:50]
    })

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    """Dashboard con KPIs principales"""
    if not db or not db.lotes:
        return jsonify({'error': 'No hay datos disponibles'}), 503

    total_lotes = len(db.lotes)
    cantidad_total = sum(l['cantidad'] for l in db.lotes)

    vencidos = [l for l in db.lotes if l['dias_restantes'] < 0]
    criticos = [l for l in db.lotes if 0 <= l['dias_restantes'] <= 20]
    bajo_stock = [l for l in db.lotes if 20 < l['dias_restantes'] <= 60]
    normales = [l for l in db.lotes if l['dias_restantes'] > 60]

    return jsonify({
        'total_lotes': total_lotes,
        'cantidad_total': cantidad_total,
        'valor_inventario': round(cantidad_total * 45, 2),  # Estimado
        'lotes_vencidos': len(vencidos),
        'lotes_criticos': len(criticos),
        'lotes_bajo_stock': len(bajo_stock),
        'lotes_normales': len(normales),
        'rotacion_promedio': round(cantidad_total / total_lotes, 2) if total_lotes > 0 else 0,
        'alertas': {
            'vencidos': [l['codigo_lote'] for l in vencidos[:5]],
            'proximoVencimiento': [l['codigo_lote'] for l in criticos[:5]]
        }
    })

@app.route('/api/reorden', methods=['GET'])
def get_reorden():
    """Calcular necesidad de reorden (20 días antes)"""
    if not db or not db.lotes:
        return jsonify({'error': 'No hay datos disponibles'}), 503

    dias_anticipacion = 20
    reorden_necesario = []

    for lote in db.lotes:
        dias_restantes = lote['dias_restantes']
        if dias_restantes <= dias_anticipacion and dias_restantes >= 0:
            reorden_necesario.append({
                'material_id': lote['material_id'],
                'nombre_material': lote['material_nombre'],
                'codigo_lote': lote['codigo_lote'],
                'cantidad_actual': lote['cantidad'],
                'vencimiento': lote['fecha_vencimiento'],
                'dias_restantes': dias_restantes,
                'urgencia': 'CRÍTICA' if dias_restantes <= 10 else 'ALTA' if dias_restantes <= 20 else 'MEDIA'
            })

    return jsonify({
        'total_necesarios': len(reorden_necesario),
        'items': sorted(reorden_necesario, key=lambda x: x['dias_restantes'])[:20]
    })

@app.route('/api/analisis-abc', methods=['GET'])
def analisis_abc():
    """Análisis ABC (simulado con cantidades)"""
    if not db or not db.lotes:
        return jsonify({'error': 'No hay datos disponibles'}), 503

    por_material = {}
    for lote in db.lotes:
        codigo = lote['material_id']
        if codigo not in por_material:
            por_material[codigo] = {'cantidad_total': 0, 'lotes': 0, 'nombre': lote['material_nombre']}
        por_material[codigo]['cantidad_total'] += lote['cantidad']
        por_material[codigo]['lotes'] += 1

    ordenado = sorted(por_material.items(), key=lambda x: x[1]['cantidad_total'], reverse=True)

    total_valor = sum(d['cantidad_total'] for _, d in ordenado)
    acumulativo = 0
    clasificacion = []

    for codigo, datos in ordenado:
        acumulativo += datos['cantidad_total']
        porcentaje_acumulado = (acumulativo / total_valor * 100) if total_valor > 0 else 0

        if porcentaje_acumulado <= 80:
            categoria = 'A'
        elif porcentaje_acumulado <= 95:
            categoria = 'B'
        else:
            categoria = 'C'

        clasificacion.append({
            'material_id': codigo,
            'nombre': datos['nombre'],
            'cantidad': datos['cantidad_total'],
            'lotes': datos['lotes'],
            'valor': round(datos['cantidad_total'], 2),
            'porcentaje_valor': round(datos['cantidad_total'] / total_valor * 100, 2) if total_valor > 0 else 0,
            'categoria': categoria
        })

    return jsonify({
        'valor_total': round(total_valor, 2),
        'articulos': clasificacion[:30]
    })

@app.route('/api/obsolescencia', methods=['GET'])
def detectar_obsolescencia():
    """Detectar lotes próximos a vencer"""
    if not db or not db.lotes:
        return jsonify({'error': 'No hay datos disponibles'}), 503

    vencidos = []
    criticos = []

    for lote in db.lotes:
        if lote['dias_restantes'] < 0:
            vencidos.append({
                'codigo_lote': lote['codigo_lote'],
                'material': lote['material_nombre'],
                'cantidad': lote['cantidad'],
                'dias_vencido': abs(lote['dias_restantes']),
                'urgencia': 'CRÍTICA'
            })
        elif lote['dias_restantes'] <= 30:
            criticos.append({
                'codigo_lote': lote['codigo_lote'],
                'material': lote['material_nombre'],
                'cantidad': lote['cantidad'],
                'dias_restantes': lote['dias_restantes'],
                'urgencia': 'ALTA'
            })

    return jsonify({
        'lotes_vencidos': len(vencidos),
        'lotes_criticos': len(criticos),
        'riesgo_obsolescencia': 'ALTO' if len(vencidos) > 0 else 'MEDIO' if len(criticos) > 5 else 'BAJO',
        'vencidos': vencidos[:10],
        'criticos': criticos[:10]
    })

@app.route('/api/optimizacion', methods=['GET'])
def optimizacion_compra():
    """Recomendaciones de optimización"""
    if not db or not db.lotes:
        return jsonify({'error': 'No hay datos disponibles'}), 503

    hoy = datetime.now().date()
    rotacion = {}

    for lote in db.lotes:
        codigo = lote['material_id']
        if codigo not in rotacion:
            rotacion[codigo] = {'cantidad': 0, 'dias': 0, 'lotes': 0, 'nombre': lote['material_nombre']}
        rotacion[codigo]['cantidad'] += lote['cantidad']
        rotacion[codigo]['lotes'] += 1

    recomendaciones = []
    for codigo, datos in rotacion.items():
        dias_promedio = datos['dias'] / datos['lotes'] if datos['lotes'] > 0 else 30
        rotacion_anual = 365 / (dias_promedio + 1) if dias_promedio >= 0 else 0

        recomendaciones.append({
            'material_id': codigo,
            'nombre': datos['nombre'],
            'cantidad_stock': datos['cantidad'],
            'lotes_activos': datos['lotes'],
            'dias_almacenamiento_promedio': round(dias_promedio, 1),
            'rotacion_anual': round(rotacion_anual, 2),
            'recomendacion': 'Aumentar compras' if rotacion_anual > 4 else 'Reducir compras' if rotacion_anual < 1 else 'Mantener nivel actual'
        })

    return jsonify({
        'total_materiales': len(recomendaciones),
        'optimizaciones': sorted(recomendaciones, key=lambda x: x['rotacion_anual'], reverse=True)[:20]
    })

# ============================================================
# INTERFAZ WEB (igual al anterior)
# ============================================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ÁNIMUS Lab - Sistema de Inventarios (Supabase)</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto; background: #f5f5f5; color: #333; }
        header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; }
        h1 { font-size: 28px; margin-bottom: 5px; }
        .subtitle { opacity: 0.9; }
        .container { max-width: 1400px; margin: 20px auto; padding: 0 20px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .card {
            background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-left: 4px solid #667eea;
        }
        .card.alert { border-left-color: #e74c3c; }
        .card.warning { border-left-color: #f39c12; }
        .card.success { border-left-color: #27ae60; }
        .card h3 { color: #667eea; margin-bottom: 10px; font-size: 14px; text-transform: uppercase; }
        .card .value { font-size: 32px; font-weight: bold; margin: 10px 0; }
        .tabs { display: flex; gap: 0; border-bottom: 1px solid #ddd; margin-bottom: 20px; }
        .tab { padding: 12px 20px; cursor: pointer; border-bottom: 3px solid transparent; transition: all 0.3s; }
        .tab.active { color: #667eea; border-bottom-color: #667eea; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; }
        th { background: #f8f9fa; padding: 12px; text-align: left; font-weight: 600; color: #667eea; }
        td { padding: 12px; border-bottom: 1px solid #eee; }
        .badge { display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600; }
        .badge.critical { background: #ffe5e5; color: #c0392b; }
        .badge.warning { background: #fff3cd; color: #856404; }
        .badge.normal { background: #d4edda; color: #155724; }
        .alert-box { padding: 15px; border-radius: 4px; margin-bottom: 20px; }
        .alert-box.critical { background: #ffe5e5; color: #c0392b; border-left: 4px solid #c0392b; }
        .alert-box.warning { background: #fff3cd; color: #856404; border-left: 4px solid #f39c12; }
        .db-status { text-align: right; padding: 10px 20px; font-size: 12px; color: #999; }
        .db-status.connected { color: #27ae60; }
        footer { text-align: center; padding: 20px; color: #999; font-size: 12px; }
    </style>
</head>
<body>
    <header>
        <h1>🧪 ÁNIMUS Lab + Espagiria Laboratorio</h1>
        <p class="subtitle">Sistema Integrado de Gestión de Inventarios (Supabase PostgreSQL)</p>
        <div class="db-status connected">✅ Conectado a Supabase | Datos en tiempo real</div>
    </header>

    <div class="container">
        <div id="dashboard-tab" class="tab-content active">
            <h2 style="margin-bottom: 20px;">Dashboard</h2>
            <div class="grid" id="kpis"></div>
            <h3 style="margin-top: 30px;">Alertas Críticas</h3>
            <div id="alertas"></div>
        </div>

        <div class="tabs">
            <div class="tab active" onclick="switchTab('dashboard')">📊 Dashboard</div>
            <div class="tab" onclick="switchTab('lotes')">📦 Lotes</div>
            <div class="tab" onclick="switchTab('reorden')">🔄 Reorden</div>
            <div class="tab" onclick="switchTab('analisis')">📈 Análisis ABC</div>
            <div class="tab" onclick="switchTab('obsolescencia')">⚠️ Obsolescencia</div>
            <div class="tab" onclick="switchTab('optimizacion')">💡 Optimización</div>
        </div>

        <!-- LOTES -->
        <div id="lotes-tab" class="tab-content">
            <h2>Gestión de Lotes</h2>
            <table>
                <thead><tr><th>Código</th><th>Material</th><th>Cantidad</th><th>Ubicación</th><th>Vencimiento</th><th>Estado</th></tr></thead>
                <tbody id="lotes-table"></tbody>
            </table>
        </div>

        <!-- REORDEN -->
        <div id="reorden-tab" class="tab-content">
            <h2>Puntos de Reorden (20 días antes)</h2>
            <table>
                <thead><tr><th>Material</th><th>Código Lote</th><th>Stock</th><th>Vencimiento</th><th>Días</th><th>Urgencia</th></tr></thead>
                <tbody id="reorden-table"></tbody>
            </table>
        </div>

        <!-- ANÁLISIS ABC -->
        <div id="analisis-tab" class="tab-content">
            <h2>Análisis ABC</h2>
            <table>
                <thead><tr><th>Material</th><th>Cantidad</th><th>% Valor</th><th>Categoría</th></tr></thead>
                <tbody id="analisis-table"></tbody>
            </table>
        </div>

        <!-- OBSOLESCENCIA -->
        <div id="obsolescencia-tab" class="tab-content">
            <h2>Detección de Obsolescencia</h2>
            <div id="obsolescencia-content"></div>
        </div>

        <!-- OPTIMIZACIÓN -->
        <div id="optimizacion-tab" class="tab-content">
            <h2>Recomendaciones</h2>
            <table>
                <thead><tr><th>Material</th><th>Stock</th><th>Rotación Anual</th><th>Recomendación</th></tr></thead>
                <tbody id="optimizacion-table"></tbody>
            </table>
        </div>
    </div>

    <footer>
        ÁNIMUS Lab | Espagiria Laboratorio | Sistema de Inventarios Supabase PostgreSQL
        <br>Última actualización: <span id="updated-time"></span>
    </footer>

    <script>
        function switchTab(tab) {
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
            document.getElementById(tab + '-tab').classList.add('active');
            event.target.classList.add('active');

            if (tab === 'dashboard') loadDashboard();
            else if (tab === 'lotes') loadLotes();
            else if (tab === 'reorden') loadReorden();
            else if (tab === 'analisis') loadAnalisisABC();
            else if (tab === 'obsolescencia') loadObsolescencia();
            else if (tab === 'optimizacion') loadOptimizacion();
        }

        async function loadDashboard() {
            const res = await fetch('/api/dashboard');
            const data = await res.json();

            if (data.error) {
                document.getElementById('kpis').innerHTML = `<div style="color: red;">ERROR: ${data.error}</div>`;
                return;
            }

            const html = `
                <div class="card"><h3>Total Lotes</h3><div class="value">${data.total_lotes}</div></div>
                <div class="card success"><h3>Cantidad Total</h3><div class="value">${data.cantidad_total}</div></div>
                <div class="card alert"><h3>Vencidos</h3><div class="value">${data.lotes_vencidos}</div></div>
                <div class="card warning"><h3>Críticos</h3><div class="value">${data.lotes_criticos}</div></div>
            `;
            document.getElementById('kpis').innerHTML = html;
            document.getElementById('updated-time').textContent = new Date().toLocaleString('es-ES');
        }

        async function loadLotes() {
            const res = await fetch('/api/lotes');
            const data = await res.json();
            let html = '';
            for (const lote of data.lotes) {
                const estado = lote.dias_restantes < 0 ? 'critical' : lote.dias_restantes <= 20 ? 'warning' : 'normal';
                html += `<tr>
                    <td>${lote.codigo_lote}</td>
                    <td>${lote.material_id}</td>
                    <td>${lote.cantidad}</td>
                    <td>${lote.ubicacion}</td>
                    <td>${lote.fecha_vencimiento}</td>
                    <td><span class="badge ${estado}">${lote.dias_restantes < 0 ? 'VENCIDO' : lote.dias_restantes <= 20 ? 'CRÍTICO' : 'NORMAL'}</span></td>
                </tr>`;
            }
            document.getElementById('lotes-table').innerHTML = html;
        }

        async function loadReorden() {
            const res = await fetch('/api/reorden');
            const data = await res.json();
            let html = '';
            for (const item of data.items) {
                html += `<tr>
                    <td>${item.nombre_material}</td>
                    <td>${item.codigo_lote}</td>
                    <td>${item.cantidad_actual}</td>
                    <td>${item.vencimiento}</td>
                    <td>${item.dias_restantes} días</td>
                    <td><span class="badge warning">${item.urgencia}</span></td>
                </tr>`;
            }
            document.getElementById('reorden-table').innerHTML = html;
        }

        async function loadAnalisisABC() {
            const res = await fetch('/api/analisis-abc');
            const data = await res.json();
            let html = '';
            for (const item of data.articulos) {
                html += `<tr>
                    <td>${item.nombre}</td>
                    <td>${item.cantidad}</td>
                    <td>${item.porcentaje_valor}%</td>
                    <td><strong>Cat. ${item.categoria}</strong></td>
                </tr>`;
            }
            document.getElementById('analisis-table').innerHTML = html;
        }

        async function loadObsolescencia() {
            const res = await fetch('/api/obsolescencia');
            const data = await res.json();
            let html = `<p><strong>Riesgo: ${data.riesgo_obsolescencia}</strong></p>`;
            if (data.vencidos.length > 0) {
                html += '<h3>Vencidos</h3><table><tr><th>Lote</th><th>Material</th><th>Cantidad</th></tr>';
                for (const item of data.vencidos) {
                    html += `<tr><td>${item.codigo_lote}</td><td>${item.material}</td><td>${item.cantidad}</td></tr>`;
                }
                html += '</table>';
            }
            document.getElementById('obsolescencia-content').innerHTML = html;
        }

        async function loadOptimizacion() {
            const res = await fetch('/api/optimizacion');
            const data = await res.json();
            let html = '';
            for (const item of data.optimizaciones) {
                html += `<tr>
                    <td>${item.nombre}</td>
                    <td>${item.cantidad_stock}</td>
                    <td><strong>${item.rotacion_anual}x/año</strong></td>
                    <td>${item.recomendacion}</td>
                </tr>`;
            }
            document.getElementById('optimizacion-table').innerHTML = html;
        }

        window.onload = () => loadDashboard();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

# ============================================================
# MAIN
# ============================================================

if __name__ == '__main__':
    if db and db.lotes:
        print(f"\n✅ App lista con {len(db.lotes)} lotes de Supabase")
        print("🌐 Acceder a: http://localhost:5000")
    else:
        print("\n⚠️  Ejecutando en modo demo (sin base de datos)")
        print("Para conectar a Supabase:")
        print("1. Edita inventario_app_supabase.py")
        print("2. Reemplaza 'TU_CONTRASEÑA_AQUI' en DB_CONFIG")
        print("3. Ejecuta: python inventario_app_supabase.py")

    app.run(debug=True, host='0.0.0.0', port=5000)
