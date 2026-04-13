#!/bin/bash
# ============================================================================
# SCRIPT DE SETUP - SISTEMA DE INVENTARIOS ÁNIMUS LAB
# ============================================================================
# Uso: bash setup.sh
# Este script instala todas las dependencias y configura el sistema

echo "🚀 SETUP DEL SISTEMA DE INVENTARIOS ÁNIMUS LAB + ESPAGIRIA"
echo "============================================================================"
echo ""

# Verificar Python
echo "[1/5] Verificando Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 no encontrado. Instálalo desde https://www.python.org/"
    exit 1
fi
echo "✅ Python encontrado: $(python3 --version)"
echo ""

# Crear virtual environment (opcional pero recomendado)
echo "[2/5] Creando entorno virtual..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Entorno virtual creado"
else
    echo "✅ Entorno virtual ya existe"
fi

# Activar virtual environment
echo ""
echo "[3/5] Instalando dependencias..."
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    # Windows
    source venv/Scripts/activate
else
    # Linux/Mac
    source venv/bin/activate
fi

pip install --upgrade pip
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ Dependencias instaladas correctamente"
else
    echo "❌ Error instalando dependencias"
    exit 1
fi

# Crear archivo .env
echo ""
echo "[4/5] Configurando variables de entorno..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✅ Archivo .env creado (revísalo y configura tus keys)"
else
    echo "✅ Archivo .env ya existe"
fi

# Verificar directorio de datos
echo ""
echo "[5/5] Verificando archivos de datos..."

# Estos son los paths que la app espera
DATA_DIR="/sessions/youthful-admiring-maxwell/mnt"
MAPEO_PATH="$DATA_DIR/outputs/MAPEO_CODIGOS.json"
INV_PATH="$DATA_DIR/uploads/INVENTARIO REAL MP  (4)-c116478a.xlsx"
FORM_PATH="$DATA_DIR/Inventarios/Formulas Maestras"

if [ -f "$MAPEO_PATH" ] && [ -f "$INV_PATH" ] && [ -d "$FORM_PATH" ]; then
    echo "✅ Archivos de datos encontrados"
    echo "   - MAPEO_CODIGOS.json: ✅"
    echo "   - INVENTARIO REAL: ✅"
    echo "   - Formulas Maestras: ✅"
else
    echo "⚠️  Archivos de datos no encontrados en la ruta esperada"
    echo "   Los datos deben estar en: $DATA_DIR"
    echo "   Asegúrate de que existan o ajusta las rutas en app_profesional.py"
fi

echo ""
echo "============================================================================"
echo "✅ SETUP COMPLETADO EXITOSAMENTE"
echo "============================================================================"
echo ""
echo "📌 PRÓXIMOS PASOS:"
echo ""
echo "1. Abre el archivo .env y configura:"
echo "   - ANTHROPIC_API_KEY (obtén en https://console.anthropic.com/)"
echo "   - (Opcional) EMAIL_REMITENTE y EMAIL_PASSWORD"
echo "   - (Opcional) GOOGLE_CALENDAR_ID"
echo ""
echo "2. Ejecuta la aplicación:"
echo "   python app_profesional.py"
echo ""
echo "3. Abre en tu navegador:"
echo "   http://localhost:5000"
echo ""
echo "============================================================================"
