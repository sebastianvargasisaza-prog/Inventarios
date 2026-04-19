# Auto-extraido de index.py -- Fase A refactor
HOME_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>HHA Group</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Segoe UI',sans-serif;background:#f5f4f2;color:#1C1917;min-height:100vh;}
.hdr{background:#1C1917;color:#fff;padding:18px 28px;display:flex;align-items:center;gap:16px;}
.hdr-logo{font-size:22px;font-weight:900;}
.hdr-sub{font-size:12px;color:#a8a29e;margin-top:2px;}
.hdr-right{margin-left:auto;font-size:12px;color:#78716c;}
.wrap{max-width:960px;margin:40px auto;padding:0 20px;}
.greeting{font-size:24px;font-weight:800;margin-bottom:6px;}
.greeting-sub{font-size:14px;color:#78716c;margin-bottom:32px;}
.sect{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#a8a29e;margin-bottom:12px;}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(175px,1fr));gap:14px;margin-bottom:32px;}
.card{background:#fff;border:1px solid #e7e5e4;border-radius:10px;padding:20px 16px;display:flex;flex-direction:column;align-items:center;gap:7px;text-decoration:none;color:#1C1917;transition:.15s;}
.card:hover{border-color:#a8a29e;box-shadow:0 4px 16px rgba(0,0,0,.08);transform:translateY(-2px);}
.card-icon{font-size:28px;}
.card-name{font-size:13px;font-weight:700;text-align:center;}
.card-desc{font-size:11px;color:#78716c;text-align:center;}
.card.ceo{border-color:#292524;background:#1C1917;color:#fff;}
.card.ceo .card-desc{color:#a8a29e;}
.card.ceo:hover{background:#292524;}
.note{text-align:center;font-size:12px;color:#a8a29e;margin-top:8px;}
.note a{color:#292524;font-weight:600;text-decoration:none;}
</style>
</head>
<body>
<div class="hdr"><div><div class="hdr-logo">HHA Group</div><div class="hdr-sub">Espagiria &middot; ANIMUS Lab</div></div><div class="hdr-right">Sistema de Gestion Interna</div></div>
<div class="wrap">
  <div class="greeting">&#128075; Bienvenido</div>
  <div class="greeting-sub">Selecciona el modulo al que deseas acceder.</div>
  <div class="sect">Produccion &amp; Planta</div>
  <div class="grid">
    <a href="/inventarios" class="card"><div class="card-icon">&#127981;</div><div class="card-name">Planta</div><div class="card-desc">Stock, lotes, trazabilidad</div></a>
    <a href="/recepcion" class="card"><div class="card-icon">&#128666;</div><div class="card-name">Recepcion</div><div class="card-desc">Ingreso de MP y MEE</div></a>
  </div>
  <div class="sect">Comercial &amp; Compras</div>
  <div class="grid">
    <a href="/compras" class="card"><div class="card-icon">&#128722;</div><div class="card-name">Compras</div><div class="card-desc">OC, proveedores, pagos</div></a>
    <a href="/clientes" class="card"><div class="card-icon">&#128101;</div><div class="card-name">Clientes</div><div class="card-desc">Maquila 360 &amp; Aliados</div></a>
  </div>
  <div class="sect">Calidad &amp; Operaciones</div>
  <div class="grid">
    <a href="/calidad" class="card"><div class="card-icon">&#x2705;</div><div class="card-name">Calidad BPM</div><div class="card-desc">CC lotes, NC, calibraciones</div></a>
    <a href="/tecnica" class="card"><div class="card-icon">&#129514;</div><div class="card-name">Tecnica</div><div class="card-desc">Formulas, fichas, INVIMA, SGD</div></a>
  </div>
  <div class="sect">Gerencia</div>
  <div class="grid">
    <a href="/gerencia" class="card ceo"><div class="card-icon">&#127759;</div><div class="card-name">Centro de Comando</div><div class="card-desc">Alertas, KPIs, decisiones</div></a>
    <a href="/gerencia-financiero" class="card ceo"><div class="card-icon">&#128200;</div><div class="card-name">Financiero</div><div class="card-desc">P&amp;L, flujo de caja, WC</div></a>
    <a href="/compromisos" class="card ceo"><div class="card-icon">&#128203;</div><div class="card-name">Compromisos</div><div class="card-desc">Actas y seguimiento</div></a>
    <a href="/rrhh" class="card ceo"><div class="card-icon">&#128101;</div><div class="card-name">RRHH</div><div class="card-desc">Nomina y empleados</div></a>
  </div>
  <div class="note">Los modulos oscuros requieren <a href="/login">iniciar sesion como CEO</a></div>
</div>
</body>
</html>"""