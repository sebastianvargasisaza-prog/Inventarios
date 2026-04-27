"""
comprobante_pago.py - Generador PDF + helpers para Comprobantes de Egreso.

Diseño inspirado en factura electrónica colombiana (formato DIAN-friendly):
  - Logo HHA + datos empresa en encabezado (sin franja negra agresiva)
  - Box derecha con título + número del documento
  - Bloque BENEFICIARIO con datos legales y bancarios
  - Box paralelo con medio de pago + forma + fecha
  - Tabla de items (REFERENCIA, DESCRIPCION, CANT, UM, PRECIO, DESC, VALOR, IVA%, IVA)
  - Caja totales (TOTAL BASE, DESCUENTOS, SUB-TOTAL, IMPUESTOS, RETENCIONES, TOTAL)
  - Cantidad total + Valor en letras
  - Notas legales (régimen, autorización numeración interna)
  - Pie con disclaimer

NO es factura electrónica formal con CUFE/DIAN — es comprobante de egreso
interno (legalmente válido como documento soporte de pago según ETT
art. 1.6.1.4.12 cuando el beneficiario no está obligado a facturar).

Paleta:
  Primario: #1F5F5B (HHA Group teal)
  Texto:    #1F2937
  Líneas:   #D6D3D1
  Beige:    #F7F4EF
"""
import os
from datetime import datetime
from pathlib import Path

# ── Paleta HHA Group ─────────────────────────────────────────────────────────
HHA_TEAL = (31, 95, 91)        # #1F5F5B (color principal del logo HHA)
HHA_TEAL_DARK = (15, 60, 56)
COLOR_TEXT = (31, 41, 55)       # gris oscuro casi negro (legibilidad)
COLOR_TEXT_SOFT = (107, 114, 128)
COLOR_LINE = (214, 211, 209)
COLOR_LINE_DARK = (120, 113, 108)
COLOR_BEIGE = (247, 244, 239)
COLOR_BLANCO = (255, 255, 255)
COLOR_NEGRO = (0, 0, 0)

# ── Paleta ÁNIMUS Lab (extraída del manual de identidad v1) ─────────────────
ANIMUS_BLACK = (0, 0, 0)
ANIMUS_BLACK_DARK = (20, 20, 20)
ANIMUS_CREAM = (247, 244, 239)
ANIMUS_OLIVA = (155, 153, 123)
ANIMUS_TERRACOTA = (224, 186, 168)


def _palette(empresa_clave):
    """Devuelve la paleta de colores según la marca pagadora.

    Animus = negro + cream (manual de identidad v1).
    Espagiria / HHA = teal (color del logo HHA Group).
    """
    if "animus" in (empresa_clave or "").lower():
        return {
            "primary":      ANIMUS_BLACK,
            "primary_dark": ANIMUS_BLACK_DARK,
            "accent":       ANIMUS_OLIVA,
            "beige":        ANIMUS_CREAM,
        }
    return {
        "primary":      HHA_TEAL,
        "primary_dark": HHA_TEAL_DARK,
        "accent":       HHA_TEAL,
        "beige":        COLOR_BEIGE,
    }

# ── Datos empresas pagadoras del grupo HHA ───────────────────────────────────
# Cada categoría de pago dispatcha a la empresa correcta:
#   Influencers / Marketing / Cuenta de Cobro → ANIMUS LAB S.A.S.
#   Mercancía / MPs / Servicios planta / etc. → ESPAGIRIA LABORATORIO S.A.S.
EMPRESAS_PAGADORAS = {
    "espagiria": {
        "razon_social": "ESPAGIRIA LABORATORIO S.A.S.",
        "nombre_corto": "Espagiria",
        "nit": "901622676-0",
        "direccion": "Cra 1 # 32 46 P 2",
        "ciudad": "Cali, Valle del Cauca, Colombia",
        "telefono": "305 3427171",
        "email": "facturasespagirialaboratorio@gmail.com",
        "regimen": "Responsable del impuesto sobre las ventas IVA",
        "actividad_economica": "2100 - Fabricación de productos farmacéuticos y cosméticos",
        "tarifa_ica": "6.6 x 1000 en Cali",
    },
    "animus": {
        "razon_social": "ANIMUS LAB S.A.S.",
        "nombre_corto": "ANIMUS Lab",
        "nit": "901962051-1",
        "direccion": "Cra 1 # 32 46 P 2",
        "ciudad": "Cali, Valle del Cauca, Colombia",
        "telefono": "305 3427171",
        "email": "facturasespagirialaboratorio@gmail.com",
        "regimen": "Responsable del impuesto sobre las ventas IVA",
        "actividad_economica": "4645 - Comercio al por mayor de productos farmacéuticos, medicinales, cosméticos y de tocador",
        # ICA Cali para CIIU 4645 (comercio al por mayor): tarifa estándar
        # 6.6 x 1000. Verificar con contadora si el RUT trae otra tarifa.
        "tarifa_ica": "6.6 x 1000 en Cali",
    },
}

