# Auto-extraído de index.py — Fase A refactor
LOGIN_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>HHA Group — Acceso Compras</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:'Segoe UI',system-ui,sans-serif;background:#0f172a;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px;}
.card{background:#1e293b;border:1px solid #334155;border-radius:20px;padding:48px 40px;width:100%;max-width:420px;}
.logo{text-align:center;margin-bottom:36px;}
.logo-badge{display:inline-block;background:linear-gradient(135deg,#f59e0b,#ef4444);border-radius:12px;padding:10px 28px;margin-bottom:14px;}
.logo-text{font-size:1.5em;font-weight:900;color:white;letter-spacing:4px;}
.logo-mod{color:#f59e0b;font-weight:700;font-size:1.05em;margin-bottom:4px;}
.logo-sub{color:#64748b;font-size:0.82em;}
label{display:block;color:#94a3b8;font-size:0.8em;font-weight:700;margin-bottom:8px;text-transform:uppercase;letter-spacing:0.5px;}
.fg{margin-bottom:20px;}
input[type=text],input[type=password]{width:100%;background:#0f172a;border:1px solid #334155;border-radius:10px;padding:14px 16px;color:white;font-size:1em;outline:none;}
.btn{width:100%;background:linear-gradient(135deg,#f59e0b,#ef4444);color:white;border:none;border-radius:10px;padding:14px;font-size:1em;font-weight:700;cursor:pointer;margin-top:8px;}
.err{background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.3);color:#f87171;padding:12px 16px;border-radius:8px;font-size:0.88em;margin-bottom:20px;text-align:center;}
.back{text-align:center;margin-top:24px;}
.back a{color:#475569;font-size:0.83em;text-decoration:none;}
</style>
</head>
<body>
<div class="card">
  <div class="logo">
    <div class="logo-badge"><div class="logo-text">HHA</div></div>
    <div class="logo-mod">Módulo de Compras</div>
    <div class="logo-sub">Solo acceso autorizado</div>
  </div>
  {error}
  <form method="POST" action="/login?next={next_url}">
    <div class="fg"><label>Usuario</label><input type="text" name="username" placeholder="Ej: Sebastian, Catalina..." required autofocus autocomplete="username"></div>
    <div class="fg"><label>Contraseña</label><input type="password" name="password" placeholder="••••••••" required></div>
    <button type="submit" class="btn">Ingresar al sistema →</button>
  </form>
  <div style="text-align:center;color:#475569;font-size:0.78em;margin-top:12px;margin-bottom:4px;">Usuarios: Sebastian · Alejandro · Catalina · Luz · Mayra</div>
  <div class="back"><a href="/">← Volver al portal HHA Group</a></div>
</div>
</body>
</html>"""
