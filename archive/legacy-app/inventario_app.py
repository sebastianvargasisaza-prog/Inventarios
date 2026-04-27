#!/usr/bin/env python3
"""
Sistema de Gestión de Inventarios - ÁNIMUS Lab + Espagiria
Monitoreo de stock, reorden, trazabilidad, optimización
"""

from flask import Flask, render_template_string, jsonify, request
from datetime import datetime, timedelta
import json
import re

app = Flask(__name__)

# ============================================================
# DATABASE MOCK - SIMULATED INVENTORY DATA
# (En producción, conectaría a Supabase PostgreSQL)
# ============================================================

class InventoryDatabase:
    """Mock database simulating Supabase with 322 lotes"""

    def __init__(self):
        self.materiales = self._load_materiales()
        self.lotes = self._load_lotes()
        self.reorder_points = self._calculate_reorder_points()

    def _load_materiales(self):
        """Cargar materiales desde la configuración"""
        return {
            'MPMP00001': {'nombre': 'Aceite Jojoba Puro', 'unidad': 'ml', 'precio': 45.00},
            'MPMP00002': {'nombre': 'Vitamina C Estabilizada', 'unidad': 'g', 'precio': 120.00},
            'MPMP00003': {'nombre': 'Ácido Hialurónico', 'unidad': 'g', 'precio': 85.00},
            'MPMP00004': {'nombre': 'Niacinamida', 'unidad': 'g', 'precio': 60.00},
            'MPMP00005': {'nombre': 'Retinol Puro', 'unidad': 'g', 'precio': 150.00},
            'MPMP00006': {'nombre': 'Ceramidas', 'unidad': 'g', 'precio': 95.00},
            'MPMP00210': {'nombre': 'Agua Desionizada', 'unidad': 'L', 'precio': 8.00},
            'MPMP00241': {'nombre': 'Glicerina Vegetal', 'unidad': 'L', 'precio': 25.00},
            'MPMP00306': {'nombre': 'Palmitoil Pentapéptido', 'unidad': 'g', 'precio': 200.00},
        }

    def _load_lotes(self):
        """Generar 322 lotes simulados"""
        lotes = []
        # Simulating the 322 lotes data structure
        data = [
            ('MPMP00210', 'A-001', 'EF1', 5000, '2027-12-31'),
            ('MPMP00241', 'A-002', 'EF1', 500, '2026-11-30'),
            ('MPMP00135', 'A-003', 'EF1', 5, '2028-06-30'),
            ('MPMP00229', 'A-004', 'EF2', 100, '2026-08-31'),
            ('MPMP00012', 'A-005', 'EF2', 1000, '2027-03-15'),
            ('MPMP00155', 'A-006', 'EF2', 250, '2026-10-15'),
            ('MPMP00031', 'A-007', 'EF3', 50, '2027-07-20'),
            ('MPMP00060', 'A-008', 'EF3', 2000, '2028-01-10'),
            ('MPMP00056', 'A-009', 'EF3', 500, '2026-09-05'),
            ('MPMP00047', 'A-010', 'EF4', 10, '2027-02-28'),
            ('MPMP00306', 'PALMI-01', 'ES-A', 100, '2027-06-30'),
            ('MPMP00001', 'LTE-001', 'EF1', 200, '2026-12-31'),
            ('MPMP00002', 'LTE-002', 'EF2', 150, '2027-01-31'),
            ('MPMP00003', 'LTE-003', 'EF3', 300, '2026-10-31'),
        ]

        for idx, (codigo_mp, lote, ubicacion, cantidad, vencimiento) in enumerate(data * 24):  # ~336 lotes
            if idx >= 322:
                break
            lotes.append({
                'id': idx + 1,
                'material_id': codigo_mp,
                'codigo_lote': f'{lote}-{idx:04d}' if idx > 13 else lote,
                'ubicacion': ubicacion,
                'cantidad': cantidad + (idx % 100),
                'fecha_vencimiento': vencimiento,
                'fecha_ingreso': (datetime.now() - timedelta(days=30 - (idx % 30))).strftime('%Y-%m-%d'),
                'activo': True,
                'dias_restantes': int((datetime.strptime(vencimiento, '%Y-%m-%d') - datetime.now()).days)
            })

        return lotes

    def _calculate_reorder_points(self):
        """Calcular puntos de reorden (20 días antes de agotarse)"""
        reorder = {}
        for lote in self.lotes:
            codigo = lote['material_id']
            if codigo not in reorder:
                reorder[codigo] = []
            reorder[codigo].append(lote)
        return reorder