# Compat: alias del dict viejo, apunta a Espagiria (default histórico)
EMPRESA_PAGADORA = EMPRESAS_PAGADORAS["espagiria"]


def _empresa(empresa_clave):
    """Devuelve el dict de la empresa pagadora correspondiente.

    Acepta variaciones case-insensitive: 'animus', 'ANIMUS', 'Animus Lab',
    'espagiria', 'Espagiria', etc. Si no reconoce, cae a Espagiria.
    """
    k = (empresa_clave or "espagiria").strip().lower()
    if "animus" in k:
        return EMPRESAS_PAGADORAS["animus"]
    return EMPRESAS_PAGADORAS["espagiria"]


def _safe(text):
    """fpdf2 latin-1 compatible (filtra emojis y chars no soportados)."""
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
    repl = {
        "—": "-", "–": "-", "…": "...", "“": '"', "”": '"',
        "‘": "'", "’": "'", "•": "·", "→": "->",
    }
    for k, v in repl.items():
        text = text.replace(k, v)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _numero_a_letras(n):
    """Convierte un número entero (COP) a letras en español."""
    n = int(round(float(n)))
    if n == 0:
        return "CERO PESOS M/CTE"

    UNIDADES = ["", "UNO", "DOS", "TRES", "CUATRO", "CINCO", "SEIS", "SIETE", "OCHO", "NUEVE",
                "DIEZ", "ONCE", "DOCE", "TRECE", "CATORCE", "QUINCE", "DIECISEIS",
                "DIECISIETE", "DIECIOCHO", "DIECINUEVE",
                "VEINTE", "VEINTIUNO", "VEINTIDOS", "VEINTITRES", "VEINTICUATRO",
                "VEINTICINCO", "VEINTISEIS", "VEINTISIETE", "VEINTIOCHO", "VEINTINUEVE"]
    DECENAS = ["", "", "", "TREINTA", "CUARENTA", "CINCUENTA", "SESENTA", "SETENTA",
               "OCHENTA", "NOVENTA"]
    CENTENAS = ["", "CIENTO", "DOSCIENTOS", "TRESCIENTOS", "CUATROCIENTOS",
                "QUINIENTOS", "SEISCIENTOS", "SETECIENTOS", "OCHOCIENTOS", "NOVECIENTOS"]

    def cien(c):
        if c == 0: return ""
        if c == 100: return "CIEN"
        if c < 30: return UNIDADES[c]
        if c < 100:
            d, u = c // 10, c % 10
            return DECENAS[d] + (" Y " + UNIDADES[u] if u else "")
        ce, r = c // 100, c % 100
        return CENTENAS[ce] + (" " + cien(r) if r else "")

    def mil(m):
        if m == 0: return ""
        if m == 1: return "MIL"
        return cien(m) + " MIL"

    millones = n // 1_000_000
    miles = (n % 1_000_000) // 1000
    resto = n % 1000

    parts = []
    if millones:
        if millones == 1:
            parts.append("UN MILLON")
        else:
            parts.append(cien(millones) + " MILLONES")
    if miles:
        parts.append(mil(miles))
    if resto:
        parts.append(cien(resto))
    return " ".join(parts) + " PESOS M/CTE"


