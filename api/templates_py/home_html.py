# Auto-extraido de index.py -- Fase A refactor
HOME_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Cortex Labs · Portal HHA Group</title>
<meta name="application-name" content="Cortex Labs">
<meta name="apple-mobile-web-app-title" content="Cortex Labs">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="mobile-web-app-capable" content="yes">
<meta name="theme-color" content="#6d28d9">
<meta name="description" content="Cortex Labs · El cerebro operativo de tu laboratorio · Desarrollado por HHA Group">
<meta name="author" content="HHA Group">
<link rel="manifest" href="/manifest.json">
<link rel="apple-touch-icon" href="/static/icons/icon-192.png">
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
<div class="hdr">
  <div>
    <div class="hdr-logo" style="display:flex;align-items:baseline;gap:10px;">
      <span style="background:linear-gradient(135deg,#a78bfa,#6d28d9);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">Cortex Labs</span>
      <span style="font-size:10px;color:#a78bfa;font-weight:700;letter-spacing:1.2px;text-transform:uppercase;border:1px solid #6d28d9;padding:2px 7px;border-radius:4px;">v1.0</span>
    </div>
    <div class="hdr-sub">by <strong style="color:#fff">HHA Group</strong> &middot; Espagiria &middot; ANIMUS Lab</div>
  </div>
  <div class="hdr-right">
    <div style="font-style:italic;color:#cbd5e1;">El cerebro operativo de tu laboratorio</div>
    <div style="font-size:10px;color:#78716c;margin-top:2px;letter-spacing:1px;text-transform:uppercase;">Desarrollado por HHA Group</div>
  </div>
</div>
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
    <a href="/solicitudes" class="card"><div class="card-icon">&#x1F4CB;</div><div class="card-name">Solicitudes</div><div class="card-desc">Pedir materiales e insumos</div></a>
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
<footer style="padding:24px 20px;border-top:1px solid #e7e5e4;margin-top:40px;text-align:center;font-size:11px;color:#a8a29e;background:#fafaf9;">
  <div style="font-weight:700;color:#6d28d9;letter-spacing:0.3px;font-size:13px;">Cortex Labs</div>
  <div style="margin-top:4px;font-style:italic;">El cerebro operativo de tu laboratorio</div>
  <div style="margin-top:10px;letter-spacing:1px;text-transform:uppercase;">Desarrollado por <strong style="color:#1c1917">HHA Group</strong></div>
  <div style="margin-top:6px;color:#d6d3d1;">&copy; 2026 HHA Group S.A.S. &middot; Todos los derechos reservados</div>
</footer>
</body>
</html>"""