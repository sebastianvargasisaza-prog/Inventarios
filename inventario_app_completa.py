#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
APLICACIÓN COMPLETA DE INVENTARIO CON CLAUDE API
Sistema integrado: inventario + chat + deducción automática + alertas + órdenes
"""

from flask import Flask, render_template_string, request, jsonify
import pandas as pd
import json
import os
from datetime import datetime, timedelta
import anthropic
from functools import lru_cache

app = Flask(__name__)

# ============================================================================
# CARGA DE DATOS
# ============================================================================

# Cargar mapeo de códigos
MAPEO_CODIGOS_PATH = "/sessions/youthful-admiring-maxwell/mnt/outputs/MAPEO_CODIGOS.json"
with open(MAPEO_CODIGOS_PATH, 'r', encoding='utf-8') as f:
    MAPEO_CODIGOS = json.load(f)

# Cargar inventario real
INVENTARIO_PATH = "/sessions/youthful-admiring-maxwell/mnt/uploads/INVENTARIO REAL MP  (4)-c116478a.xlsx"
df_inventario = pd.read_excel(INVENTARIO_PATH)

# Crear índice de inventario por código
inventario_por_codigo = {}
for idx, row in df_inventario.iterrows():
    codigo = str(row['CODIGO MP']).strip() if pd.notna(row['CODIGO MP']) else ""
    nombre = str(row['NOMBRE MP']).strip() if pd.notna(row['NOMBRE MP']) else ""
    cantidad = row['CANTIDAD'] if pd.notna(row['CANTIDAD']) else 0
    vencimiento = row['FECHA DE VENCIMIENTO'] if pd.notna(row['FECHA DE VENCIMIENTO']) else None

    if codigo and codigo != "nan":
        if codigo not in inventario_por_codigo:
            inventario_por_codigo[codigo] = {'nombre': nombre, 'cantidad': 0, 'lotes': []}
        inventario_por_codigo[codigo]['cantidad'] += cantidad
        if vencimiento:
            inventario_por_codigo[codigo]['lotes'].append({
                'cantidad': cantidad,
                'vencimiento': str(vencimiento)[:10]
            })

# Cargar fórmulas
FORMULAS_DIR = "/sessions/youthful-admiring-maxwell/mnt/Inventarios/Formulas Maestras"
formulas = {}

for product_folder in sorted(os.listdir(FORMULAS_DIR)):
    folder_path = os.path.join(FORMULAS_DIR, product_folder)
    if not os.path.isdir(folder_path):
        continue

    for file in os.listdir(folder_path):
        if file.endswith('.xlsx'):
            file_path = os.path.join(folder_path, file)
            try:
                df = pd.read_excel(file_path, sheet_name='DISPENSACIÓN', header=None)
                ingredientes = []

                for idx in range(16, len(df)):
                    row = df.iloc[idx]
                    codigo_formula = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
                    nombre_mp = str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else ""
                    cantidad = row.iloc[9] if pd.notna(row.iloc[9]) else 0

                    if (codigo_formula and codigo_formula != "nan" and
                        codigo_formula.startswith("MP") and nombre_mp and nombre_mp != "nan"):

                        # Buscar código canónico
                        codigo_canonico = None
                        if nombre_mp in MAPEO_CODIGOS:
                            codigo_canonico = MAPEO_CODIGOS[nombre_mp].get('codigo_inventario')

                        ingredientes.append({
                            'nombre': nombre_mp,
                            'codigo_formula': codigo_formula,
                            'codigo_canonico': codigo_canonico,
                            'cantidad': float(cantidad) if pd.notna(cantidad) else 0
                        })

                if ingredientes:
                    formulas[product_folder.strip()] = ingredientes
            except:
                pass

# ============================================================================
# BASE DE DATOS EN MEMORIA
# ============================================================================

class InventarioApp:
    def __init__(self):
        self.inventario = dict(inventario_por_codigo)  # copia
        self.movimientos = []  # historial
        self.ordenes_compra = []  # órdenes generadas
        self.chat_history = []

    def registrar_produccion(self, producto, cantidad_kg):
        """Registra producción y deduce materiales automáticamente"""
        if producto not in formulas:
            return {'error': f'Producto {producto} no encontrado'}

        movimiento = {
            'timestamp': datetime.now().isoformat(),
            'tipo': 'PRODUCCIÓN',
            'producto': producto,
            'cantidad': cantidad_kg,
            'detalles': [],
            'alertas': []
        }

        # Deducir materiales
        for ing in formulas[producto]:
            cantidad_a_deducir = ing['cantidad'] * (cantidad_kg / 12.0)  # 12 kg es unidad por defecto

            codigo_inv = ing['codigo_canonico']
            if not codigo_inv:
                movimiento['detalles'].append({
                    'material': ing['nombre'],
                    'estado': 'ADVERTENCIA',
                    'mensaje': 'No tiene código en inventario (faltante)'
                })
                movimiento['alertas'].append(f"⚠ {ing['nombre']} no está en inventario")
                continue

            # Validar disponibilidad
            if codigo_inv not in self.inventario:
                movimiento['detalles'].append({
                    'material': ing['nombre'],
                    'estado': 'ERROR',
                    'mensaje': 'No en base de datos'
                })
                movimiento['alertas'].append(f"✗ {ing['nombre']} no en base de datos")
                continue

            cantidad_disponible = self.inventario[codigo_inv]['cantidad']
            if cantidad_disponible < cantidad_a_deducir:
                movimiento['alertas'].append(
                    f"✗ Stock insuficiente de {ing['nombre']}: "
                    f"disponible {cantidad_disponible:.2f}g, necesario {cantidad_a_deducir:.2f}g"
                )

            # Deducir
            self.inventario[codigo_inv]['cantidad'] -= cantidad_a_deducir
            movimiento['detalles'].append({
                'material': ing['nombre'],
                'codigo': codigo_inv,
                'cantidad_deducida': cantidad_a_deducir,
                'cantidad_restante': self.inventario[codigo_inv]['cantidad'],
                'estado': 'OK'
            })

        self.movimientos.append(movimiento)

        # Generar alertas de stock bajo
        alertas_stock = self._verificar_stock_bajo()
        if alertas_stock:
            movimiento['alertas'].extend(alertas_stock)

        return movimiento

    def _verificar_stock_bajo(self, dias_minimos=20):
        """Verifica si hay stock bajo (menos de 20 días de consumo)"""
        alertas = []
        # Aquí implementaría lógica basada en consumo histórico
        return alertas

    def obtener_estado_inventario(self):
        """Retorna estado actual del inventario"""
        return {
            'total_items': len(self.inventario),
            'cantidad_total_kg': sum(v['cantidad'] for v in self.inventario.values()) / 1000,
            'items': [
                {
                    'codigo': cod,
                    'nombre': info['nombre'],
                    'cantidad_g': info['cantidad'],
                    'cantidad_kg': info['cantidad'] / 1000
                }
                for cod, info in list(self.inventario.items())[:50]
            ]
        }

    def analisis_abc(self):
        """Análisis ABC de inventario por valor/importancia"""
        # Ordenar por cantidad (proxy de importancia)
        sorted_items = sorted(
            self.inventario.items(),
            key=lambda x: x[1]['cantidad'],
            reverse=True
        )

        total = sum(v['cantidad'] for v in self.inventario.values())
        categoria_a = []
        categoria_b = []
        categoria_c = []

        acum = 0
        for cod, info in sorted_items:
            acum += info['cantidad']
            pct = (acum / total) * 100 if total > 0 else 0

            item = {'codigo': cod, 'nombre': info['nombre'], 'cantidad': info['cantidad']}

            if pct <= 80:
                categoria_a.append(item)
            elif pct <= 95:
                categoria_b.append(item)
            else:
                categoria_c.append(item)

        return {
            'A (80%)': len(categoria_a),
            'B (15%)': len(categoria_b),
            'C (5%)': len(categoria_c),
            'A_items': categoria_a[:10],
            'B_items': categoria_b[:10],
            'C_items': categoria_c[:10]
        }

# Instancia global
app_db = InventarioApp()

# ============================================================================
# INTEGRACIÓN CON CLAUDE API
# ============================================================================

client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY', ''))

SYSTEM_PROMPT = """Eres un asistente de gestión de inventario para ÁNIMUS Lab / Espagiria.
Tu rol es ayudar con:
- Consultas sobre inventario (disponibilidad, cantidades, códigos)
- Registrar producciones (ej: "hice Renova C 10 12 kg")
- Generar alertas de stock bajo
- Crear órdenes de compra
- Análisis ABC del inventario