def parse_obs_beneficiario(obs_str):
    """Extrae datos de beneficiario desde el string OBS estructurado.

    Formato esperado (generado por marketing.py al crear SOLs de influencer):
      BENEFICIARIO: {nombre} | BANCO: {banco} {tipo} | CUENTA/CEL: {cuenta} |
      CED/NIT: {cedula} | CONCEPTO: {x} | VALOR: ${x}

    Devuelve dict con las claves del beneficiario, todas pueden ser "".
    """
    result = {"nombre": "", "banco": "", "tipo_cuenta": "", "cuenta": "",
              "cedula": "", "email": "", "ciudad": ""}
    if not obs_str:
        return result
    for part in obs_str.split("|"):
        part = part.strip()
        if part.upper().startswith("BENEFICIARIO:"):
            result["nombre"] = part.split(":", 1)[1].strip()
        elif part.upper().startswith("BANCO:"):
            banco_raw = part.split(":", 1)[1].strip()
            # "Bancolombia Ahorros" → banco="Bancolombia", tipo_cuenta="Ahorros"
            tokens = banco_raw.split()
            if len(tokens) >= 2:
                result["banco"] = " ".join(tokens[:-1])
                result["tipo_cuenta"] = tokens[-1]
            else:
                result["banco"] = banco_raw
        elif part.upper().startswith("CUENTA/CEL:"):
            result["cuenta"] = part.split(":", 1)[1].strip()
        elif part.upper().startswith("CED/NIT:"):
            result["cedula"] = part.split(":", 1)[1].strip()
    return result


def _logo_path(empresa_clave="hha"):
    """Devuelve path del logo si existe, o None si no.

    Busca en orden de especificidad. Para Animus NO cae al de HHA — preferimos
    fallback de texto branded (negro/cream) que es visualmente más coherente
    con la marca que usar el logo de HHA en un comprobante de Animus.
    """
    base = Path(__file__).parent / "static"
    k = (empresa_clave or "").lower()
    if "animus" in k:
        candidates = [base / "logos" / "animus_lab.png",
                      base / "logos" / "animus.png"]
    elif "espagiria" in k:
        candidates = [base / "logos" / "espagiria.png",
                      base / "logos" / "hha_group.png",
                      base / "logo_hha.png"]
    else:
        candidates = [base / "logos" / "hha_group.png",
                      base / "logo_hha.png"]
    for p in candidates:
        if p.exists():
            return str(p)
    return None


def _render_logo_or_text(pdf, x, y, w, h, empresa_clave):
    """Dibuja el logo de la empresa, o un placeholder branded si el PNG falta.

    Para Animus: cuadro cream con texto 'ANIMUS LAB' en negro grueso —
    coherente con el manual de identidad (negro + crema). Para Espagiria/HHA:
    cuadro con texto teal. Esto evita que un comprobante de Animus muestre
    el logo de HHA cuando el archivo aún no se subió a static/logos/.
    """
    logo_p = _logo_path(empresa_clave)
    if logo_p:
        try:
            pdf.image(logo_p, x=x, y=y, w=w, h=h)
            return
        except Exception:
            pass

    k = (empresa_clave or "").lower()
    if "animus" in k:
        pdf.set_fill_color(*ANIMUS_CREAM)
        pdf.set_draw_color(*ANIMUS_BLACK)
        pdf.set_line_width(0.6)
        pdf.rect(x, y, w, h, "DF")
        pdf.set_xy(x, y + h / 2 - 5)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*ANIMUS_BLACK)
        pdf.cell(w, 5, "ANIMUS", align="C", ln=True)
        pdf.set_x(x)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*ANIMUS_OLIVA)
        pdf.cell(w, 4, "L A B", align="C")
    else:
        pdf.set_fill_color(*COLOR_BEIGE)
        pdf.set_draw_color(*HHA_TEAL)
        pdf.set_line_width(0.5)
        pdf.rect(x, y, w, h, "DF")
        pdf.set_xy(x, y + h / 2 - 4)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*HHA_TEAL)
        pdf.cell(w, 5, "HHA", align="C", ln=True)
        pdf.set_x(x)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*HHA_TEAL_DARK)
        pdf.cell(w, 4, "GROUP", align="C")


