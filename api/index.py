import os
import json
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, render_template_string
from anthropic import Anthropic
import pandas as pd

app = Flask(__name__)
client = Anthropic()

# Database path
DB_PATH = '/tmp/inventario.db'

def init_db():
    """Initialize SQLite database with required tables"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Create movimientos table
    c.execute('''CREATE TABLE IF NOT EXISTS movimientos
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  material_id TEXT,
                  material_nombre TEXT,
                  cantidad REAL,
                  tipo TEXT,
                  fecha TEXT,
                  observaciones TEXT)''')

    # Create producciones table
    c.execute('''CREATE TABLE IF NOT EXISTS producciones
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  producto TEXT,
                  cantidad REAL,
                  fecha TEXT,
                  estado TEXT,
                  observaciones TEXT)''')

    # Create alertas table
    c.execute('''CREATE TABLE IF NOT EXISTS alertas
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  material_id TEXT,
                  material_nombre TEXT,
                  stock_actual REAL,
                  stock_minimo REAL,
                  fecha TEXT,
                  estado TEXT)''')

    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

# HTML Dashboard Template
DASHBOARD_HTML = '''<\!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sistema de Inventarios - ÁNIMUS Lab</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }

        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }

        .header p {
            font-size: 1.1em;
            opacity: 0.9;
        }

        .tabs {
            display: flex;
            background: #f5f5f5;
            border-bottom: 2px solid #ddd;
            overflow-x: auto;
        }

        .tab-button {
            flex: 1;
            padding: 15px 20px;
            background: none;
            border: none;
            cursor: pointer;
            font-size: 1em;
            font-weight: 500;
            color: #666;
            transition: all 0.3s;
            white-space: nowrap;
        }

        .tab-button:hover {
            background: white;
            color: #667eea;
        }

        .tab-button.active {
            background: white;
            color: #667eea;
            border-bottom: 3px solid #667eea;
        }

        .tab-content {
            display: none;
            padding: 30px;
            animation: fadeIn 0.3s;
        }

        .tab-content.active {
            display: block;
        }

        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        .form-group {
            margin-bottom: 20px;
        }

        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #333;
        }

        input, textarea, select {
            width: 100%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 6px;
            font-size: 1em;
            transition: border-color 0.3s;
        }

        input:focus, textarea:focus, select:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 30px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 1em;
            font-weight: 600;
            transition: transform 0.2s, box-shadow 0.2s;
        }

        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
        }

        .table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }

        .table th {
            background: #f5f5f5;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: #333;
            border-bottom: 2px solid #ddd;
        }

        .table td {
            padding: 12px;
            border-bottom: 1px solid #ddd;
        }

        .table tr:hover {
            background: #f9f9f9;
        }

        .alert {
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 20px;
        }

        .alert-success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }

        .alert-error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }

        .alert-info {
            background: #d1ecf1;
            color: #0c5460;
            border: 1px solid #bee5eb;
        }

        .chat-container {
            height: 500px;
            display: flex;
            flex-direction: column;
            background: #f9f9f9;
            border: 2px solid #ddd;
            border-radius: 6px;
            overflow: hidden;
        }

        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 15px;
        }

        .message {
            padding: 12px 16px;
            border-radius: 6px;
            max-width: 80%;
            word-wrap: break-word;
        }

        .message.user {
            background: #667eea;
            color: white;
            align-self: flex-end;
        }

        .message.assistant {
            background: white;
            color: #333;
            border: 1px solid #ddd;
            align-self: flex-start;
        }

        .chat-input {
            display: flex;
            gap: 10px;
            padding: 15px;
            background: white;
            border-top: 2px solid #ddd;
        }

        .chat-input input {
            flex: 1;
            margin: 0;
        }

        .chat-input button {
            width: 100px;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .card {
            background: white;
            border: 2px solid #ddd;
            border-radius: 6px;
            padding: 20px;
            text-align: center;
        }

        .card h3 {
            color: #667eea;
            margin-bottom: 10px;
        }

        .card p {
            font-size: 2em;
            font-weight: bold;
            color: #333;
        }

        .abc-item {
            padding: 15px;
            background: #f9f9f9;
            border-radius: 6px;
            margin-bottom: 10px;
            border-left: 4px solid #667eea;
        }

        .abc-item.A {
            border-left-color: #ff6b6b;
        }

        .abc-item.B {
            border-left-color: #ffd93d;
        }

        .abc-item.C {
            border-left-color: #6bcf7f;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📦 Sistema de Inventarios</h1>
            <p>ÁNIMUS Lab - Gestión Inteligente de Inventario</p>
        </div>

        <div class="tabs">
            <button class="tab-button active" onclick="switchTab('dashboard')">📊 Dashboard</button>
            <button class="tab-button" onclick="switchTab('produccion')">🏭 Registrar Producción</button>
            <button class="tab-button" onclick="switchTab('abc')">📈 Análisis ABC</button>
            <button class="tab-button" onclick="switchTab('alertas')">⚠️ Alertas</button>
            <button class="tab-button" onclick="switchTab('chat')">🤖 Chat IA</button>
            <button class="tab-button" onclick="switchTab('movimientos')">📋 Movimientos</button>
        </div>

        <\!-- Dashboard Tab -->
        <div id="dashboard" class="tab-content active">
            <h2>Dashboard Principal</h2>
            <div class="grid">
                <div class="card">
                    <h3>Stock Total</h3>
                    <p id="stock-total">0</p>
                </div>
                <div class="card">
                    <h3>Movimientos</h3>
                    <p id="movimientos-count">0</p>
                </div>
                <div class="card">
                    <h3>Alertas</h3>
                    <p id="alertas-count">0</p>
                </div>
                <div class="card">
                    <h3>Producciones</h3>
                    <p id="producciones-count">0</p>
                </div>
            </div>
            <button onclick="loadDashboard()">Actualizar Dashboard</button>
        </div>

        <\!-- Producción Tab -->
        <div id="produccion" class="tab-content">
            <h2>Registrar Producción</h2>
            <div class="form-group">
                <label>Producto</label>
                <input type="text" id="producto" placeholder="Nombre del producto">
            </div>
            <div class="form-group">
                <label>Cantidad</label>
                <input type="number" id="cantidad" placeholder="Cantidad producida" step="0.01">
            </div>
            <div class="form-group">
                <label>Observaciones</label>
                <textarea id="obs-prod" placeholder="Observaciones adicionales" rows="4"></textarea>
            </div>
            <button onclick="registrarProduccion()">Registrar Producción</button>
            <div id="prod-response"></div>
        </div>

        <\!-- ABC Tab -->
        <div id="abc" class="tab-content">
            <h2>Análisis ABC del Inventario</h2>
            <button onclick="loadABC()">Generar Análisis ABC</button>
            <div id="abc-results" style="margin-top: 20px;"></div>
        </div>

        <\!-- Alertas Tab -->
        <div id="alertas" class="tab-content">
            <h2>Gestión de Alertas</h2>
            <button onclick="loadAlertas()">Cargar Alertas</button>
            <table class="table" id="alertas-table" style="margin-top: 20px;">
                <thead>
                    <tr>
                        <th>Material</th>
                        <th>Stock Actual</th>
                        <th>Stock Mínimo</th>
                        <th>Estado</th>
                        <th>Fecha</th>
                    </tr>
                </thead>
                <tbody></tbody>
            </table>
        </div>

        <\!-- Chat IA Tab -->
        <div id="chat" class="tab-content">
            <h2>Chat con IA - Asesor de Inventario</h2>
            <div class="chat-container">
                <div class="chat-messages" id="chat-messages"></div>
                <div class="chat-input">
                    <input type="text" id="chat-input" placeholder="Escribe tu pregunta..." onkeypress="if(event.key==='Enter') enviarChat()">
                    <button onclick="enviarChat()">Enviar</button>
                </div>
            </div>
        </div>

        <\!-- Movimientos Tab -->
        <div id="movimientos" class="tab-content">
            <h2>Registro de Movimientos</h2>
            <div class="form-group">
                <label>Material ID</label>
                <input type="text" id="material-id" placeholder="ID del material">
            </div>
            <div class="form-group">
                <label>Nombre Material</label>
                <input type="text" id="material-nombre" placeholder="Nombre del material">
            </div>
            <div class="form-group">
                <label>Cantidad</label>
                <input type="number" id="movimiento-cantidad" placeholder="Cantidad" step="0.01">
            </div>
            <div class="form-group">
                <label>Tipo</label>
                <select id="movimiento-tipo">
                    <option>Entrada</option>
                    <option>Salida</option>
                    <option>Ajuste</option>
                </select>
            </div>
            <div class="form-group">
                <label>Observaciones</label>
                <textarea id="movimiento-obs" placeholder="Observaciones" rows="3"></textarea>
            </div>
            <button onclick="registrarMovimiento()">Registrar Movimiento</button>
            <div id="movimiento-response"></div>

            <h3 style="margin-top: 30px;">Historial de Movimientos</h3>
            <button onclick="loadMovimientos()">Cargar Movimientos</button>
            <table class="table" id="movimientos-table" style="margin-top: 20px;">
                <thead>
                    <tr>
                        <th>Material</th>
                        <th>Cantidad</th>
                        <th>Tipo</th>
                        <th>Fecha</th>
                        <th>Observaciones</th>
                    </tr>
                </thead>
                <tbody></tbody>
            </table>
        </div>
    </div>

    <script>
        function switchTab(tabName) {
            // Hide all tabs
            const tabs = document.querySelectorAll('.tab-content');
            tabs.forEach(tab => tab.classList.remove('active'));

            // Remove active class from buttons
            const buttons = document.querySelectorAll('.tab-button');
            buttons.forEach(btn => btn.classList.remove('active'));

            // Show selected tab
            document.getElementById(tabName).classList.add('active');

            // Mark button as active
            event.target.classList.add('active');
        }

        async function registrarMovimiento() {
            const data = {
                material_id: document.getElementById('material-id').value,
                material_nombre: document.getElementById('material-nombre').value,
                cantidad: parseFloat(document.getElementById('movimiento-cantidad').value),
                tipo: document.getElementById('movimiento-tipo').value,
                observaciones: document.getElementById('movimiento-obs').value
            };

            try {
                const response = await fetch('/api/movimientos', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                const result = await response.json();
                showAlert(result.message || 'Movimiento registrado', 'success');
                document.getElementById('movimiento-response').innerHTML =
                    '<div class="alert alert-success">' + result.message + '</div>';
            } catch (error) {
                showAlert('Error: ' + error.message, 'error');
            }
        }

        async function registrarProduccion() {
            const data = {
                producto: document.getElementById('producto').value,
                cantidad: parseFloat(document.getElementById('cantidad').value),
                observaciones: document.getElementById('obs-prod').value
            };

            try {
                const response = await fetch('/api/produccion', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                const result = await response.json();
                document.getElementById('prod-response').innerHTML =
                    '<div class="alert alert-success">' + result.message + '</div>';
                setTimeout(() => {
                    document.getElementById('producto').value = '';
                    document.getElementById('cantidad').value = '';
                    document.getElementById('obs-prod').value = '';
                }, 1500);
            } catch (error) {
                document.getElementById('prod-response').innerHTML =
                    '<div class="alert alert-error">Error: ' + error.message + '</div>';
            }
        }

        async function loadDashboard() {
            try {
                const response = await fetch('/api/inventario');
                const data = await response.json();
                document.getElementById('stock-total').textContent = data.total_items || '0';
                document.getElementById('movimientos-count').textContent = data.movimientos || '0';
                document.getElementById('alertas-count').textContent = data.alertas || '0';
                document.getElementById('producciones-count').textContent = data.producciones || '0';
            } catch (error) {
                console.error('Error loading dashboard:', error);
            }
        }

        async function loadABC() {
            try {
                const response = await fetch('/api/analisis-abc');
                const data = await response.json();
                let html = '';
                if (data.items && data.items.length > 0) {
                    data.items.forEach(item => {
                        html += `<div class="abc-item ${item.clasificacion}">
                            <strong>${item.material}</strong> - Clasificación: ${item.clasificacion}<br>
                            Cantidad: ${item.cantidad} | Valor: ${item.valor}
                        </div>`;
                    });
                } else {
                    html = '<p>No hay datos para el análisis ABC</p>';
                }
                document.getElementById('abc-results').innerHTML = html;
            } catch (error) {
                document.getElementById('abc-results').innerHTML =
                    '<div class="alert alert-error">Error: ' + error.message + '</div>';
            }
        }

        async function loadAlertas() {
            try {
                const response = await fetch('/api/alertas');
                const data = response.ok ? await response.json() : {alertas: []};
                const tbody = document.querySelector('#alertas-table tbody');
                tbody.innerHTML = '';

                if (data.alertas && data.alertas.length > 0) {
                    data.alertas.forEach(alerta => {
                        tbody.innerHTML += `<tr>
                            <td>${alerta.material_nombre}</td>
                            <td>${alerta.stock_actual}</td>
                            <td>${alerta.stock_minimo}</td>
                            <td>${alerta.estado}</td>
                            <td>${alerta.fecha}</td>
                        </tr>`;
                    });
                } else {
                    tbody.innerHTML = '<tr><td colspan="5">No hay alertas</td></tr>';
                }
            } catch (error) {
                console.error('Error loading alertas:', error);
            }
        }

        async function loadMovimientos() {
            try {
                const response = await fetch('/api/movimientos');
                const data = response.ok ? await response.json() : {movimientos: []};
                const tbody = document.querySelector('#movimientos-table tbody');
                tbody.innerHTML = '';

                if (data.movimientos && data.movimientos.length > 0) {
                    data.movimientos.forEach(mov => {
                        tbody.innerHTML += `<tr>
                            <td>${mov.material_nombre}</td>
                            <td>${mov.cantidad}</td>
                            <td>${mov.tipo}</td>
                            <td>${mov.fecha}</td>
                            <td>${mov.observaciones}</td>
                        </tr>`;
                    });
                } else {
                    tbody.innerHTML = '<tr><td colspan="5">No hay movimientos registrados</td></tr>';
                }
            } catch (error) {
                console.error('Error loading movimientos:', error);
            }
        }

        async function enviarChat() {
            const input = document.getElementById('chat-input');
            const message = input.value.trim();
            if (\!message) return;

            const chatMessages = document.getElementById('chat-messages');
            chatMessages.innerHTML += `<div class="message user">${message}</div>`;
            input.value = '';

            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message: message})
                });
                const data = await response.json();
                chatMessages.innerHTML += `<div class="message assistant">${data.response}</div>`;
                chatMessages.scrollTop = chatMessages.scrollHeight;
            } catch (error) {
                chatMessages.innerHTML += `<div class="message assistant">Error: ${error.message}</div>`;
            }
        }

        function showAlert(message, type) {
            console.log(type + ': ' + message);
        }

        // Load dashboard on page load
        window.onload = loadDashboard;
    </script>
</body>
</html>
'''

# API Endpoints
@app.route('/')
def index():
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'message': 'Inventory system is running'})

@app.route('/api/inventario')
def get_inventario():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('SELECT COUNT(*) FROM movimientos')
    movimientos = c.fetchone()[0]

    c.execute('SELECT COUNT(*) FROM producciones')
    producciones = c.fetchone()[0]

    c.execute('SELECT COUNT(*) FROM alertas')
    alertas = c.fetchone()[0]

    conn.close()

    return jsonify({
        'total_items': movimientos + producciones,
        'movimientos': movimientos,
        'producciones': producciones,
        'alertas': alertas
    })

@app.route('/api/movimientos', methods=['GET', 'POST'])
def handle_movimientos():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if request.method == 'POST':
        data = request.json
        c.execute('''INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, observaciones)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (data['material_id'], data['material_nombre'], data['cantidad'],
                   data['tipo'], datetime.now().isoformat(), data.get('observaciones', '')))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Movimiento registrado exitosamente'}), 201

    c.execute('SELECT material_nombre, cantidad, tipo, fecha, observaciones FROM movimientos ORDER BY fecha DESC LIMIT 100')
    movimientos = [{'material_nombre': row[0], 'cantidad': row[1], 'tipo': row[2], 'fecha': row[3], 'observaciones': row[4]} for row in c.fetchall()]
    conn.close()
    return jsonify({'movimientos': movimientos})

@app.route('/api/produccion', methods=['GET', 'POST'])
def handle_produccion():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if request.method == 'POST':
        data = request.json
        c.execute('''INSERT INTO producciones (producto, cantidad, fecha, estado, observaciones)
                     VALUES (?, ?, ?, ?, ?)''',
                  (data['producto'], data['cantidad'], datetime.now().isoformat(), 'Completado', data.get('observaciones', '')))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Producción registrada exitosamente'}), 201

    c.execute('SELECT producto, cantidad, fecha, estado FROM producciones ORDER BY fecha DESC LIMIT 50')
    producciones = [{'producto': row[0], 'cantidad': row[1], 'fecha': row[2], 'estado': row[3]} for row in c.fetchall()]
    conn.close()
    return jsonify({'producciones': producciones})

@app.route('/api/chat', methods=['POST'])
def handle_chat():
    data = request.json
    user_message = data.get('message', '')

    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": f"Eres un asesor experto en gestión de inventarios. Responde brevemente en español. Pregunta: {user_message}"}
            ]
        )
        assistant_message = response.content[0].text
        return jsonify({'response': assistant_message})
    except Exception as e:
        return jsonify({'response': f'Error en el chat: {str(e)}'}), 500

@app.route('/api/analisis-abc', methods=['GET'])
def get_analisis_abc():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''SELECT material_nombre, SUM(cantidad) as total_qty FROM movimientos
                 WHERE tipo = 'Entrada' GROUP BY material_nombre ORDER BY total_qty DESC''')
    items = c.fetchall()
    conn.close()

    if not items:
        return jsonify({'items': []})

    total = sum(item[1] for item in items)
    cumulative = 0
    abc_items = []

    for material, qty in items:
        cumulative += qty
        percentage = (cumulative / total) * 100

        if percentage <= 80:
            clasificacion = 'A'
        elif percentage <= 95:
            clasificacion = 'B'
        else:
            clasificacion = 'C'

        abc_items.append({
            'material': material,
            'cantidad': qty,
            'valor': f'{percentage:.1f}%',
            'clasificacion': clasificacion
        })

    return jsonify({'items': abc_items})

@app.route('/api/alertas', methods=['GET', 'POST'])
def handle_alertas():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if request.method == 'POST':
        data = request.json
        c.execute('''INSERT INTO alertas (material_id, material_nombre, stock_actual, stock_minimo, fecha, estado)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (data['material_id'], data['material_nombre'], data['stock_actual'],
                   data['stock_minimo'], datetime.now().isoformat(), 'Activa'))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Alerta creada'}), 201

    c.execute('SELECT material_nombre, stock_actual, stock_minimo, estado, fecha FROM alertas ORDER BY fecha DESC')
    alertas = [{'material_nombre': row[0], 'stock_actual': row[1], 'stock_minimo': row[2], 'estado': row[3], 'fecha': row[4]} for row in c.fetchall()]
    conn.close()
    return jsonify({'alertas': alertas})

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