db = InventoryDatabase()

# ============================================================
# API ENDPOINTS
# ============================================================

@app.route('/api/lotes', methods=['GET'])
def get_lotes():
    """Obtener todos los lotes con filtros opcionales"""
    status_filter = request.args.get('status')  # 'critico', 'bajo', 'normal', 'vencido'
    material = request.args.get('material')

    lotes = db.lotes
    hoy = datetime.now().date()

    # Aplicar filtros de estado
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
        'lotes': lotes[:50]  # Paginated
    })

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    """Dashboard con KPIs principales"""
    hoy = datetime.now().date()

    total_lotes = len(db.lotes)
    cantidad_total = sum(l['cantidad'] for l in db.lotes)

    # Clasificación ABC
    vencidos = [l for l in db.lotes if l['dias_restantes'] < 0]
    criticos = [l for l in db.lotes if 0 <= l['dias_restantes'] <= 20]
    bajo_stock = [l for l in db.lotes if 20 < l['dias_restantes'] <= 60]
    normales = [l for l in db.lotes if l['dias_restantes'] > 60]

    # Valor de inventario
    valor_total = 0
    for lote in db.lotes:
        mat = db.materiales.get(lote['material_id'], {})
        valor_total += lote['cantidad'] * mat.get('precio', 0)

    return jsonify({
        'total_lotes': total_lotes,
        'cantidad_total': cantidad_total,
        'valor_inventario': round(valor_total, 2),
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
    """Calcular necesidad de reorden (20 días antes de agotarse)"""
    hoy = datetime.now().date()
    dias_anticipacion = 20

    reorden_necesario = []
    for lote in db.lotes:
        dias_restantes = lote['dias_restantes']
        if dias_restantes <= dias_anticipacion and dias_restantes >= 0:
            mat = db.materiales.get(lote['material_id'], {})
            reorden_necesario.append({
                'material_id': lote['material_id'],
                'codigo_lote': lote['codigo_lote'],
                'cantidad_actual': lote['cantidad'],
                'vencimiento': lote['fecha_vencimiento'],
                'dias_restantes': dias_restantes,
                'nombre_material': mat.get('nombre', 'Desconocido'),
                'urgencia': 'CRÍTICA' if dias_restantes <= 10 else 'ALTA' if dias_restantes <= 20 else 'MEDIA',
                'precio_unitario': mat.get('precio', 0)
            })

    return jsonify({
        'total_necesarios': len(reorden_necesario),
        'items': sorted(reorden_necesario, key=lambda x: x['dias_restantes'])[:20]
    })

@app.route('/api/analisis-abc', methods=['GET'])
def analisis_abc():
    """Análisis ABC: valor vs frecuencia de movimiento"""
    # Agrupar por material
    por_material = {}
    for lote in db.lotes:
        codigo = lote['material_id']
        if codigo not in por_material:
            por_material[codigo] = {'cantidad_total': 0, 'lotes': 0}
        por_material[codigo]['cantidad_total'] += lote['cantidad']
        por_material[codigo]['lotes'] += 1

    # Calcular valor total
    for codigo, datos in por_material.items():
        mat = db.materiales.get(codigo, {})
        datos['valor'] = datos['cantidad_total'] * mat.get('precio', 0)
        datos['nombre'] = mat.get('nombre', codigo)

    # Ordenar por valor
    ordenado = sorted(por_material.items(), key=lambda x: x[1]['valor'], reverse=True)

    total_valor = sum(d['valor'] for _, d in ordenado)
    acumulativo = 0
    clasificacion = []

    for codigo, datos in ordenado:
        acumulativo += datos['valor']
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
            'valor': round(datos['valor'], 2),
            'porcentaje_valor': round(datos['valor'] / total_valor * 100, 2) if total_valor > 0 else 0,
            'categoria': categoria
        })

    return jsonify({
        'valor_total': round(total_valor, 2),
        'articulos': clasificacion[:30]
    })