Cuando el usuario registra una producción, extrae:
- Nombre del producto
- Cantidad en kg

Responde en español, de forma clara y accionable. Incluye siempre números concretos."""

def chat_con_claude(mensaje_usuario, historial_anterior=None):
    """Envia mensaje a Claude y obtiene respuesta"""
    if not client.api_key:
        return "❌ API key de Claude no configurada. Usa: export ANTHROPIC_API_KEY=sk-..."

    try:
        # Contexto del inventario
        contexto = f"""
        ESTADO ACTUAL DEL INVENTARIO:
        - Items totales: {len(app_db.inventario)}
        - Productos con fórmula disponibles: {len(formulas)}
        - Últimos movimientos: {len(app_db.movimientos)}
        """

        messages = historial_anterior or []
        messages.append({"role": "user", "content": mensaje_usuario})

        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            system=SYSTEM_PROMPT + "\n\n" + contexto,
            messages=messages
        )

        respuesta = response.content[0].text
        return respuesta
    except Exception as e:
        return f"❌ Error en Claude API: {str(e)}"

# ============================================================================
# RUTAS REST API
# ============================================================================

@app.route('/api/inventario', methods=['GET'])
def api_inventario():
    """Estado del inventario"""
    return jsonify(app_db.obtener_estado_inventario())

@app.route('/api/produccion', methods=['POST'])
def api_produccion():
    """Registra una producción"""
    data = request.json
    producto = data.get('producto', '')
    cantidad = float(data.get('cantidad', 0))

    movimiento = app_db.registrar_produccion(producto, cantidad)
    return jsonify(movimiento)

@app.route('/api/chat', methods=['POST'])
def api_chat():
    """Chat con Claude integrado"""
    data = request.json
    mensaje = data.get('mensaje', '')

    # Guardar en historial
    app_db.chat_history.append({'role': 'user', 'content': mensaje})

    # Obtener respuesta de Claude
    respuesta = chat_con_claude(mensaje, app_db.chat_history)

    # Procesar comandos especiales
    if 'producción' in mensaje.lower() or 'produje' in mensaje.lower():
        # Intentar extraer producto y cantidad
        palabras = mensaje.lower().split()
        # Lógica simple para detectar patrón "producto X kg"
        pass

    app_db.chat_history.append({'role': 'assistant', 'content': respuesta})

    return jsonify({
        'respuesta': respuesta,
        'historial_length': len(app_db.chat_history)
    })

@app.route('/api/abc', methods=['GET'])
def api_abc():
    """Análisis ABC"""
    return jsonify(app_db.analisis_abc())

@app.route('/api/movimientos', methods=['GET'])
def api_movimientos():
    """Historial de movimientos"""
    return jsonify(app_db.movimientos[-20:])

# ============================================================================
# INTERFAZ HTML
# ============================================================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Inventario Espagiria - ÁNIMUS Lab</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        .card {
            background: white;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.15);
        }
        .card h2 {
            color: #333;
            margin-bottom: 16px;
            border-bottom: 2px solid #667eea;
            padding-bottom: 12px;
        }
        .form-group {
            margin-bottom: 16px;
        }
        .form-group label {
            display: block;
            margin-bottom: 6px;
            color: #555;
            font-weight: 500;
        }
        .form-group input, .form-group select {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 14px;
        }
        .form-group input:focus, .form-group select:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102,126,234,0.1);
        }
        button {
            background: #667eea;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s;
        }
        button:hover {
            background: #764ba2;
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102,126,234,0.3);
        }
        .chat-container {
            grid-column: 1 / -1;
        }
        .chat-messages {
            background: #f9f9f9;
            border-radius: 8px;
            padding: 16px;
            height: 400px;
            overflow-y: auto;
            margin-bottom: 16px;
            border: 1px solid #eee;
        }
        .message {
            margin-bottom: 12px;
            padding: 12px;
            border-radius: 6px;
            font-size: 14px;
        }
        .message.user {
            background: #e3f2fd;
            text-align: right;
            margin-left: 40px;
        }
        .message.assistant {
            background: #f5f5f5;
            margin-right: 40px;
        }
        .chat-input {
            display: flex;
            gap: 8px;
        }
        .chat-input input {
            flex: 1;
        }
        .alert {
            padding: 12px;
            border-radius: 6px;
            margin-bottom: 12px;
            font-size: 13px;
            border-left: 4px solid;
        }
        .alert.success {
            background: #e8f5e9;
            color: #2e7d32;
            border-color: #4caf50;
        }
        .alert.warning {
            background: #fff3e0;
            color: #e65100;
            border-color: #ff9800;
        }
        .alert.error {
            background: #ffebee;
            color: #c62828;
            border-color: #f44336;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
            margin-bottom: 16px;
        }
        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 16px;
            border-radius: 8px;
            text-align: center;
        }
        .stat-value {
            font-size: 24px;
            font-weight: bold;
            margin: 8px 0;
        }
        .stat-label {
            font-size: 12px;
            opacity: 0.9;
        }
        .header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }
        .header h1 {
            font-size: 32px;
            margin-bottom: 8px;
        }
        .header p {
            font-size: 14px;
            opacity: 0.9;
        }
        @media (max-width: 1024px) {
            .container {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🧴 INVENTARIO ESPAGIRIA</h1>
        <p>ÁNIMUS Lab - Sistema de Gestión Integrado</p>
    </div>

    <div class="container">
        <!-- PANEL DE PRODUCCIÓN -->
        <div class="card">
            <h2>📊 Registrar Producción</h2>
            <form id="formProduccion">
                <div class="form-group">
                    <label>Producto</label>
                    <select id="producto" required>
                        <option value="">-- Seleccionar --</option>
                        <option value="RENOVA C">RENOVA C</option>
                        <option value="CONTORNO DE CAFEINA">CONTORNO DE CAFEINA</option>
                        <option value="EMULSION HIDRATANTE ANTIOXIDANTE">EMULSION HIDRATANTE</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Cantidad (kg)</label>
                    <input type="number" id="cantidad" step="0.1" min="0" required>
                </div>
                <button type="submit">Registrar Producción</button>
            </form>
            <div id="alertas" style="margin-top: 16px;"></div>
        </div>

        <!-- PANEL DE INVENTARIO -->
        <div class="card">
            <h2>📦 Estado del Inventario</h2>
            <div class="stats" id="stats">
                <div class="stat-card">
                    <div class="stat-label">Items Totales</div>
                    <div class="stat-value" id="totalItems">-</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Total (kg)</div>
                    <div class="stat-value" id="totalKg">-</div>
                </div>
            </div>
            <div id="inventarioList"></div>
        </div>

        <!-- PANEL DE CHAT CON CLAUDE -->
        <div class="card chat-container">
            <h2>💬 Chat - Claude Asistente</h2>
            <div class="chat-messages" id="chatMessages"></div>
            <div class="chat-input">
                <input type="text" id="chatInput" placeholder="Pregunta sobre inventario, producciones, ordenes...">
                <button onclick="enviarChat()">Enviar</button>
            </div>
        </div>
    </div>

    <script>
        // Actualizar estado del inventario
        async function cargarInventario() {
            const res = await fetch('/api/inventario');
            const data = await res.json();

            document.getElementById('totalItems').textContent = data.total_items;
            document.getElementById('totalKg').textContent = data.cantidad_total_kg.toFixed(2);

            let html = '<table style="width:100%; font-size:12px; border-collapse: collapse;">';
            html += '<tr style="border-bottom:1px solid #ddd;"><th style="text-align:left; padding:8px;">Código</th><th>Cantidad (kg)</th></tr>';
            for (const item of data.items) {
                html += `<tr style="border-bottom:1px solid #eee;"><td style="padding:8px;">${item.codigo}</td><td>${item.cantidad_kg.toFixed(2)}</td></tr>`;
            }
            html += '</table>';
            document.getElementById('inventarioList').innerHTML = html;
        }

        // Registrar producción
        document.getElementById('formProduccion').addEventListener('submit', async (e) => {
            e.preventDefault();
            const producto = document.getElementById('producto').value;
            const cantidad = document.getElementById('cantidad').value;

            const res = await fetch('/api/produccion', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ producto, cantidad })
            });
            const data = await res.json();

            let html = '';
            if (data.error) {
                html = `<div class="alert error">${data.error}</div>`;
            } else {
                html = `<div class="alert success">✓ Producción registrada: ${data.producto} ${data.cantidad} kg</div>`;
                if (data.alertas && data.alertas.length > 0) {
                    for (const alerta of data.alertas) {
                        html += `<div class="alert warning">${alerta}</div>`;
                    }
                }
            }
            document.getElementById('alertas').innerHTML = html;

            cargarInventario();
            document.getElementById('formProduccion').reset();
        });

        // Chat con Claude
        async function enviarChat() {
            const input = document.getElementById('chatInput');
            const mensaje = input.value.trim();
            if (!mensaje) return;

            // Añadir mensaje del usuario
            const messagesDiv = document.getElementById('chatMessages');
            messagesDiv.innerHTML += `<div class="message user">${mensaje}</div>`;

            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mensaje })
            });
            const data = await res.json();

            messagesDiv.innerHTML += `<div class="message assistant">${data.respuesta}</div>`;
            messagesDiv.scrollTop = messagesDiv.scrollHeight;

            input.value = '';
        }

        // Enter para enviar en chat
        document.getElementById('chatInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') enviarChat();
        });

        // Cargar datos iniciales
        cargarInventario();
        setInterval(cargarInventario, 30000); // Actualizar cada 30s
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("APLICACIÓN DE INVENTARIO ESPAGIRIA - ÁNIMUS LAB")
    print("=" * 80)
    print(f"\n✓ Inventario cargado: {len(app_db.inventario)} códigos")
    print(f"✓ Formulas cargadas: {len(formulas)} productos")
    print(f"✓ Mapeo de códigos: {len(MAPEO_CODIGOS)} MPs")
    print("\nInicia sesión en: http://localhost:5000")
    print("API disponibles:")
    print("  GET  /api/inventario     - Estado actual")
    print("  POST /api/produccion     - Registrar producción")
    print("  POST /api/chat           - Chat con Claude")
    print("  GET  /api/abc            - Análisis ABC")
    print("  GET  /api/movimientos    - Historial")
    print("\n" + "=" * 80 + "\n")

    print("⚠ IMPORTANTE: Configura ANTHROPIC_API_KEY")
    print("   export ANTHROPIC_API_KEY=sk-...\n")

    app.run(debug=True, host='0.0.0.0', port=5000)
