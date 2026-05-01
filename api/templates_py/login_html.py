# Auto-extraído de index.py — Fase A refactor (rebranded EOS)
LOGIN_HTML = """<!DOCTYPE html>
<html lang="es" translate="no">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>EOS · Acceso</title>
<link rel="stylesheet" href="/static/cortex.css?v=eos12">
<script>(function(){try{var t=localStorage.getItem("cx-theme");if(t==="dark")document.documentElement.setAttribute("data-theme","dark");}catch(e){}})();</script>
<meta name="application-name" content="EOS">
<meta name="apple-mobile-web-app-title" content="EOS">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="mobile-web-app-capable" content="yes">
<meta name="theme-color" content="#6d28d9">
<meta name="description" content="EOS · Todo el holding, al frente · Desarrollado por HHA Group">
<meta name="author" content="HHA Group">
<link rel="manifest" href="/manifest.json">
<link rel="icon" type="image/x-icon" href="/static/favicon.ico?v=eos11">
<link rel="icon" type="image/png" sizes="32x32" href="/static/icons/favicon-32.png?v=eos11">
<link rel="apple-touch-icon" sizes="180x180" href="/static/icons/apple-touch-icon-180.png?v=eos11">
<style>
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;background:radial-gradient(ellipse at top,#1e1b4b 0%,#0f172a 50%,#0a0a0f 100%);min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:20px;color:#e2e8f0;}
.card{background:rgba(30,41,59,0.7);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);border:1px solid rgba(167,139,250,0.2);border-radius:20px;padding:48px 40px;width:100%;max-width:440px;box-shadow:0 20px 60px rgba(109,40,217,0.15);}
.logo{text-align:center;margin-bottom:36px;}
.brand-mark{display:inline-block;width:80px;height:80px;border-radius:18px;margin-bottom:18px;box-shadow:0 12px 36px rgba(109,40,217,0.45);}
.brand-name{font-size:30px;font-weight:800;letter-spacing:-0.8px;background:linear-gradient(135deg,#c4b5fd,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;margin-bottom:4px;}
.brand-tag{color:#a78bfa;font-size:12px;font-style:italic;margin-bottom:14px;}
.brand-by{color:#64748b;font-size:10px;text-transform:uppercase;letter-spacing:1.5px;}
.brand-by strong{color:#cbd5e1;}
label{display:block;color:#94a3b8;font-size:0.8em;font-weight:700;margin-bottom:8px;text-transform:uppercase;letter-spacing:0.5px;}
.fg{margin-bottom:20px;}
input[type=text],input[type=password]{width:100%;background:rgba(15,23,42,0.6);border:1px solid #334155;border-radius:10px;padding:14px 16px;color:white;font-size:1em;outline:none;transition:.2s;}
input[type=text]:focus,input[type=password]:focus{border-color:#a78bfa;background:rgba(15,23,42,0.9);box-shadow:0 0 0 3px rgba(167,139,250,0.15);}
.btn{width:100%;background:linear-gradient(135deg,#a78bfa,#6d28d9);color:white;border:none;border-radius:10px;padding:14px;font-size:1em;font-weight:700;cursor:pointer;margin-top:8px;transition:.2s;letter-spacing:0.3px;}
.btn:hover{transform:translateY(-1px);box-shadow:0 8px 20px rgba(109,40,217,0.4);}
.err{background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.3);color:#f87171;padding:12px 16px;border-radius:8px;font-size:0.88em;margin-bottom:20px;text-align:center;}
.users-hint{text-align:center;color:#475569;font-size:0.78em;margin-top:14px;margin-bottom:4px;}
.back{text-align:center;margin-top:18px;}
.back a{color:#64748b;font-size:0.83em;text-decoration:none;}
.back a:hover{color:#a78bfa;}
.app-footer{margin-top:32px;text-align:center;font-size:10px;color:#475569;letter-spacing:0.5px;line-height:1.6;}
.app-footer strong{color:#94a3b8;}
@media(max-width:480px){
  .card{padding:36px 24px;}
  .brand-name{font-size:26px;}
}
</style>
</head>
<body>
<div class="card">
  <div class="logo">
    <span class="brand-mark" style="display:inline-flex;align-items:center;justify-content:center;color:#6d28d9;" aria-label="EOS">
      <svg viewBox="0 0 32 32" width="64" height="64" fill="none" stroke="#6d28d9" xmlns="http://www.w3.org/2000/svg">
        <circle cx="16" cy="12" r="3" fill="#6d28d9"/>
        <path d="M 5 19 Q 16 17, 27 19" stroke-width="1.5" stroke-linecap="round" opacity=".55"/>
        <path d="M 5 23 Q 16 21, 27 23" stroke-width="1.5" stroke-linecap="round" opacity=".25"/>
      </svg>
    </span>
    <div class="brand-name">EOS</div>
    <div class="brand-tag">Todo el holding, al frente</div>
    <div class="brand-by">by <strong>HHA Group</strong></div>
  </div>
  {error}
  <form method="POST" action="/login?next={next_url}">
    <div class="fg"><label>Usuario</label><input type="text" name="username" placeholder="Ej: Sebastian, Catalina..." required autofocus autocomplete="username"></div>
    <div class="fg"><label>Contraseña</label><input type="password" name="password" placeholder="••••••••" required autocomplete="current-password"></div>
    <button type="submit" class="btn">Ingresar →</button>
  </form>
  <div class="back"><a href="/">← Volver al portal</a></div>
</div>
<footer class="app-footer">
  <div><strong>EOS v1.0</strong> &middot; Edición Espagiria</div>
  <div style="margin-top:4px;">Desarrollado por <strong>HHA Group</strong></div>
  <div style="margin-top:6px;color:#334155;">&copy; 2026 HHA Group S.A.S. &middot; Todos los derechos reservados</div>
</footer>
</body>
</html>"""
