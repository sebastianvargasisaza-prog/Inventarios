MODULOS_HTML = """<\!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>HHA Group — Módulos</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Segoe UI',sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh;}
.header{background:#1e293b;border-bottom:1px solid #334155;padding:16px 24px;display:flex;align-items:center;justify-content:space-between;}
.header-logo{font-size:18px;font-weight:800;color:#fff;}
.header-sub{font-size:12px;color:#94a3b8;margin-top:2px;}
.header-user{font-size:12px;color:#94a3b8;}
.header-user strong{color:#e2e8f0;}
.main{padding:32px 24px;max-width:960px;margin:0 auto;}
.title{font-size:22px;font-weight:700;color:#f1f5f9;margin-bottom:6px;}
.subtitle{font-size:13px;color:#64748b;margin-bottom:28px;}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:14px;}
.mod-card{display:flex;flex-direction:column;align-items:center;gap:8px;padding:22px 12px 18px;background:#1e293b;border:1px solid #334155;border-radius:12px;text-decoration:none;color:#e2e8f0;transition:.15s;cursor:pointer;}
.mod-card:hover{background:#263348;border-color:#475569;transform:translateY(-2px);}
.mod-icon{font-size:30px;line-height:1;}
.mod-name{font-size:13px;font-weight:600;text-align:center;}
.footer{margin-top:40px;text-align:center;}
.logout-btn{display:inline-flex;align-items:center;gap:6px;padding:8px 20px;background:transparent;border:1px solid #334155;border-radius:8px;color:#64748b;text-decoration:none;font-size:12px;font-weight:600;transition:.15s;}
.logout-btn:hover{border-color:#7f1d1d;color:#f87171;}
</style>
</head>
<body>
<div class="header">
  <div>
    <div class="header-logo">HHA Group</div>
    <div class="header-sub">Espagiria &middot; ANIMUS Lab</div>
  </div>
  <div class="header-user">Usuario: <strong>{usuario}</strong></div>
</div>
<div class="main">
  <div class="title">&#x1F4F1; Selecciona un m&#xF3;dulo</div>
  <div class="subtitle">Elige el m&#xF3;dulo al que deseas acceder. Solo podr&#xE1;s ingresar a los que tienes autorizaci&#xF3;n.</div>
  <div class="grid">
    <a class="mod-card" href="/inventarios"><span class="mod-icon">&#x1F4E6;</span><span class="mod-name">Inventario</span></a>
    <a class="mod-card" href="/compras"><span class="mod-icon">&#x1F6D2;</span><span class="mod-name">Compras</span></a>
    <a class="mod-card" href="/recepcion"><span class="mod-icon">&#x1F69A;</span><span class="mod-name">Recepci&#xF3;n</span></a>
    <a class="mod-card" href="/clientes"><span class="mod-icon">&#x1F91D;</span><span class="mod-name">Clientes</span></a>
    <a class="mod-card" href="/financiero"><span class="mod-icon">&#x1F4CA;</span><span class="mod-name">Financiero</span></a>
    <a class="mod-card" href="/compromisos"><span class="mod-icon">&#x2705;</span><span class="mod-name">Compromisos</span></a>
    <a class="mod-card" href="/hub-salida"><span class="mod-icon">&#x1F9EA;</span><span class="mod-name">Maquila</span></a>
    <a class="mod-card" href="/calidad"><span class="mod-icon">&#x1F52C;</span><span class="mod-name">Calidad</span></a>
    <a class="mod-card" href="/tecnica"><span class="mod-icon">&#x1F527;</span><span class="mod-name">T&#xE9;cnica</span></a>
    <a class="mod-card" href="/rrhh"><span class="mod-icon">&#x1F465;</span><span class="mod-name">RRHH</span></a>
    <a class="mod-card" href="/solicitudes"><span class="mod-icon">&#x1F4DD;</span><span class="mod-name">Solicitudes</span></a>
  </div>
  <div class="footer">
    <a class="logout-btn" href="/logout">&#x23CF; Cerrar sesi&#xF3;n</a>
  </div>
</div>
</body>
</html>"""