def generar_comprobante_egreso_pdf(
    numero_ce,
    fecha_pago,
    beneficiario,
    items,
    aplicar_retefuente=False,
    aplicar_retica=False,
    aplicar_iva=False,
    medio_pago="Transferencia",
    observaciones="",
    pagado_por="",
    empresa_clave="espagiria",
):
    """Genera bytes PDF de un Comprobante de Egreso (estilo factura formal).

    Args:
        numero_ce: "CE-2026-0042" — único, secuencial
        fecha_pago: datetime
        beneficiario: dict con: nombre, cedula, banco, cuenta,
                      tipo_cuenta, ciudad, email, telefono, direccion
        items: lista de dicts con: descripcion, fecha, cantidad, valor_unit,
               (opcionales: referencia, um, descuento)
        aplicar_retefuente: 10% sobre subtotal
        aplicar_retica: 0.66/1000 (Cali default)
        aplicar_iva: 19% sobre subtotal
        medio_pago: "Transferencia" | "Nequi" | "Cheque" | etc.
        observaciones: texto libre
        pagado_por: usuario que registró el pago

    Returns:
        bytes PDF
    """
    from fpdf import FPDF

    if isinstance(fecha_pago, str):
        try:
            fecha_pago = datetime.fromisoformat(fecha_pago.replace("Z", ""))
        except (ValueError, TypeError):
            fecha_pago = datetime.now()
    if fecha_pago is None:
        fecha_pago = datetime.now()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    W = pdf.w - 20  # ancho útil

    emp = _empresa(empresa_clave)
    pal = _palette(empresa_clave)

    # ════════════════════════════════════════════════════════════════════
    # ENCABEZADO: Logo izquierda + Datos empresa centro + Box documento derecha
    # ════════════════════════════════════════════════════════════════════
    HEAD_Y = 12
    HEAD_H = 38

    # Logo izquierda — usa el logo correcto de la marca, o fallback texto
    # branded si el PNG no existe (no muestra HHA en comprobantes Animus).
    _render_logo_or_text(pdf, x=12, y=HEAD_Y, w=32, h=32,
                         empresa_clave=empresa_clave)

    # Datos empresa centro
    pdf.set_xy(50, HEAD_Y + 1)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*pal["primary"])
    pdf.cell(95, 6, _safe(emp["razon_social"]), ln=True)

    pdf.set_x(50)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*COLOR_TEXT)
    pdf.cell(95, 4, _safe(f"NIT: {emp['nit']}"), ln=True)
    pdf.set_x(50)
    pdf.cell(95, 4, _safe(emp["direccion"] + " - " + emp["ciudad"]), ln=True)
    pdf.set_x(50)
    pdf.cell(95, 4, _safe("Tel: " + emp["telefono"]), ln=True)
    pdf.set_x(50)
    pdf.cell(95, 4, _safe(emp["email"]), ln=True)
    pdf.set_x(50)
    pdf.set_font("Helvetica", "I", 7)
    pdf.set_text_color(*COLOR_TEXT_SOFT)
    pdf.cell(95, 4, _safe(emp["regimen"]), ln=True)

    # Box documento derecha (estilo factura)
    box_x, box_y = 148, HEAD_Y
    box_w, box_h = 50, 30
    pdf.set_draw_color(*pal["primary"])
    pdf.set_line_width(0.5)
    pdf.rect(box_x, box_y, box_w, box_h)

    # Banda superior del box
    pdf.set_fill_color(*pal["primary"])
    pdf.rect(box_x, box_y, box_w, 8, "F")
    pdf.set_xy(box_x, box_y + 1.5)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*COLOR_BLANCO)
    pdf.cell(box_w, 5, "COMPROBANTE DE EGRESO", align="C")

    # Contenido del box
    pdf.set_xy(box_x + 2, box_y + 10)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(*COLOR_TEXT_SOFT)
    pdf.cell(15, 4, "No.")
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*pal["primary_dark"])
    pdf.cell(0, 4, _safe(numero_ce), ln=True)

    pdf.set_x(box_x + 2)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(*COLOR_TEXT_SOFT)
    pdf.cell(15, 4, "Fecha:")
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(*COLOR_TEXT)
    pdf.cell(0, 4, _safe(fecha_pago.strftime("%Y/%m/%d")), ln=True)

    pdf.set_x(box_x + 2)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(*COLOR_TEXT_SOFT)
    pdf.cell(15, 4, "Hora:")
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(*COLOR_TEXT)
    pdf.cell(0, 4, _safe(fecha_pago.strftime("%H:%M")), ln=True)

    pdf.set_x(box_x + 2)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(*COLOR_TEXT_SOFT)
    pdf.cell(15, 4, "Pagina:")
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(*COLOR_TEXT)
    pdf.cell(0, 4, "1 de 1", ln=True)

    pdf.set_y(HEAD_Y + HEAD_H + 4)

    # ════════════════════════════════════════════════════════════════════
    # BENEFICIARIO + MEDIO DE PAGO (dos columnas como factura)
    # ════════════════════════════════════════════════════════════════════
    BENEF_Y = pdf.get_y()
    BENEF_H = 36

    # Columna izquierda: BENEFICIARIO
    pdf.set_draw_color(*COLOR_LINE_DARK)
    pdf.set_line_width(0.3)
    pdf.rect(10, BENEF_Y, 115, BENEF_H)

    pdf.set_xy(11, BENEF_Y + 1)
    pdf.set_font("Helvetica", "B", 7.5)
    pdf.set_text_color(*COLOR_TEXT_SOFT)
    pdf.cell(0, 4, "BENEFICIARIO", ln=True)

    def _kv(label, value, x, y, w_label=22):
        pdf.set_xy(x, y)
        pdf.set_font("Helvetica", "B", 7.5)
        pdf.set_text_color(*COLOR_TEXT_SOFT)
        pdf.cell(w_label, 4.5, _safe(label.upper()))
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*COLOR_TEXT)
        pdf.cell(0, 4.5, _safe(value), ln=True)

    y = BENEF_Y + 6
    _kv("Nombre", beneficiario.get("nombre", ""), 11, y); y += 4.5
    _kv("CC/NIT", beneficiario.get("cedula", ""), 11, y); y += 4.5
    _kv("Banco", beneficiario.get("banco", "") + " - " + beneficiario.get("tipo_cuenta", ""), 11, y); y += 4.5
    _kv("Cuenta", beneficiario.get("cuenta", ""), 11, y); y += 4.5
    _kv("Ciudad", beneficiario.get("ciudad", ""), 11, y); y += 4.5
    _kv("Correo", beneficiario.get("email", "") or "(no registrado)", 11, y)

    # Columna derecha: MEDIO/FORMA DE PAGO
    pdf.rect(127, BENEF_Y, 73, BENEF_H)

    pdf.set_xy(128, BENEF_Y + 1)
    pdf.set_font("Helvetica", "B", 7.5)
    pdf.set_text_color(*COLOR_TEXT_SOFT)
    pdf.cell(0, 4, "MEDIO DE PAGO", ln=True)

    y = BENEF_Y + 6
    _kv("Medio", medio_pago, 128, y, w_label=22); y += 4.5
    _kv("Forma", "Contado", 128, y, w_label=22); y += 4.5
    # "Pagado por" debe mostrar la EMPRESA emisora (Espagiria o ANIMUS Lab),
    # no la persona que registró el pago. La persona aparece como EMISOR
    # en el bloque de firmas al final del documento.
    _kv("Pagado por", emp["nombre_corto"], 128, y, w_label=22); y += 4.5
    _kv("Moneda", "PESOS COL", 128, y, w_label=22); y += 4.5
    _kv("NIT pagador", emp["nit"], 128, y, w_label=22)

    pdf.set_y(BENEF_Y + BENEF_H + 4)

    # ════════════════════════════════════════════════════════════════════
    # TABLA DE ITEMS (estilo factura formal)
    # ════════════════════════════════════════════════════════════════════
    # Columnas: REF (25), DESCRIPCION (78), CANT (12), UM (10), P.UNIT (22),
    #           DESC (15), VALOR (22), IVA% (8), IVA (18) = 210 mm? — ajusto
    # Real W: 190. Reasigno: 24, 60, 12, 10, 22, 14, 22, 8, 18 = 190
    cols = [(24, "REFERENCIA", "L"), (60, "DESCRIPCION", "L"),
            (12, "CANT", "C"), (10, "UM", "C"),
            (22, "PRECIO UNIT", "R"), (14, "DESCUENTO", "R"),
            (22, "VALOR TOTAL", "R"), (8, "IVA%", "C"), (18, "IVA", "R")]

    pdf.set_fill_color(*pal["primary"])
    pdf.set_text_color(*COLOR_BLANCO)
    pdf.set_font("Helvetica", "B", 7)
    for w, name, _ in cols:
        pdf.cell(w, 6, _safe(name), border=0, fill=True, align="C")
    pdf.ln()

    pdf.set_text_color(*COLOR_TEXT)
    pdf.set_font("Helvetica", "", 7.5)
    subtotal = 0.0
    cantidad_total = 0
    iva_pct_global = 19 if aplicar_iva else 0
    for i, it in enumerate(items):
        ref = it.get("referencia", "")
        desc = it.get("descripcion", "")
        cant = it.get("cantidad", 1) or 1
        # Si cantidad llega 0 (caso típico de servicios donde solo hay valor),
        # forzar 1 para que el VALOR_TOTAL del renglón coincida con valor_unit.
        if cant == 0:
            cant = 1
        um = it.get("um", "UND")
        p_unit = float(it.get("valor_unit", 0) or 0)
        descuento = float(it.get("descuento", 0) or 0)
        valor_total_item = (p_unit * cant) - descuento
        iva_item = round(valor_total_item * iva_pct_global / 100, 2) if aplicar_iva else 0
        subtotal += valor_total_item
        cantidad_total += cant

        # Alternar fill suave
        if i % 2 == 0:
            pdf.set_fill_color(*pal["beige"])
            fill = True
        else:
            pdf.set_fill_color(*COLOR_BLANCO)
            fill = False

        vals = [
            (cols[0][0], _safe(ref[:18] or "-"), "L"),
            (cols[1][0], _safe(desc[:48]), "L"),
            (cols[2][0], f"{cant:,.0f}" if isinstance(cant, (int, float)) else str(cant), "C"),
            (cols[3][0], _safe(um), "C"),
            (cols[4][0], _safe(f"${p_unit:,.0f}"), "R"),
            (cols[5][0], _safe(f"${descuento:,.0f}"), "R"),
            (cols[6][0], _safe(f"${valor_total_item:,.0f}"), "R"),
            (cols[7][0], f"{iva_pct_global}%" if aplicar_iva else "-", "C"),
            (cols[8][0], _safe(f"${iva_item:,.0f}") if aplicar_iva else "-", "R"),
        ]
        for w, v, align in vals:
            pdf.cell(w, 5.5, v, border=0, fill=fill, align=align)
        pdf.ln()

    # Línea separadora
    pdf.set_draw_color(*COLOR_LINE_DARK)
    pdf.set_line_width(0.3)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())

    # Cantidad total — en línea propia, alineada a la derecha, con espacio
    # claro respecto a la caja de totales que viene después. Antes se
    # superponía con los headers de la tabla de totales.
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*COLOR_TEXT)
    pdf.cell(0, 5, _safe(f"Cantidad Total: {cantidad_total:,.0f}"), align="R", ln=True)
    pdf.ln(3)

    # ════════════════════════════════════════════════════════════════════
    # CAJA DE TOTALES (estilo factura formal)
    # ════════════════════════════════════════════════════════════════════
    iva_total = round(subtotal * iva_pct_global / 100, 2) if aplicar_iva else 0
    rete_fuente_pct = 10 if aplicar_retefuente else 0
    rete_fuente = round(subtotal * rete_fuente_pct / 100, 2) if aplicar_retefuente else 0
    rete_ica_pct = 0.66 if aplicar_retica else 0
    rete_ica = round(subtotal * rete_ica_pct / 1000, 2) if aplicar_retica else 0
    retenciones = rete_fuente + rete_ica
    total = subtotal + iva_total - retenciones

    # 6 columnas: TOTAL BASE | DESCUENTOS | SUB-TOTAL | IMPUESTOS | RETENCIONES | TOTAL
    box_y = pdf.get_y()
    pdf.set_draw_color(*pal["primary"])
    pdf.set_line_width(0.4)
    pdf.rect(10, box_y, 190, 14, "D")
    cw = 190 / 6

    pdf.set_xy(10, box_y + 1)
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_text_color(*COLOR_TEXT_SOFT)
    headers = ["TOTAL BASE", "DESCUENTOS", "SUB-TOTAL", "IMPUESTOS", "RETENCIONES", "TOTAL"]
    for h in headers:
        pdf.cell(cw, 5, _safe(h), align="C")
    pdf.ln(5)

    pdf.set_x(10)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*COLOR_TEXT)
    vals = [
        f"${subtotal:,.0f}",
        f"${0:,.0f}",
        f"${subtotal:,.0f}",
        f"${iva_total:,.0f}",
        f"${retenciones:,.0f}",
        f"${total:,.0f}",
    ]
    for i, v in enumerate(vals):
        if i == 5:
            pdf.set_text_color(*pal["primary_dark"])
            pdf.set_font("Helvetica", "B", 10)
        pdf.cell(cw, 7, _safe(v), align="C")
    pdf.ln(8)

    # ════════════════════════════════════════════════════════════════════
    # VALOR EN LETRAS + NOTAS LEGALES
    # ════════════════════════════════════════════════════════════════════
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*COLOR_TEXT)
    pdf.cell(28, 5, "Valor en letras:")
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*COLOR_TEXT_SOFT)
    pdf.multi_cell(W - 28, 5, _safe(_numero_a_letras(total) + " *******"))

    pdf.ln(1)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*COLOR_TEXT)
    pdf.cell(0, 5, "Notas:", ln=True)
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(*COLOR_TEXT_SOFT)
    notas = []
    if observaciones:
        notas.append(observaciones)
    # Texto legal alineado con DIAN Resolución 000167 de 2021 + Decreto
    # 1625 de 2016 art. 1.6.1.4.12. Este documento es el "Documento Soporte
    # en adquisiciones efectuadas a no obligados a facturar" — instrumento
    # válido para soportar costos/deducciones cuando el proveedor no expide
    # factura electrónica. Debe contener: denominación, numeración
    # consecutiva, fecha, datos completos de adquirente y proveedor,
    # descripción, valor, discriminación de IVA si aplica.
    notas.append(
        "DOCUMENTO SOPORTE DE PAGO en adquisiciones efectuadas a sujetos no "
        "obligados a expedir factura de venta o documento equivalente. "
        "Expedido conforme a la Resolucion DIAN 000167 de 2021 y al Decreto "
        "1625 de 2016 (E.T.R.) art. 1.6.1.4.12. NO constituye factura "
        "electronica de venta."
    )
    notas.append(
        f"ADQUIRENTE: {emp['razon_social']} - NIT {emp['nit']} - "
        f"Actividad economica CIIU {emp['actividad_economica']}. "
        f"Tarifa ICA {emp['tarifa_ica']}. "
        f"Numeracion interna autorizada: rango CE-{datetime.now().year}-0001 "
        f"a CE-{datetime.now().year}-9999."
    )
    notas.append(
        f"El beneficiario declara haber recibido a satisfaccion el valor "
        f"relacionado en este documento por los conceptos descritos. "
        f"Para cualquier observacion sobre este comprobante, contactar el "
        f"area administrativa de {emp['nombre_corto']} al correo "
        f"{emp['email']}."
    )
    for n in notas:
        pdf.multi_cell(W, 4, _safe(n))
        pdf.ln(0.5)

    # ════════════════════════════════════════════════════════════════════
    # AUTORIZACION NUMERACION INTERNA + FIRMAS
    # ════════════════════════════════════════════════════════════════════
    # Espacio reservado a las firmas — fixed Y para que no se mueva con notas.
    # Dos firmas: EMISOR (representante legal de la empresa que paga) y
    # BENEFICIARIO (quien recibe el pago). El usuario que registró la
    # operación (pagado_por) queda solo como auditoría interna abajo.
    pdf.set_y(-40)
    pdf.set_draw_color(*COLOR_LINE_DARK)
    pdf.set_line_width(0.2)
    y = pdf.get_y()
    pdf.line(20, y, 90, y)
    pdf.line(120, y, 190, y)
    pdf.set_xy(20, y + 1)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*COLOR_TEXT)
    pdf.cell(70, 4, "EMISOR", align="C", ln=True)
    pdf.set_x(20)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(*COLOR_TEXT_SOFT)
    pdf.cell(70, 3.5, _safe(emp["razon_social"]), align="C")

    pdf.set_xy(120, y + 1)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*COLOR_TEXT)
    pdf.cell(70, 4, "BENEFICIARIO", align="C", ln=True)
    pdf.set_x(120)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(*COLOR_TEXT_SOFT)
    pdf.cell(70, 3.5, _safe(beneficiario.get("nombre", "") + (" - CC " + beneficiario["cedula"] if beneficiario.get("cedula") else "")), align="C")

    # Numeracion interna + autorizacion
    pdf.set_y(-22)
    pdf.set_font("Helvetica", "", 6.5)
    pdf.set_text_color(*COLOR_TEXT_SOFT)
    _anio = fecha_pago.year
    pdf.cell(0, 3,
             _safe(f"Autorizacion numeracion interna: rango CE-{_anio}-0001 "
                   f"hasta CE-{_anio}-9999. "
                   f"Vigencia: {_anio}/01/01 - {_anio}/12/31."),
             align="C", ln=True)

    # Footer: usa el branding correcto según la empresa que firma
    pdf.set_font("Helvetica", "I", 6)
    if "animus" in (empresa_clave or "").lower():
        footer_txt = ("Documento generado el " +
                      datetime.now().strftime("%Y/%m/%d %H:%M") +
                      " - ANIMUS Lab S.A.S. (HHA Group)")
    else:
        footer_txt = ("Documento generado el " +
                      datetime.now().strftime("%Y/%m/%d %H:%M") +
                      " - HHA Group: Transformamos ciencia en cuidado - "
                      "by ANIMUS x Espagiria")
    pdf.cell(0, 3, _safe(footer_txt), align="C")

    # Output bytes
    out = pdf.output()
    return bytes(out) if isinstance(out, bytearray) else out


