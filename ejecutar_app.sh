#!/bin/bash

# ========================================================
# ÁNIMUS Lab + Espagiria - Sistema de Inventarios
# Script para ejecutar la aplicación (macOS/Linux)
# ========================================================

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║    ÁNIMUS Lab + Espagiria Laboratorio                 ║"
echo "║    Sistema Integrado de Gestión de Inventarios        ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# Verificar que Python esté instalado
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 no está instalado"
    echo ""
    echo "Instala Python desde: https://www.python.org/downloads/"
    exit 1
fi

# Verificar que Flask esté instalado
if ! python3 -c "import flask" 2>/dev/null; then
    echo ""
    echo "⚠️  Flask no está instalado. Instalando..."
    echo ""
    pip3 install flask
    echo ""
fi

echo ""
echo "✅ Iniciando aplicación..."
echo ""
echo "📊 Accede a: http://localhost:5000"
echo "🔌 API:      http://localhost:5000/api/*"
echo ""
echo "Presiona CTRL+C para detener el servidor"
echo ""

# Ejecutar la app
python3 inventario_app.py