@app.route('/api/obsolescencia', methods=['GET'])
def detectar_obsolescencia():
    """Detectar lotes próximos a vencer"""
    vencidos = []
    criticos = []
    bajo_movimiento = []

    for lote in db.lotes:
        if lote['dias_restantes'] < 0:
            vencidos.append({
                'codigo_lote': lote['codigo_lote'],
                'material': db.materiales.get(lote['material_id'], {}).get('nombre', '?'),
                'cantidad': lote['cantidad'],
                'dias_vencido': abs(lote['dias_restantes']),
                'urgencia': 'CRÍTICA'
            })
        elif lote['dias_restantes'] <= 30:
            criticos.append({
                'codigo_lote': lote['codigo_lote'],
                'material': db.materiales.get(lote['material_id'], {}).get('nombre', '?'),
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
    """Recomendaciones de optimización de compra"""
    hoy = datetime.now().date()

    # Calcular rotación por material
    rotacion = {}
    for lote in db.lotes:
        codigo = lote['material_id']
        dias_almacenado = (hoy - datetime.strptime(lote['fecha_ingreso'], '%Y-%m-%d').date()).days
        if codigo not in rotacion:
            rotacion[codigo] = {'cantidad': 0, 'dias': 0, 'lotes': 0}
        rotacion[codigo]['cantidad'] += lote['cantidad']
        rotacion[codigo]['dias'] += dias_almacenado
        rotacion[codigo]['lotes'] += 1

    recomendaciones = []
    for codigo, datos in rotacion.items():
        dias_promedio = datos['dias'] / datos['lotes'] if datos['lotes'] > 0 else 0
        rotacion_anual = 365 / (dias_promedio + 1) if dias_promedio >= 0 else 0

        mat = db.materiales.get(codigo, {})

        recomendaciones.append({
            'material_id': codigo,
            'nombre': mat.get('nombre', codigo),
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
# INTERFAZ WEB
# ============================================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ÁNIMUS Lab - Sistema de Inventarios</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
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
        .card .subtext { color: #999; font-size: 12px; }

        .tabs { display: flex; gap: 0; border-bottom: 1px solid #ddd; margin-bottom: 20px; }
        .tab { padding: 12px 20px; cursor: pointer; border-bottom: 3px solid transparent; transition: all 0.3s; }
        .tab.active { color: #667eea; border-bottom-color: #667eea; }

        .tab-content { display: none; }
        .tab-content.active { display: block; }

        table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; }
        th { background: #f8f9fa; padding: 12px; text-align: left; font-weight: 600; color: #667eea; }
        td { padding: 12px; border-bottom: 1px solid #eee; }
        tr:hover { background: #f8f9fa; }

        .badge { display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600; }
        .badge.critical { background: #ffe5e5; color: #c0392b; }
        .badge.warning { background: #fff3cd; color: #856404; }
        .badge.normal { background: #d4edda; color: #155724; }

        button { background: #667eea; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; }
        button:hover { background: #5568d3; }

        .alert-box { padding: 15px; border-radius: 4px; margin-bottom: 20px; }
        .alert-box.critical { background: #ffe5e5; color: #c0392b; border-left: 4px solid #c0392b; }
        .alert-box.warning { background: #fff3cd; color: #856404; border-left: 4px solid #f39c12; }

        footer { text-align: center; padding: 20px; color: #999; font-size: 12px; }
    </style>
</head>
<body>
    <header>
        <h1>🧪 ÁNIMUS Lab + Espagiria Laboratorio</h1>
        <p class="subtitle">Sistema Integrado de Gestión de Inventarios</p>
    </header>

    <div class="container">
        <!-- DASHBOARD -->
        <div id="dashboard-tab" class="tab-content active">
            <h2 style="margin-bottom: 20px;">Dashboard</h2>
            <div class="grid" id="kpis"></div>

            <h3 style="margin-top: 30px;">Alertas Críticas</h3>
            <div id="alertas"></div>
        </div>

        <!-- NAVEGACIÓN -->
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
            <div style="margin-bottom: 15px;">
                <button onclick="loadLotes()">Todos</button>
                <button onclick="loadLotes('vencido')">Vencidos</button>
                <button onclick="loadLotes('critico')">Críticos</button>
                <button onclick="loadLotes('bajo')">Bajo Stock</button>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Código Lote</th>
                        <th>Material</th>
                        <th>Cantidad</th>
                        <th>Ubicación</th>
                        <th>Vencimiento</th>
                        <th>Estado</th>
                    </tr>
                </thead>
                <tbody id="lotes-table"></tbody>
            </table>
        </div>

        <!-- REORDEN -->
        <div id="reorden-tab" class="tab-content">
            <h2>Puntos de Reorden (20 días antes)</h2>
            <table>
                <thead>
                    <tr>
                        <th>Material</th>
                        <th>Código Lote</th>
                        <th>Stock Actual</th>
                        <th>Vencimiento</th>
                        <th>Días Restantes</th>
                        <th>Urgencia</th>
                    </tr>
                </thead>
                <tbody id="reorden-table"></tbody>
            </table>
        </div>

        <!-- ANÁLISIS ABC -->
        <div id="analisis-tab" class="tab-content">
            <h2>Análisis ABC (Pareto)</h2>
            <p style="margin-bottom: 20px;">Clasificación según valor de inventario</p>
            <table>
                <thead>
                    <tr>
                        <th>Material</th>
                        <th>Cantidad</th>
                        <th>Valor Total</th>
                        <th>% del Valor</th>
                        <th>Categoría</th>
                    </tr>
                </thead>
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
            <h2>Recomendaciones de Optimización</h2>
            <table>
                <thead>
                    <tr>
                        <th>Material</th>
                        <th>Stock Actual</th>
                        <th>Rotación Anual</th>
                        <th>Días Almacenamiento</th>
                        <th>Recomendación</th>
                    </tr>
                </thead>
                <tbody id="optimizacion-table"></tbody>
            </table>
        </div>
    </div>

    <footer>
        ÁNIMUS Lab | Espagiria Laboratorio | Sistema de Inventarios Inteligente
        <br>Datos: 322 lotes, 300+ materiales | Última actualización: <span id="updated-time"></span>
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

            const html = `
                <div class="card">
                    <h3>Total de Lotes</h3>
                    <div class="value">${data.total_lotes}</div>
                    <div class="subtext">Cantidad: ${data.cantidad_total} unidades</div>
                </div>
                <div class="card success">
                    <h3>Valor de Inventario</h3>
                    <div class="value">$${data.valor_inventario.toLocaleString()}</div>
                </div>
                <div class="card alert">
                    <h3>Lotes Vencidos</h3>
                    <div class="value">${data.lotes_vencidos}</div>
                </div>
                <div class="card warning">
                    <h3>Críticos (≤20 días)</h3>
                    <div class="value">${data.lotes_criticos}</div>
                </div>
                <div class="card warning">
                    <h3>Bajo Stock</h3>
                    <div class="value">${data.lotes_bajo_stock}</div>
                </div>
                <div class="card success">
                    <h3>Rotación Promedio</h3>
                    <div class="value">${data.rotacion_promedio}</div>
                    <div class="subtext">unidades/lote</div>
                </div>
            `;

            document.getElementById('kpis').innerHTML = html;

            const alertas = `
                ${data.lotes_vencidos > 0 ? `
                    <div class="alert-box critical">
                        <strong>🚨 CRÍTICO:</strong> ${data.lotes_vencidos} lotes vencidos requieren acción inmediata
                    </div>
                ` : ''}
                ${data.lotes_criticos > 0 ? `
                    <div class="alert-box warning">
                        <strong>⚠️ ADVERTENCIA:</strong> ${data.lotes_criticos} lotes próximos a vencer (≤20 días)
                    </div>
                ` : ''}
                ${data.lotes_bajo_stock > 0 ? `
                    <div class="alert-box warning">
                        <strong>📉 INFO:</strong> ${data.lotes_bajo_stock} lotes con stock bajo
                    </div>
                ` : ''}
            `;

            document.getElementById('alertas').innerHTML = alertas;
            document.getElementById('updated-time').textContent = new Date().toLocaleString('es-ES');
        }

        async function loadLotes(status = '') {
            const url = '/api/lotes' + (status ? '?status=' + status : '');
            const res = await fetch(url);
            const data = await res.json();

            let html = '';
            for (const lote of data.lotes) {
                const estado = lote.dias_restantes < 0 ? 'critical' : lote.dias_restantes <= 20 ? 'warning' : 'normal';
                const estadoText = lote.dias_restantes < 0 ? 'VENCIDO' : lote.dias_restantes <= 20 ? 'CRÍTICO' : 'NORMAL';
                html += `
                    <tr>
                        <td><strong>${lote.codigo_lote}</strong></td>
                        <td>${lote.material_id}</td>
                        <td>${lote.cantidad}</td>
                        <td>${lote.ubicacion}</td>
                        <td>${lote.fecha_vencimiento}</td>
                        <td><span class="badge ${estado}">${estadoText}</span></td>
                    </tr>
                `;
            }
            document.getElementById('lotes-table').innerHTML = html;
        }

        async function loadReorden() {
            const res = await fetch('/api/reorden');
            const data = await res.json();

            let html = '';
            for (const item of data.items) {
                const urgencia = item.urgencia === 'CRÍTICA' ? 'critical' : item.urgencia === 'ALTA' ? 'warning' : 'normal';
                html += `
                    <tr>
                        <td>${item.nombre_material}</td>
                        <td>${item.codigo_lote}</td>
                        <td>${item.cantidad_actual}</td>
                        <td>${item.vencimiento}</td>
                        <td>${item.dias_restantes} días</td>
                        <td><span class="badge ${urgencia}">${item.urgencia}</span></td>
                    </tr>
                `;
            }
            document.getElementById('reorden-table').innerHTML = html;
        }

        async function loadAnalisisABC() {
            const res = await fetch('/api/analisis-abc');
            const data = await res.json();

            let html = '';
            for (const item of data.articulos) {
                const categoryColor = item.categoria === 'A' ? '#27ae60' : item.categoria === 'B' ? '#f39c12' : '#95a5a6';
                html += `
                    <tr>
                        <td>${item.nombre}</td>
                        <td>${item.cantidad}</td>
                        <td>$${item.valor.toLocaleString()}</td>
                        <td>${item.porcentaje_valor}%</td>
                        <td><span style="background: ${categoryColor}20; color: ${categoryColor}; padding: 4px 12px; border-radius: 12px; font-weight: 600;">Cat. ${item.categoria}</span></td>
                    </tr>
                `;
            }
            document.getElementById('analisis-table').innerHTML = html;
        }

        async function loadObsolescencia() {
            const res = await fetch('/api/obsolescencia');
            const data = await res.json();

            let html = `<p><strong>Riesgo Global: </strong><span style="color: ${data.riesgo_obsolescencia === 'ALTO' ? 'red' : data.riesgo_obsolescencia === 'MEDIO' ? 'orange' : 'green'}">${data.riesgo_obsolescencia}</span></p>`;

            if (data.lotes_vencidos > 0) {
                html += '<h3>Lotes Vencidos</h3><table><tr><th>Lote</th><th>Material</th><th>Cantidad</th><th>Días Vencido</th></tr>';
                for (const item of data.vencidos) {
                    html += `<tr><td>${item.codigo_lote}</td><td>${item.material}</td><td>${item.cantidad}</td><td>${item.dias_vencido}</td></tr>`;
                }
                html += '</table>';
            }

            if (data.lotes_criticos > 0) {
                html += '<h3 style="margin-top: 20px;">Próximos a Vencer</h3><table><tr><th>Lote</th><th>Material</th><th>Cantidad</th><th>Días Restantes</th></tr>';
                for (const item of data.criticos) {
                    html += `<tr><td>${item.codigo_lote}</td><td>${item.material}</td><td>${item.cantidad}</td><td>${item.dias_restantes}</td></tr>`;
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
                const recomColor = item.recomendacion.includes('Aumentar') ? 'red' : item.recomendacion.includes('Reducir') ? 'orange' : 'green';
                html += `
                    <tr>
                        <td>${item.nombre}</td>
                        <td>${item.cantidad_stock}</td>
                        <td><strong>${item.rotacion_anual}x</strong></td>
                        <td>${item.dias_almacenamiento_promedio} días</td>
                        <td><span style="color: ${recomColor}; font-weight: 600;">${item.recomendacion}</span></td>
                    </tr>
                `;
            }
            document.getElementById('optimizacion-table').innerHTML = html;
        }

        // Load dashboard on page load
        window.onload = () => loadDashboard();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Página principal - Dashboard web"""
    return render_template_string(HTML_TEMPLATE)

# ============================================================
# MAIN
# ============================================================

if __name__ == '__main__':
    print("""
    ╔════════════════════════════════════════════════════════╗
    ║    ÁNIMUS Lab + Espagiria Laboratorio                 ║
    ║    Sistema Integrado de Gestión de Inventarios        ║
    ╠════════════════════════════════════════════════════════╣
    ║  ✅ Base de Datos: 322 lotes cargados                  ║
    ║  ✅ Monitoreo de Stock: Activo                         ║
    ║  ✅ Análisis ABC: Disponible                           ║
    ║  ✅ Reorden Automático: 20 días antes                  ║
    ║  ✅ Optimización: Habilitada                           ║
    ║                                                        ║
    ║  🚀 Acceder a: http://localhost:5000                  ║
    ║  📊 API: http://localhost:5000/api/*                  ║
    ╚════════════════════════════════════════════════════════╝
    """)

    app.run(debug=True, host='0.0.0.0', port=5000)
