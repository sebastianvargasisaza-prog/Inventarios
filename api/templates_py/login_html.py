# Auto-extraído de index.py - Fase A refactor (rebranded EOS)
# Rediseñado 14-ago-2026 (Sebastián: "el ingreso se ve feito, no premium").
# El símbolo iba violeta sobre un tile violeta y casi no se leía; los campos
# eran oscuros sobre oscuro y el fondo ignoraba el tema. Ahora vive sobre los
# tokens de cortex (claro y oscuro, siguiendo la preferencia del sistema) y el
# contrato con el backend queda intacto: mismo form, mismos names, {error} y
# {next_url} en su lugar.
LOGIN_HTML = """<!DOCTYPE html>
<html lang="es" translate="no">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>EOS · Acceso</title>
<script>(function(){try{var t=localStorage.getItem("cx-theme");if(!t&&window.matchMedia&&window.matchMedia("(prefers-color-scheme: dark)").matches){t="dark";}if(t==="dark"){document.documentElement.setAttribute("data-theme","dark");}}catch(e){}})();</script>
<link rel="stylesheet" href="/static/cortex.css?v=eos15">
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
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;
     background:var(--cx-bg);color:var(--cx-text);min-height:100vh;
     display:flex;flex-direction:column;align-items:center;justify-content:center;padding:24px 18px;
     -webkit-font-smoothing:antialiased}
/* El aura da profundidad sin pintar el fondo: funciona igual en claro y en oscuro. */
.aura{position:fixed;inset:0;pointer-events:none;z-index:0;
      background:radial-gradient(760px 460px at 50% -12%, rgba(167,139,250,.20), transparent 70%)}
.shell{position:relative;z-index:1;width:100%;max-width:436px}
.card{background:var(--cx-card);border:1px solid var(--cx-border);
      border-radius:var(--cx-r-xl);padding:40px 34px 32px;
      box-shadow:var(--cx-sh-lg)}
.logo{text-align:center;margin-bottom:30px}
/* El símbolo va BLANCO sobre el tile violeta · antes iba violeta sobre violeta y no se leía. */
.brand-mark{display:inline-flex;align-items:center;justify-content:center;width:74px;height:74px;
            border-radius:21px;margin-bottom:18px;
            background:var(--cx-primary-grad);
            box-shadow:0 14px 32px rgba(109,40,217,.34)}
.brand-name{font-size:34px;font-weight:800;letter-spacing:-1.2px;line-height:1}
.brand-tag{color:var(--cx-primary-text);font-size:13px;font-style:italic;margin-top:6px}
.brand-casas{margin-top:14px;display:flex;align-items:center;justify-content:center;gap:8px;
             font-size:10.5px;font-weight:800;text-transform:uppercase;letter-spacing:1.2px;
             color:var(--cx-text-mute)}
.brand-casas span.sep{width:3px;height:3px;border-radius:50%;background:var(--cx-text-faint)}
label{display:block;color:var(--cx-text-mute);font-size:11px;font-weight:800;
      margin-bottom:6px;text-transform:uppercase;letter-spacing:.7px}
.fg{margin-bottom:16px}
input[type=text],input[type=password]{width:100%;padding:13px 15px;font-size:15px;font-family:inherit;
      background:var(--cx-bg-alt);color:var(--cx-text);
      border:1px solid var(--cx-border);border-radius:var(--cx-r-md);outline:none;transition:.15s}
input[type=text]::placeholder,input[type=password]::placeholder{color:var(--cx-text-faint)}
input[type=text]:focus,input[type=password]:focus{border-color:var(--cx-primary-light);
      background:var(--cx-card);box-shadow:0 0 0 3px var(--cx-primary-pale)}
.btn{width:100%;background:var(--cx-primary-grad);color:#fff;
     border:none;border-radius:var(--cx-r-md);padding:14px;font-size:15px;font-weight:800;
     letter-spacing:.2px;cursor:pointer;margin-top:8px;transition:.15s;
     box-shadow:0 8px 20px rgba(109,40,217,.28)}
.btn:hover{transform:translateY(-1px);box-shadow:0 12px 26px rgba(109,40,217,.36)}
.err{background:var(--cx-danger-pale);color:var(--cx-danger-text);
     border-left:3px solid var(--cx-danger);padding:11px 14px;
     border-radius:var(--cx-r-sm);font-size:13px;margin-bottom:18px}
.back{text-align:center;margin-top:20px}
.back a{color:var(--cx-text-mute);font-size:12.5px;text-decoration:none;font-weight:600}
.back a:hover{color:var(--cx-primary-text)}
.app-footer{margin-top:24px;text-align:center;font-size:11px;color:var(--cx-text-mute);
            line-height:1.8}
.app-footer strong{color:var(--cx-text-soft)}
@media(max-width:480px){
  .card{padding:32px 22px 26px}
  .brand-name{font-size:29px}
}
</style>
</head>
<body>
<div class="aura"></div>
<main class="shell">
<div class="card">
  <div class="logo">
    <span class="brand-mark" aria-label="EOS">
      <svg viewBox="0 0 32 32" width="40" height="40" fill="none" stroke="#ffffff" xmlns="http://www.w3.org/2000/svg">
        <circle cx="16" cy="12" r="3" fill="#ffffff"/>
        <path d="M 5 19 Q 16 17, 27 19" stroke-width="1.6" stroke-linecap="round" opacity=".85"/>
        <path d="M 5 23 Q 16 21, 27 23" stroke-width="1.6" stroke-linecap="round" opacity=".5"/>
      </svg>
    </span>
    <div class="brand-name">EOS</div>
    <div class="brand-tag">Todo el holding, al frente</div>
    <div class="brand-casas">Espagiria<span class="sep"></span>ÁNIMUS Lab<span class="sep"></span>HHA Group</div>
  </div>
  {error}
  <form method="POST" action="/login?next={next_url}">
    <div class="fg"><label for="username">Usuario</label><input type="text" id="username" name="username" placeholder="Ej: Sebastian, Catalina..." required autofocus autocomplete="username"></div>
    <div class="fg"><label for="password">Contraseña</label><input type="password" id="password" name="password" placeholder="Tu contraseña" required autocomplete="current-password"></div>
    <button type="submit" class="btn">Ingresar</button>
  </form>
  <div class="back"><a href="/">Volver al inicio</a></div>
</div>
<footer class="app-footer">
  <div><strong>EOS v1.0</strong> &middot; Edición Espagiria</div>
  <div>&copy; 2026 HHA Group S.A.S. &middot; Todos los derechos reservados</div>
</footer>
</main>
</body>
</html>"""