# ─── Helpers de persistencia ─────────────────────────────────────────────────


def reservar_numero_ce(conn, anio=None):
    """Reserva atómicamente el siguiente CE-YYYY-NNNN."""
    from datetime import datetime as _dt
    if anio is None:
        anio = _dt.now().year
    c = conn.cursor()
    c.execute("""
        INSERT INTO comprobantes_seq (anio, ultimo) VALUES (?, 1)
        ON CONFLICT(anio) DO UPDATE SET ultimo = ultimo + 1
    """, (anio,))
    c.execute("SELECT ultimo FROM comprobantes_seq WHERE anio=?", (anio,))
    row = c.fetchone()
    n = row[0] if row else 1
    return f"CE-{anio}-{n:04d}"


def crear_comprobante_y_pdf(
    conn, beneficiario, items, monto_subtotal,
    aplicar_retefuente=False, aplicar_retica=False, aplicar_iva=False,
    medio_pago="Transferencia", observaciones="",
    pagado_por="", numero_oc="", pago_oc_id=None,
    empresa="Espagiria",
):
    """Reserva número CE, genera PDF, persiste en comprobantes_pago."""
    from datetime import datetime as _dt
    import base64

    fecha_pago = _dt.now()
    numero_ce = reservar_numero_ce(conn, anio=fecha_pago.year)

    iva = round(monto_subtotal * 0.19, 2) if aplicar_iva else 0
    retefuente = round(monto_subtotal * 0.10, 2) if aplicar_retefuente else 0
    retica = round(monto_subtotal * 0.00066, 2) if aplicar_retica else 0
    total_pagado = round(monto_subtotal + iva - retefuente - retica, 2)

    pdf_bytes = generar_comprobante_egreso_pdf(
        numero_ce=numero_ce, fecha_pago=fecha_pago,
        beneficiario=beneficiario, items=items,
        aplicar_retefuente=aplicar_retefuente,
        aplicar_retica=aplicar_retica,
        aplicar_iva=aplicar_iva,
        medio_pago=medio_pago, observaciones=observaciones,
        pagado_por=pagado_por,
        empresa_clave=empresa.lower() if empresa else "espagiria",
    )
    pdf_b64 = base64.b64encode(pdf_bytes).decode("ascii")

    c = conn.cursor()
    c.execute("""
        INSERT INTO comprobantes_pago (
            numero_ce, anio, pago_oc_id, numero_oc,
            beneficiario_nombre, beneficiario_cedula, beneficiario_banco,
            beneficiario_cuenta, beneficiario_tipo_cta, beneficiario_ciudad,
            subtotal, iva, iva_pct, retefuente, retefuente_pct,
            retica, retica_pct, total_pagado,
            medio_pago, observaciones, pagado_por, empresa, pdf_archivo
        ) VALUES (?, ?, ?, ?,  ?, ?, ?, ?, ?, ?,  ?, ?, ?, ?, ?, ?, ?, ?,  ?, ?, ?, ?, ?)
    """, (
        numero_ce, fecha_pago.year, pago_oc_id, numero_oc,
        beneficiario.get("nombre", ""), beneficiario.get("cedula", ""),
        beneficiario.get("banco", ""), beneficiario.get("cuenta", ""),
        beneficiario.get("tipo_cuenta", ""), beneficiario.get("ciudad", ""),
        monto_subtotal, iva, 19 if aplicar_iva else 0,
        retefuente, 10 if aplicar_retefuente else 0,
        retica, 0.66 if aplicar_retica else 0,
        total_pagado,
        medio_pago, observaciones, pagado_por, empresa, pdf_b64,
    ))
    comprobante_id = c.lastrowid
    return {
        "numero_ce": numero_ce,
        "comprobante_id": comprobante_id,
        "pdf_bytes": pdf_bytes,
        "subtotal": monto_subtotal,
        "iva": iva,
        "retefuente": retefuente,
        "retica": retica,
        "total_pagado": total_pagado,
    }
