"""Centro de Operaciones - Vista ejecutiva CEO.
Dashboard unificado con TODO de cada area en un solo vistazo."""

HTML = r"""
<!DOCTYPE html>
<html lang="es" translate="no">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Centro de Operaciones - HHA Group</title>
<link rel="stylesheet" href="/static/cortex.css?v=eos15">
<script>(function(){try{var t=localStorage.getItem("cx-theme");if(t==="dark")document.documentElement.setAttribute("data-theme","dark");}catch(e){}})();</script>
<style>
  * { box-sizing: border-box; }
  /* El fondo estaba FIJO en claro mientras el color del texto sí era token: al invertir el
     tema el texto se aclaraba y el fondo no, y el contraste caía a 1.0 -- o sea, texto
     invisible en la pantalla principal del CEO. Es M104 en su forma más cara: un par
     (fondo, texto) donde sólo uno de los dos sigue al tema. Medido con los tokens: 16.1 en
     claro y 16.3 en oscuro. */
  body { margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; background:var(--cx-bg); color:var(--cx-text); }
  .header { background:linear-gradient(135deg,#4c1d95 0%,#6d28d9 100%); padding:18px 28px; display:flex;align-items:center;justify-content:space-between; color:#fff; }
  .header h1 { margin:0; font-size:1.4em; font-weight:700; color:#fff; }
  .header a { color:#ddd6fe; font-size:0.85em; text-decoration:none; }
  .header a:hover { color:#fff; }
  .live-dot { display:inline-block; width:8px; height:8px; background:var(--cx-accent); border-radius:50%; margin-right:6px; animation:pulse 2s infinite; vertical-align:middle; }
  @keyframes pulse { 0%,100%{opacity:1;} 50%{opacity:0.4;} }
  .container { max-width:1600px; margin:0 auto; padding:18px; }
  .grid { display:grid; gap:14px; }
  .grid-6 { grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); }
  .grid-2 { grid-template-columns:1fr 1fr; }
  .card { background:var(--cx-card); border:1px solid var(--cx-hairline); border-radius:14px; padding:16px; box-shadow:var(--cx-sh-card); transition:box-shadow .2s ease,transform .2s ease; }
  .card:hover { transform:translateY(-2px); box-shadow:var(--cx-sh-card-hover); }
  .card .label { font-size:0.7em; color:var(--cx-text-mute); text-transform:uppercase; letter-spacing:0.06em; font-weight:700; margin-bottom:8px; }
  .card .val { font-size:1.8em; font-weight:800; color:var(--cx-text); line-height:1; }
  .card .sub { font-size:0.78em; color:var(--cx-text-faint); margin-top:6px; }
  .card .delta { font-size:0.7em; padding:2px 8px; border-radius:8px; font-weight:700; display:inline-block; }
  .delta-pos { background:var(--cx-success-pale); color:var(--cx-success-text); }
  .delta-neg { background:var(--cx-danger-pale); color:var(--cx-danger-text); }
  .delta-warn { background:var(--cx-warn-pale); color:var(--cx-warn-dark,#b45309); }
  .delta-neutral { background:var(--cx-info-pale); color:var(--cx-info-text); }
  .area-title { font-size:0.78em; font-weight:700; color:var(--cx-text-mute); text-transform:uppercase; letter-spacing:0.1em; margin:24px 0 8px; padding-bottom:6px; border-bottom:1px solid var(--cx-hairline); display:flex; align-items:center; }
  .area-title-icon { margin-right:8px; }
  .panel { background:var(--cx-card); border:1px solid var(--cx-hairline); border-radius:14px; padding:18px; box-shadow:var(--cx-sh-card); }
  .panel h3 { margin:0 0 12px; font-size:0.95em; color:var(--cx-text); display:flex; align-items:center; gap:8px; }
  .activity { font-size:0.82em; max-height:280px; overflow-y:auto; }
  .activity-row { padding:8px 0; border-bottom:1px solid var(--cx-bg-alt); display:flex; gap:10px; align-items:start; }
  .activity-row:last-child { border-bottom:none; }
  .activity-icon { font-size:14px; flex-shrink:0; }
  .activity-content { flex:1; min-width:0; }
  .activity-title { font-weight:600; color:var(--cx-text); font-size:12px; }
  .activity-detail { font-size:11px; color:var(--cx-text-mute); margin-top:2px; }
  .activity-time { font-size:10px; color:var(--cx-text-faint); white-space:nowrap; }
  .quick-link { display:inline-flex; align-items:center; gap:6px; padding:5px 10px; background:var(--cx-primary-soft); color:var(--cx-primary-text); border-radius:6px; text-decoration:none; font-size:11px; font-weight:600; margin-left:8px; }
  .quick-link:hover { background:var(--cx-primary-soft); }
  .empty { color:var(--cx-text-faint); font-style:italic; padding:20px; text-align:center; font-size:13px; }
  .refresh-btn { background:transparent; border:1px solid var(--cx-border); color:var(--cx-text-soft); border-radius:6px; padding:6px 12px; cursor:pointer; font-size:12px; }
  .refresh-btn:hover { border-color:var(--cx-primary); color:var(--cx-primary-text); }
  /* Mobile responsive */
  @media (max-width:768px) {
    .header { padding:12px 14px; flex-wrap:wrap; gap:8px; }
    .header h1 { font-size:1.05em; }
    .container { padding:10px; }
    .grid-6 { grid-template-columns:repeat(2,1fr); gap:8px; }
    .grid-2 { grid-template-columns:1fr; }
    .card { padding:12px; }
    .card .val { font-size:1.4em; }
    .card .label { font-size:0.65em; }
    .area-title { font-size:0.7em; margin:16px 0 6px; }
    .panel { padding:14px; }
  }
  @media (max-width:480px) {
    .grid-6 { grid-template-columns:1fr 1fr; }
    .header h1 { font-size:0.95em; }
  }
  /* Pestañas del Centro de Mando */
  .cm-tabs { display:flex; gap:8px; flex-wrap:wrap; margin:6px 0 20px; border-bottom:1px solid var(--cx-hairline); padding-bottom:0; }
  .cm-tab { appearance:none; border:none; background:transparent; cursor:pointer; font-size:14px; font-weight:600;
            color:var(--cx-text-mute); padding:10px 4px; margin-right:14px; border-bottom:2.5px solid transparent;
            transition:color .15s, border-color .15s; display:inline-flex; align-items:center; gap:7px; }
  .cm-tab:hover { color:var(--cx-primary-text); }
  .cm-tab.active { color:var(--cx-primary-text); border-bottom-color:var(--cx-primary); }
  .cm-badge { min-width:18px; height:18px; padding:0 5px; border-radius:9px; background:var(--cx-danger,#dc2626); color:#fff;
              font-size:10px; font-weight:700; display:none; align-items:center; justify-content:center; line-height:1; }
  .cm-badge.on { display:inline-flex; }
  /* Grid de decisiones. `auto-fill` reserva las columnas aunque no haya tarjetas que las
     llenen: un grupo con 1 sola decisión dejaba dos huecos vacíos a la derecha y la pantalla
     se veía a medio usar. `auto-fit` colapsa las columnas sobrantes, así una tarjeta sola
     ocupa el ancho completo y tres se reparten parejo. */
  #decisiones { display:grid; grid-template-columns:repeat(auto-fit,minmax(400px,1fr)); gap:12px; }
  .container { max-width:1800px; }
  /* El encabezado de tema ocupa la fila entera: sin eso las tarjetas se acomodan alrededor
     y el separador queda flotando en el medio de la grilla. */
  #decisiones .dec-sep { grid-column:1/-1; font-size:12px; font-weight:800; color:var(--cx-text);
    text-transform:uppercase; letter-spacing:.06em; padding:10px 2px 2px; display:flex; align-items:center; gap:7px; }
  #decisiones .dec-sep:first-child { padding-top:0; }
  /* Sub-pestañas dentro de una sección (Pagos › Influencers) */
  .cm-subtabs { display:flex; gap:6px; flex-wrap:wrap; margin:0 0 16px; border-bottom:1px solid var(--cx-hairline); }
  .cm-subtab { appearance:none; border:none; background:transparent; cursor:pointer; font-size:13px; font-weight:700;
    color:var(--cx-text-mute); padding:9px 16px; border-bottom:3px solid transparent; display:inline-flex; align-items:center; gap:7px; }
  .cm-subtab.active { color:var(--cx-primary-text); border-bottom-color:var(--cx-primary); }
  .pg-chip { border:1px solid var(--cx-border); background:transparent; color:var(--cx-text-mute);
    border-radius:20px; padding:6px 14px; font-size:12px; font-weight:600; cursor:pointer; }
  .pg-chip.on { border-color:var(--cx-primary); background:var(--cx-primary); color:#fff; }
  /* Fila de pago: cerrada muestra lo mínimo para reconocerla; abierta, todo para decidir. */
  .pg-row { background:var(--cx-card); border:1px solid var(--cx-hairline); border-radius:14px;
    margin-bottom:10px; box-shadow:var(--cx-sh-sm); overflow:hidden; border-left:4px solid var(--cx-border); }
  .pg-row.alerta { border-left-color:var(--cx-danger); }
  .pg-row.ok     { border-left-color:var(--cx-success); }
  .pg-head { display:flex; align-items:center; gap:14px; padding:14px 18px; cursor:pointer; }
  .pg-head:hover { background:var(--cx-bg-alt); }
  .pg-ini { width:40px; height:40px; border-radius:12px; display:flex; align-items:center; justify-content:center;
    font-weight:800; font-size:15px; color:#fff; background:var(--cx-primary-grad,var(--cx-primary)); flex:0 0 auto; }
  .pg-nom { font-weight:800; font-size:15px; color:var(--cx-text); letter-spacing:-.01em; }
  .pg-sub { font-size:12px; color:var(--cx-text-mute); margin-top:2px; }
  .pg-monto { font-size:17px; font-weight:800; color:var(--cx-text); white-space:nowrap; letter-spacing:-.02em; }
  .pg-body { padding:0 18px 16px; border-top:1px dashed var(--cx-border); }
  .pg-ficha { display:grid; grid-template-columns:repeat(auto-fit,minmax(140px,1fr)); gap:12px 16px; margin:14px 0; }
  .pg-ficha .lbl { font-size:9.5px; font-weight:700; color:var(--cx-text-mute); text-transform:uppercase; letter-spacing:.05em; }
  .pg-ficha .val { font-size:13px; color:var(--cx-text); margin-top:2px; word-break:break-word; }
  /* La ficha va POR PARTES (Sebastián 4-ago): quién es y qué publicó · qué se le debe · a dónde
     se consigna. Trece campos seguidos en una sola grilla se leen como un muro, y el dato que
     de verdad se copia -- la cuenta -- queda perdido entre el resto. */
  .pg-bloque { margin:14px 0 0; }
  .pg-bloque-tit { font-size:9.5px; font-weight:800; text-transform:uppercase; letter-spacing:.08em;
    color:var(--cx-text-mute); display:flex; align-items:center; gap:9px; margin-bottom:2px; }
  .pg-bloque-tit::after { content:''; flex:1; height:1px; background:var(--cx-hairline); }
  .pg-bloque .pg-ficha { margin:9px 0 0; }
  .pg-banco { background:var(--cx-bg-alt); border:1px solid var(--cx-hairline);
    border-radius:12px; padding:11px 14px 13px; margin-top:9px; }
  .pg-banco .pg-ficha { margin:0; }
  .pg-banco .val { font-variant-numeric:tabular-nums; }
  .pg-ficha .pg-cuenta .val { font-size:15px; font-weight:800; letter-spacing:.01em; }
  .pg-alerta { background:var(--cx-danger-pale); color:var(--cx-danger-text); border-radius:10px;
    padding:10px 13px; font-size:12.5px; margin-bottom:9px; line-height:1.45; }
  #decisiones .dec-card { display:flex; align-items:center; gap:14px; text-decoration:none;
            background:var(--cx-card); border:1px solid var(--cx-hairline); border-radius:14px;
            padding:15px 18px; transition:box-shadow .18s, transform .12s, border-color .18s; box-shadow:var(--cx-sh-sm); }
  #decisiones .dec-card:hover { box-shadow:0 8px 22px rgba(24,24,27,.08); transform:translateY(-2px); border-color:var(--cx-primary-light,#c4b5fd); }
  #decisiones .dec-ico { width:38px; height:38px; border-radius:11px; display:flex; align-items:center;
            justify-content:center; font-size:19px; line-height:1; flex:0 0 auto; }
  #decisiones .dec-body { flex:1; min-width:0; }
  #decisiones .dec-tit { font-weight:700; color:var(--cx-text); font-size:14.5px; letter-spacing:-.01em; }
  #decisiones .dec-det { color:var(--cx-text-mute,#78716c); font-size:12.5px; margin-top:3px; line-height:1.4; }
  #decisiones .dec-badge { font-size:9px; font-weight:700; text-transform:uppercase; letter-spacing:.7px;
            color:var(--cx-text-mute,#a8a29e); background:transparent; white-space:nowrap; flex:0 0 auto; }
  #decisiones .dec-arrow { flex:0 0 auto; display:flex; align-items:center; color:var(--cx-text-mute,#d6d3d1); transition:transform .15s, color .15s; }
  #decisiones .dec-card:hover .dec-arrow { color:var(--cx-primary-text,#6d28d9); transform:translateX(3px); }
  @media (max-width:768px){ #decisiones { grid-template-columns:1fr; } .cm-tab { font-size:12.5px; margin-right:8px; } }
  /* KPI clickeable: cada tarjeta lleva a donde ver/actuar */
  a.card { text-decoration:none; color:inherit; cursor:pointer; position:relative; display:block; }
  a.card::after { content:""; position:absolute; top:15px; right:15px; width:14px; height:14px;
                  background-color:var(--cx-primary); opacity:0; transform:translateX(-4px);
                  transition:opacity .15s, transform .15s;
                  -webkit-mask:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.6' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M9 18l6-6-6-6'/%3E%3C/svg%3E") center/contain no-repeat;
                          mask:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.6' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M9 18l6-6-6-6'/%3E%3C/svg%3E") center/contain no-repeat; }
  a.card:hover { box-shadow:0 6px 18px rgba(0,0,0,.09); transform:translateY(-1px); border-color:var(--cx-primary-soft); }
  a.card:hover::after { opacity:.85; transform:translateX(0); }
</style>
</head>
<body>
  <header class="cx-mod-header cx-fade-in">
    <span class="cx-mod-header__logo" style="display:inline-flex;align-items:center;color:var(--cx-primary-text);"><svg viewBox="0 0 32 32" width="38" height="38" fill="none" stroke="#6d28d9" xmlns="http://www.w3.org/2000/svg"><circle cx="16" cy="12" r="3" fill="#6d28d9"/><path d="M 5 19 Q 16 17, 27 19" stroke-width="1.5" stroke-linecap="round" opacity=".55"/><path d="M 5 23 Q 16 21, 27 23" stroke-width="1.5" stroke-linecap="round" opacity=".25"/></svg></span>
    <div>
      <div class="cx-mod-header__title">
        <span class="live-dot" style="display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--cx-danger);margin-right:8px;animation:pulse 1.5s infinite;"></span>
        Centro de Mando
      </div>
      <div class="cx-mod-header__sub">Tu día de un vistazo &middot; <a href="/gerencia" style="color:var(--cx-primary-text);text-decoration:none;font-weight:600">Gerencia</a> &middot; <a href="/financiero" style="color:var(--cx-primary-text);text-decoration:none;font-weight:600">Financiero</a></div>
    </div>
    <div class="cx-mod-header__nav">
      <button class="cx-btn cx-btn-ghost cx-btn-sm" onclick="cargar(true)" title="Actualizar"><svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 1 1-2.64-6.36M21 3v5h-5"/></svg>Actualizar</button>
      <a href="/modulos" class="cx-btn cx-btn-ghost cx-btn-sm" title="Volver a módulos">Módulos</a>
      <button class="cx-theme-toggle" onclick="cxToggleTheme()" title="Modo claro/oscuro">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4 12H2M22 12h-2M5.6 5.6 4.2 4.2M19.8 19.8l-1.4-1.4M5.6 18.4l-1.4 1.4M19.8 4.2l-1.4 1.4"/></svg>
      </button>
    </div>
  </header>
  <script>function cxToggleTheme(){var h=document.documentElement;var c=h.getAttribute('data-theme');var n=c==='dark'?'light':'dark';if(n==='dark')h.setAttribute('data-theme','dark');else h.removeAttribute('data-theme');try{localStorage.setItem('cx-theme',n);}catch(e){}}</script>

  <div class="container">

    <!-- NAV DE PESTAÑAS -->
    <div class="cm-tabs" id="cm-tabs">
      <button class="cm-tab active" data-pane="dec" onclick="showPane('dec')">🎯 Decisiones <span class="cm-badge" id="cm-badge-dec"></span></button>
      <button class="cm-tab" data-pane="pagos" onclick="showPane('pagos')">💸 Pagos <span class="cm-badge" id="cm-badge-pagos"></span></button>
      <button class="cm-tab" data-pane="pulso" onclick="showPane('pulso')">📊 Pulso del día</button>
      <button class="cm-tab" data-pane="pend" onclick="showPane('pend')">📋 Pendientes <span class="cm-badge" id="cm-badge-pend"></span></button>
      <button class="cm-tab" data-pane="fin" onclick="showPane('fin')">💳 Finanzas & Equipo</button>
      <button class="cm-tab" data-pane="estr" onclick="showPane('estr')">🎯 Estratégico</button>
    </div>

    <!-- PANE: PAGOS · lo que hay que pagar, con la ficha completa para decidirlo acá -->
    <div class="pane" id="pane-pagos" style="display:none">
      <div class="cm-subtabs" id="pg-subtabs">
        <button class="cm-subtab active" data-sub="influencers" onclick="showSubPago('influencers')">👥 Influencers <span id="pg-sub-n" style="opacity:.7"></span></button>
      </div>

      <!-- Sebastián 28-jul: "aquí no es necesario los estados, que me salga así de una; todos
           están aprobados, acá lo que hago es pagar o rechazar, fin". Así que no hay filtros
           de estado: todo lo que está acá espera decisión, cada uno viene abierto con sus
           datos, y las dos únicas acciones son Pagar y Rechazar. El buscador queda porque con
           25 en pantalla llegar a uno por nombre sí hace falta. -->
      <div id="pg-kpis" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin-bottom:16px"></div>
      <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:14px">
        <div style="position:relative;flex:1;min-width:240px;max-width:420px">
          <span style="position:absolute;left:13px;top:50%;transform:translateY(-50%);font-size:14px;opacity:.5;pointer-events:none">🔍</span>
          <input id="pg-buscar" type="search" placeholder="Buscar creador por nombre..." oninput="pintarPagos()"
                 style="width:100%;background:var(--cx-bg-alt);border:1px solid var(--cx-border);border-radius:999px;padding:10px 16px 10px 36px;color:var(--cx-text);font-size:13px;outline:none">
        </div>
        <span id="pg-conteo" style="font-size:12.5px;color:var(--cx-text-mute);font-weight:600"></span>
      </div>
      <div id="pg-lista"><div class="empty" style="padding:14px;color:var(--cx-text-mute)">Cargando pagos...</div></div>
    </div>

    <!-- PANE: DECISIONES (lo que puedo atacar HOY) -->
    <div class="pane" id="pane-dec">
    <!-- Lo que SOLO el CEO puede destrabar · va primero porque un tablero de CEO se abre para
         decidir, no para mirar. Todo lo calcula su modulo dueño (la caja: `caja_saldo` de
         Animus · los creadores: `_pagos_influencer_pendientes`): el tablero no recalcula nada,
         porque dos calculos del mismo hecho SIEMPRE divergen. -->
    <div class="area-title" style="border:none;padding-bottom:2px"><span class="area-title-icon">✍️</span>Espera tu decisión</div>
    <div id="ceo-decisiones" class="ceo-dec-grid"><div class="empty" style="padding:14px;color:var(--cx-text-mute)">Cargando…</div></div>

    <div class="area-title" style="border:none;padding-bottom:2px;margin-top:22px"><span class="area-title-icon">🎯</span>Lo que podés atacar hoy
      <span id="dec-resumen" style="margin-left:auto;font-size:12px;font-weight:600;color:var(--cx-text-mute)"></span>
    </div>
    <div id="dec-chips" style="display:flex;gap:6px;flex-wrap:wrap;margin:0 0 8px 0"></div>
    <!-- Segundo eje: POR TEMA. 45 tarjetas de 6 tipos distintos en una sola pared no se
         pueden atacar; agrupadas, cada tema se resuelve de una sentada. -->
    <div id="dec-grupos" style="display:flex;gap:6px;flex-wrap:wrap;margin:0 0 14px 0;padding-top:8px;border-top:1px solid var(--cx-hairline)"></div>
    <div id="decisiones"><div class="empty" style="padding:14px;color:var(--cx-text-mute)">Cargando decisiones...</div></div>
    </div>

    <!-- PANE: PULSO DEL DÍA -->
    <div class="pane" id="pane-pulso" style="display:none">

    <!-- ÁREA: CAJA HOY (solo del día - el mes vive en Financiero) -->
    <div class="area-title"><span class="area-title-icon">💰</span>Caja del día <a class="quick-link" href="/financiero" style="margin-left:auto;">Ver mes en Financiero →</a></div>
    <div class="grid grid-6">
      <a class="card" href="/financiero"><div class="label">Ingresos hoy</div><div class="val" id="caja-ing-hoy">-</div><div class="sub" style="color:var(--cx-text-mute)">solo hoy</div></a>
      <a class="card" href="/financiero"><div class="label">Egresos hoy</div><div class="val" style="color:#fca5a5" id="caja-egr-hoy">-</div><div class="sub" style="color:var(--cx-text-mute)">solo hoy</div></a>
      <a class="card" href="/financiero"><div class="label">Neto hoy</div><div class="val" id="caja-neto-hoy">-</div><div class="sub" style="color:var(--cx-text-mute)">ing − egr del día</div></a>
    </div>

    <!-- ÁREA: PRODUCCIÓN + INVENTARIO -->
    <div class="area-title"><span class="area-title-icon">🏭</span>Producción & Inventario <a class="quick-link" href="/inventarios">Ver Planta</a></div>
    <div class="grid grid-6">
      <a class="card" href="/inventarios"><div class="label">Lotes mes</div><div class="val" id="prod-lotes">-</div><div class="sub" id="prod-kg"></div></a>
      <a class="card" href="/programacion"><div class="label">Programados 30d</div><div class="val" id="prod-prog">-</div><div class="sub">próximas producciones</div></a>
      <a class="card" href="/compras"><div class="label">MPs en cero</div><div class="val" style="color:#fca5a5" id="inv-cero">-</div><div class="sub">stock crítico</div></a>
      <a class="card" href="/compras"><div class="label">MPs bajo mín.</div><div class="val" style="color:#fcd34d" id="inv-bajo">-</div><div class="sub">requieren reposición</div></a>
      <a class="card" href="/inventarios"><div class="label">Lotes vencen 7d</div><div class="val" style="color:#fcd34d" id="inv-venc">-</div><div class="sub">acción urgente</div></a>
      <a class="card" href="/aseguramiento"><div class="label">NCs abiertas</div><div class="val" style="color:var(--cx-accent)" id="ncs">-</div><div class="sub">calidad sin cerrar</div></a>
    </div>

    <!-- ÁREA: COMERCIAL -->
    <div class="area-title"><span class="area-title-icon">🛍️</span>Comercial <a class="quick-link" href="/animus">ÁNIMUS</a><a class="quick-link" href="/clientes">Clientes B2B</a></div>
    <div class="grid grid-6">
      <a class="card" href="/animus"><div class="label">Ventas Shopify hoy</div><div class="val" id="sh-hoy">-</div><div class="sub" id="sh-hoy-count"></div></a>
      <a class="card" href="/animus"><div class="label">Ventas Shopify mes</div><div class="val" id="sh-mes">-</div><div class="sub" id="sh-mes-count"></div></a>
      <a class="card" href="/clientes"><div class="label">Pedidos B2B activos</div><div class="val" id="ped-b2b">-</div><div class="sub">en proceso/listos</div></a>
    </div>

    </div><!-- /pane-pulso -->

    <!-- PANE: FINANZAS & EQUIPO -->
    <div class="pane" id="pane-fin" style="display:none">

    <!-- ÁREA: PAGOS -->
    <div class="area-title"><span class="area-title-icon">💳</span>Pagos pendientes <a class="quick-link" href="/compras">Compras</a><a class="quick-link" href="/contabilidad">Contabilidad</a></div>
    <div class="grid grid-6">
      <a class="card" href="/compras"><div class="label">OCs por pagar</div><div class="val" id="oc-pend">-</div><div class="sub" id="oc-pend-val"></div></a>
      <a class="card" href="/compras"><div class="label">Facturas con saldo</div><div class="val" id="fac-pend">-</div><div class="sub" id="fac-pend-val"></div></a>
      <a class="card" href="/marketing"><div class="label">Influencers a pagar</div><div class="val" id="mkt-toca">-</div><div class="sub">ciclo cumplido</div></a>
    </div>

    <!-- ÁREA: DIRECCIÓN TÉCNICA -->
    <div class="area-title"><span class="area-title-icon">🔧</span>Dirección Técnica <a class="quick-link" href="/tecnica">Ver módulo</a></div>
    <div class="grid grid-6">
      <a class="card" href="/tecnica"><div class="label">Fórmulas vigentes</div><div class="val" id="t-formulas">-</div><div class="sub">activas en producción</div></a>
      <a class="card" href="/admin/reportes-invima"><div class="label">Registros INVIMA</div><div class="val" id="t-invima">-</div><div class="sub">vigentes</div></a>
      <a class="card" href="/tecnica"><div class="label">SGDs vencen 30d</div><div class="val" style="color:var(--cx-accent)" id="t-sgd">-</div><div class="sub">SOPs por revisar</div></a>
    </div>

    <!-- ÁREA: PERSONAS / RRHH -->
    <div class="area-title"><span class="area-title-icon">👤</span>Personas <a class="quick-link" href="/rrhh">RRHH</a></div>
    <div class="grid grid-6">
      <a class="card" href="/rrhh"><div class="label">Empleados activos</div><div class="val" id="rrhh-act">-</div><div class="sub">en planilla</div></a>
      <a class="card" href="/rrhh"><div class="label">Ausencias pendientes</div><div class="val" style="color:var(--cx-accent)" id="rrhh-aus">-</div><div class="sub">por aprobar</div></a>
    </div>

    <!-- ÁREA: EQUIPO / COMUNICACIÓN -->
    <div class="area-title"><span class="area-title-icon">💬</span>Comunicación <a class="quick-link" href="/comunicacion">Compromisos &amp; Chat</a></div>
    <div class="grid grid-6">
      <a class="card" href="/comunicacion"><div class="label">Compromisos vencidos</div><div class="val" style="color:#fca5a5" id="t-venc">-</div><div class="sub">todas las áreas</div></a>
      <a class="card" href="/chat"><div class="label">Mensajes sin leer</div><div class="val" style="color:var(--cx-accent)" id="msg-sin">-</div><div class="sub">en mi bandeja</div></a>
      <a class="card" href="/comunicacion"><div class="label">Quejas Alta/Crítica</div><div class="val" style="color:#fca5a5" id="quejas">-</div><div class="sub">requieren acción</div></a>
      <a class="card" href="/marketing"><div class="label">Campañas activas</div><div class="val" id="camp">-</div><div class="sub">marketing</div></a>
    </div>

    <!-- ACTIVIDAD RECIENTE -->
    <div class="grid grid-2" style="margin-top:24px">
      <div class="panel">
        <h3>⚡ Actividad última hora</h3>
        <div class="activity" id="actividad"><div class="empty">Cargando...</div></div>
      </div>
      <div class="panel">
        <h3>🎯 Acceso rápido</h3>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:8px">
          <a href="/gerencia" class="card" style="text-decoration:none;text-align:center;color:var(--cx-accent)"><div style="font-size:24px;margin-bottom:4px">🏛️</div><div style="font-size:12px;font-weight:600">Gerencia</div></a>
          <a href="/financiero" class="card" style="text-decoration:none;text-align:center;color:var(--cx-success-text)"><div style="font-size:24px;margin-bottom:4px">💵</div><div style="font-size:12px;font-weight:600">Financiero</div></a>
          <a href="/programacion" class="card" style="text-decoration:none;text-align:center;color:#22d3ee"><div style="font-size:24px;margin-bottom:4px">📅</div><div style="font-size:12px;font-weight:600">Programación</div></a>
          <a href="/marketing" class="card" style="text-decoration:none;text-align:center;color:var(--cx-primary-light)"><div style="font-size:24px;margin-bottom:4px">📣</div><div style="font-size:12px;font-weight:600">Marketing</div></a>
          <a href="/calidad" class="card" style="text-decoration:none;text-align:center;color:#f87171"><div style="font-size:24px;margin-bottom:4px">🔬</div><div style="font-size:12px;font-weight:600">Calidad</div></a>
          <a href="/tecnica" class="card" style="text-decoration:none;text-align:center;color:var(--cx-accent)"><div style="font-size:24px;margin-bottom:4px">🔧</div><div style="font-size:12px;font-weight:600">Técnica</div></a>
        </div>
      </div>
    </div>
    </div><!-- /pane-fin -->

    <!-- PANE: PENDIENTES · la bandeja cross-modulo que vivia en /mi-bandeja, una pantalla a la
         que NINGUN menu enlazaba: 230 lineas alcanzables solo tecleando la URL (M121). -->
    <div class="pane" id="pane-pend" style="display:none">
      <div class="area-title" style="border:none;padding-bottom:2px"><span class="area-title-icon">📋</span>Todo lo que espera tu atención
        <span id="pend-resumen" style="margin-left:auto;font-size:12px;font-weight:600;color:var(--cx-text-mute)"></span>
      </div>
      <div id="pend-chips" style="display:flex;gap:6px;flex-wrap:wrap;margin:0 0 14px 0"></div>
      <div id="pend-lista"><div class="empty" style="padding:14px;color:var(--cx-text-mute)">Cargando pendientes…</div></div>
    </div>

    <!-- PANE: ESTRATEGICO · lo que /gerencia tenia de propio (metas, aliados, inputs del mes).
         Los KPIs de inventario/produccion NO se repiten aca: ya estan en Pulso del dia, y
         mostrarlos dos veces es como volvieron a divergir la ultima vez. -->
    <div class="pane" id="pane-estr" style="display:none">
      <div class="area-title" style="border:none;padding-bottom:2px"><span class="area-title-icon">🎯</span>Metas y canal</div>
      <div id="estr-metas" class="grid-cards"><div class="empty" style="padding:14px;color:var(--cx-text-mute)">Cargando…</div></div>

      <div class="area-title" style="border:none;padding-bottom:2px;margin-top:22px"><span class="area-title-icon">📝</span>Lo que sólo vos sabés
        <span style="margin-left:auto;font-size:11px;font-weight:500;color:var(--cx-text-mute)">se actualiza una vez al mes</span>
      </div>
      <div class="panel">
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:12px">
          <div><label class="estr-lbl">Saldo de caja declarado</label>
            <input id="estr-caja" type="number" class="estr-in" placeholder="0"></div>
          <div><label class="estr-lbl">Ingresos ÁNIMUS del mes</label>
            <input id="estr-animus" type="number" class="estr-in" placeholder="0"></div>
          <div><label class="estr-lbl">Ingresos Maquila del mes</label>
            <input id="estr-maquila" type="number" class="estr-in" placeholder="0"></div>
          <div><label class="estr-lbl">Nómina del período</label>
            <div id="estr-nomina" style="padding:9px 0;font-weight:800;color:var(--cx-text)">-</div>
            <div style="font-size:11px;color:var(--cx-text-mute)">sale de RRHH &middot; no se edita acá</div></div>
        </div>
        <label class="estr-lbl">Notas del período</label>
        <input id="estr-notas" class="estr-in" placeholder="Ej: mes de lanzamiento, pago de nómina atrasado…">
        <div style="margin-top:12px"><button class="estr-btn" onclick="estrGuardar()">💾 Guardar</button>
          <span id="estr-msg" style="margin-left:10px;font-size:12px"></span></div>
      </div>
    </div>
  </div>

<script>
</script>
<style>
/* ── Pestañas nuevas del Centro de Mando (5-ago) ── todo en tokens: un hex suelto ignora el
   tema oscuro y dispara el trinquete de deuda de diseño. */
.ceo-dec-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:13px;margin-bottom:8px}
.ceo-card{background:var(--cx-card);border:1px solid var(--cx-border);border-radius:14px;padding:15px 17px;
  box-shadow:0 1px 2px rgba(24,24,27,.04);display:flex;flex-direction:column}
.ceo-card.urge{border-left:5px solid var(--cx-danger)}
.ceo-card.ok{border-left:5px solid var(--cx-success)}
.ceo-card.espera{border-left:5px solid var(--cx-warn)}
.ceo-card-t{font-size:10.5px;font-weight:800;letter-spacing:.09em;text-transform:uppercase;color:var(--cx-text-mute)}
.ceo-card-n{font-size:22px;font-weight:800;color:var(--cx-text);letter-spacing:-.02em;line-height:1.15;margin-top:5px;
  font-variant-numeric:tabular-nums}
.ceo-card-s{font-size:11.5px;color:var(--cx-text-mute);margin-top:4px;line-height:1.45}
.ceo-lista{margin-top:10px;border-top:1px solid var(--cx-hairline);padding-top:8px}
.ceo-li{display:flex;justify-content:space-between;gap:10px;padding:5px 0;font-size:12px;
  border-bottom:1px solid var(--cx-hairline)}
.ceo-li:last-child{border-bottom:none}
.ceo-li-n{color:var(--cx-text);font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ceo-li-q{font-size:11px;color:var(--cx-text-mute);font-weight:400}
.ceo-li-v{color:var(--cx-text);font-weight:800;white-space:nowrap;font-variant-numeric:tabular-nums}
.ceo-vacio{font-size:12px;color:var(--cx-success-text);padding:3px 0}
.ceo-aviso{font-size:11.5px;color:var(--cx-danger-text);padding:3px 0}
.ceo-mas{font-size:11px;color:var(--cx-text-faint);margin-top:6px}
.ceo-ir{margin-top:10px;align-self:flex-start;font-size:11.5px;font-weight:700;color:var(--cx-primary-text);
  text-decoration:none;border:1px solid var(--cx-primary-soft,var(--cx-border));border-radius:8px;padding:5px 11px}
.ceo-ir:hover{background:var(--cx-primary-pale,var(--cx-bg-alt))}
.pend-chip{background:var(--cx-card);border:1px solid var(--cx-border);border-radius:999px;padding:5px 13px;
  font-size:12px;font-weight:700;color:var(--cx-text-soft);cursor:pointer}
.pend-chip.on{background:var(--cx-primary-pale,var(--cx-bg-alt));border-color:var(--cx-primary);color:var(--cx-primary-text)}
.pend-grupo{font-size:10.5px;font-weight:800;letter-spacing:.09em;text-transform:uppercase;
  color:var(--cx-text-mute);margin:16px 0 7px}
.pend-item{display:flex;gap:11px;align-items:flex-start;background:var(--cx-card);border:1px solid var(--cx-border);
  border-radius:12px;padding:12px 14px;margin-bottom:8px}
.pend-item.critical{border-left:5px solid var(--cx-danger)}
.pend-item.high{border-left:5px solid var(--cx-warn)}
.pend-item.medium{border-left:5px solid var(--cx-info)}
.pend-t{font-size:13px;font-weight:700;color:var(--cx-text)}
.pend-d{font-size:11.5px;color:var(--cx-text-mute);margin-top:3px;line-height:1.45}
.pend-m{font-size:10.5px;color:var(--cx-text-faint);margin-top:5px;display:flex;gap:9px;flex-wrap:wrap}
.pend-ir{margin-left:auto;font-size:11.5px;font-weight:700;color:var(--cx-primary-text);text-decoration:none;
  white-space:nowrap;align-self:center}
.estr-lbl{display:block;font-size:11px;font-weight:700;color:var(--cx-text-soft);margin-bottom:5px}
.estr-in{width:100%;background:var(--cx-card);border:1.5px solid var(--cx-border);color:var(--cx-text);
  padding:9px 12px;border-radius:9px;font-size:13.5px;box-sizing:border-box;font-family:inherit}
.estr-in:focus{outline:none;border-color:var(--cx-primary)}
.estr-btn{background:var(--cx-primary-grad,var(--cx-primary));color:#fff;border:none;border-radius:9px;
  padding:9px 20px;font-size:13px;font-weight:700;cursor:pointer;font-family:inherit}
.estr-card{background:var(--cx-card);border:1px solid var(--cx-border);border-radius:14px;padding:15px 17px}
.estr-card .n{font-size:21px;font-weight:800;color:var(--cx-text);letter-spacing:-.02em;
  font-variant-numeric:tabular-nums}
.estr-card .l{font-size:10.5px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:var(--cx-text-mute)}
.estr-card .s{font-size:11.5px;color:var(--cx-text-mute);margin-top:4px}
</style>
<script>
function showPane(p){
  // ⚠ Toda pestaña nueva va TAMBIEN en esta lista. El conmutador apaga todos los paneles antes
  // de encender el destino, asi que un destino ausente deja la pantalla EN BLANCO -- y sin un
  // solo error a la vista (M112/M155).
  var panes=['dec','pagos','pulso','fin','pend','estr'];
  panes.forEach(function(x){ var el=document.getElementById('pane-'+x); if(el) el.style.display = (x===p)?'':'none'; });
  var tabs=document.querySelectorAll('#cm-tabs .cm-tab');
  tabs.forEach(function(t){ if(t.getAttribute('data-pane')===p) t.classList.add('active'); else t.classList.remove('active'); });
  // La bandeja de pagos se pide al ABRIR su pestaña, no en la carga del tablero: recorre
  // los pagos pendientes y calcula alertas de cada uno, y eso no va en la ruta critica (M43).
  if(p==='pagos' && !window._PG_DATA) cargarPagos();
  // Cada pestaña pide lo suyo al ABRIRSE, no en la carga del tablero (M43).
  if(p==='pend' && !window._PEND_DATA) cargarPendientes();
  if(p==='estr' && !window._ESTR_DATA) cargarEstrategico();
  try{ if(history && history.replaceState) history.replaceState(null,'','#'+p); }catch(e){}
}
function showSubPago(s){
  window._PG_SUB=s;
  var b=document.querySelectorAll('#pg-subtabs .cm-subtab');
  b.forEach(function(t){ if(t.getAttribute('data-sub')===s) t.classList.add('active'); else t.classList.remove('active'); });
}
function fmtM(n) { n = parseFloat(n||0); if(n>=1e6) return '$'+(n/1e6).toFixed(1)+'M'; if(n>=1e3) return '$'+(n/1e3).toFixed(0)+'K'; return '$'+Math.round(n).toLocaleString('es-CO'); }
function fmtN(n) { return (n||0).toLocaleString('es-CO'); }
function _esc(s){return String(s||'').replace(/[<>&"]/g,c=>({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;'}[c]));}

// ── ESPERA TU DECISION · lo que solo el CEO destraba ────────────────────────────
// Cada bloque se pinta por separado: si uno falla deja su aviso y NO se lleva la pantalla. Y lo
// que no se pudo medir se DICE -- un cero que nadie calculo se lee como "no hay nada que hacer"
// y significa lo contrario (M154).
function _ceoCard(cls, titulo, numero, sub, cuerpo, ir){
  return '<div class="ceo-card '+cls+'">'
    + '<div class="ceo-card-t">'+titulo+'</div>'
    + '<div class="ceo-card-n">'+numero+'</div>'
    + (sub ? '<div class="ceo-card-s">'+sub+'</div>' : '')
    + (cuerpo||'')
    + (ir ? '<a class="ceo-ir" href="'+ir[1]+'">'+ir[0]+'</a>' : '')
    + '</div>';
}
function _ceoFilas(items, pinta, vacio, tope){
  if(!items || !items.length) return '<div class="ceo-lista"><div class="ceo-vacio">'+vacio+'</div></div>';
  var n = tope||5;
  var h = '<div class="ceo-lista">' + items.slice(0,n).map(pinta).join('');
  if(items.length > n) h += '<div class="ceo-mas">y '+(items.length-n)+' más</div>';
  return h + '</div>';
}
async function cargarDecisionesCEO(){
  var box = document.getElementById('ceo-decisiones');
  if(!box) return;
  try{
    var d = await (await fetch('/api/gerencia/decisiones-ceo', {credentials:'same-origin'})).json();
    if(!d.ok){ box.innerHTML = '<div class="ceo-aviso">'+_esc(d.error||'No pude cargar')+'</div>'; return; }
    var h = '';
    if(d.caja){
      var cj = d.caja;
      var sub = 'disponible ' + fmtM(cj.disponible)
        + (cj.comprometido > 0 ? ' · ' + fmtM(cj.comprometido) + ' ya comprometido' : '');
      if(cj.sin_comprobante_n > 0) sub += ' · ' + cj.sin_comprobante_n + ' pagos sin comprobante';
      h += _ceoCard(cj.esperan_n>0?'espera':'ok', '💵 Caja menor',
        fmtM(cj.saldo) + ' <span style="font-size:12px;font-weight:600;color:var(--cx-text-mute)">en la gaveta</span>', sub,
        _ceoFilas(cj.pendientes, function(x){
          return '<div class="ceo-li"><span class="ceo-li-n">'+_esc(x.concepto)
            +' <span class="ceo-li-q">· '+_esc(x.solicitado_por)+'</span></span>'
            +'<span class="ceo-li-v">'+fmtM(x.monto)+'</span></div>';
        }, 'Nadie espera tu autorización'), ['Ir a la caja','/animus']);
    } else { h += _ceoCard('urge','💵 Caja menor','·','','<div class="ceo-aviso">No pude leerla</div>',null); }
    if(d.influencers){
      var inf = d.influencers;
      h += _ceoCard(inf.vencidos_n>0?'urge':(inf.n>0?'espera':'ok'), '📣 Pagos a creadores', fmtM(inf.monto),
        inf.n + ' esperando' + (inf.vencidos_n>0 ? ' · ' + inf.vencidos_n + ' VENCIDOS' : ''),
        _ceoFilas(inf.pendientes, function(x){
          var urg = (x.urgencia==='vencido') ? ' style="color:var(--cx-danger-text)"' : '';
          return '<div class="ceo-li"><span class="ceo-li-n"'+urg+'>'+_esc(x.influencer_nombre||x.nombre||'?')
            +(x.urgencia==='vencido' ? ' <span class="ceo-li-q">· vencido</span>' : '')
            +'</span><span class="ceo-li-v">'+fmtM(x.monto)+'</span></div>';
        }, 'Ningún creador esperando pago'), ['Ir a pagar','#pagos']);
    } else { h += _ceoCard('urge','📣 Pagos a creadores','·','','<div class="ceo-aviso">No pude leerlos</div>',null); }
    if(d.ocs_por_autorizar){
      var oc = d.ocs_por_autorizar;
      var tot = oc.reduce(function(a,x){ return a + (x.valor||0); }, 0);
      h += _ceoCard(oc.length>0?'espera':'ok', '🛒 Compras por autorizar', fmtM(tot),
        oc.length + ' órdenes revisadas',
        _ceoFilas(oc, function(x){
          return '<div class="ceo-li"><span class="ceo-li-n">'+_esc(x.proveedor||'?')
            +' <span class="ceo-li-q">· '+_esc(x.numero_oc)+'</span></span>'
            +'<span class="ceo-li-v">'+fmtM(x.valor)+'</span></div>';
        }, 'Ninguna orden esperando tu firma'), ['Ir a Compras','/compras']);
    }
    if(d.calidad){
      var q = d.calidad, tq = (q.lotes_por_liberar||0)+(q.mbr_por_aprobar||0);
      h += _ceoCard(tq>0?'espera':'ok', '🔬 Tu firma como Director Técnico', fmtN(tq),
        (q.lotes_por_liberar||0)+' lotes por liberar · '+(q.mbr_por_aprobar||0)+' procedimientos por aprobar',
        '<div class="ceo-lista"><div class="ceo-vacio">'
        + (tq>0 ? 'Un lote sin liberar es producto terminado que no se puede vender.' : 'Nada esperando tu firma.')
        + '</div></div>', ['Ir a Calidad','/calidad']);
    }
    box.innerHTML = h;
    if(d.avisos && d.avisos.length) box.innerHTML += '<div class="ceo-aviso">⚠ '+d.avisos.map(_esc).join(' · ')+'</div>';
  }catch(e){ box.innerHTML = '<div class="ceo-aviso">No pude cargar lo que espera tu decisión: '+_esc(e.message)+'</div>'; }
}

// ── PENDIENTES · la bandeja cross-modulo que vivia en /mi-bandeja ───────────────
var _PEND_FILTRO = 'all';
var _PEND_SEV = {critical:'🔴 Crítico', high:'🟡 Alta', medium:'🟢 Media'};
async function cargarPendientes(){
  var box = document.getElementById('pend-lista');
  if(!box) return;
  try{
    var d = await (await fetch('/api/bandeja-ceo', {credentials:'same-origin'})).json();
    window._PEND_DATA = d;
    pintarPendientes();
  }catch(e){ box.innerHTML = '<div class="ceo-aviso">No pude cargar los pendientes: '+_esc(e.message)+'</div>'; }
}
function pendFiltro(f){ _PEND_FILTRO = f; pintarPendientes(); }
function pintarPendientes(){
  var d = window._PEND_DATA || {};
  var items = d.items || [];
  var cnt = d.counts || {};
  var chips = document.getElementById('pend-chips');
  if(chips){
    var defs = [['all','Todos',d.total||0],['critical','🔴 Críticos',cnt.critical||0],
                ['high','🟡 Alta',cnt.high||0],['medium','🟢 Media',cnt.medium||0]];
    chips.innerHTML = defs.map(function(x){
      return '<button class="pend-chip'+(_PEND_FILTRO===x[0]?' on':'')+'" onclick="pendFiltro(\''+x[0]+'\')">'
        + x[1] + ' <b>' + x[2] + '</b></button>';
    }).join('');
  }
  var res = document.getElementById('pend-resumen');
  if(res) res.textContent = (d.total||0) + ' pendientes';
  var badge = document.getElementById('cm-badge-pend');
  if(badge) badge.textContent = (cnt.critical ? cnt.critical : (d.total||''));
  var vis = (_PEND_FILTRO==='all') ? items : items.filter(function(it){ return it.severidad===_PEND_FILTRO; });
  var box = document.getElementById('pend-lista');
  if(!vis.length){ box.innerHTML = '<div class="empty" style="padding:20px;color:var(--cx-success-text)">✅ Sin pendientes en esta categoría</div>'; return; }
  var g = {critical:[], high:[], medium:[]};
  vis.forEach(function(it){ if(g[it.severidad]) g[it.severidad].push(it); });
  var h = '';
  ['critical','high','medium'].forEach(function(sev){
    if(!g[sev].length) return;
    h += '<div class="pend-grupo">'+_PEND_SEV[sev]+' · '+g[sev].length+'</div>';
    g[sev].forEach(function(it){
      h += '<div class="pend-item '+sev+'"><div style="flex:1;min-width:0">'
        + '<div class="pend-t">'+_esc(it.titulo)+'</div>'
        + '<div class="pend-d">'+_esc(it.descripcion)+'</div>'
        + '<div class="pend-m"><span>'+_esc(it.modulo)+'</span>'
        + ((it.edad_dias !== null && it.edad_dias !== undefined) ? '<span>⏱ '+it.edad_dias+'d</span>' : '')
        + '</div></div>'
        + (it.link ? '<a class="pend-ir" href="'+_esc(it.link)+'">Abrir →</a>' : '')
        + '</div>';
    });
  });
  box.innerHTML = h;
}

// ── ESTRATEGICO · lo que /gerencia tenia de propio ──────────────────────────────
async function cargarEstrategico(){
  var box = document.getElementById('estr-metas');
  if(!box) return;
  try{
    var d = await (await fetch('/api/gerencia/dashboard-extra', {credentials:'same-origin'})).json();
    window._ESTR_DATA = d;
    var ig = d.ingresos_mes || {}, inf = d.influencer_spend || {}, mq = d.maquila_target || {};
    var h = '';
    h += '<div class="estr-card"><div class="l">Ingresos del mes</div><div class="n">'+fmtM(ig.total||0)+'</div>'
      + '<div class="s">ÁNIMUS '+fmtM(ig.animus_total||0)+' · Maquila '+fmtM(ig.maquila||0)+'</div></div>';
    h += '<div class="estr-card"><div class="l">Aliados B2B / Shopify</div><div class="n">'+fmtM(ig.aliados||0)+'</div>'
      + '<div class="s">directo Shopify '+fmtM(ig.shopify||0)+'</div></div>';
    h += '<div class="estr-card"><div class="l">Inversión en creadores (año)</div><div class="n">'+fmtM(inf.ytd||0)+'</div>'
      + '<div class="s">'+(inf.ocs||0)+' órdenes</div></div>';
    if(mq && mq.maquila_ytd !== undefined){
      h += '<div class="estr-card"><div class="l">Maquila del año</div><div class="n">'+fmtM(mq.maquila_ytd||0)+'</div>'
        + '<div class="s">'+(mq.pct_espagiria||0)+'% de la meta Espagiria</div></div>';
    }
    box.innerHTML = h;
  }catch(e){ box.innerHTML = '<div class="ceo-aviso">No pude cargar las metas: '+_esc(e.message)+'</div>'; }
  // los inputs del mes (los llena el CEO · la nomina NO se teclea, se deriva de RRHH)
  try{
    var k = await (await fetch('/api/gerencia/kpis', {credentials:'same-origin'})).json();
    var f = k.inputs_manuales || {}, nom = k.nomina || {};
    var set = function(id, v){ var e = document.getElementById(id); if(e && v) e.value = v; };
    set('estr-caja', f.saldo_caja); set('estr-animus', f.ingresos_animus);
    set('estr-maquila', f.ingresos_maquila); set('estr-notas', f.notas);
    var n = document.getElementById('estr-nomina');
    if(n) n.textContent = nom.total
      ? (fmtM(nom.total) + '  ·  ' + (nom.empleados||0) + ' personas' + (nom.periodo ? ' · ' + nom.periodo : ''))
      : 'sin nómina registrada este período';
  }catch(e){}
}
async function estrGuardar(){
  var g = function(id){ var e = document.getElementById(id); return e ? e.value : ''; };
  var msg = document.getElementById('estr-msg');
  try{
    var t = await (await fetch('/api/csrf-token',{credentials:'same-origin'})).json();
    var r = await fetch('/api/gerencia/input-manual', {method:'POST', credentials:'same-origin',
      headers:{'Content-Type':'application/json','X-CSRF-Token':t.csrf_token},
      body: JSON.stringify({saldo_caja: parseFloat(g('estr-caja'))||0,
                            ingresos_animus: parseFloat(g('estr-animus'))||0,
                            ingresos_maquila: parseFloat(g('estr-maquila'))||0,
                            notas: g('estr-notas')})});
    var d = await r.json();
    if(msg) msg.innerHTML = r.ok
      ? '<span style="color:var(--cx-success-text)">✓ '+_esc(d.message||'Guardado')+'</span>'
      : '<span style="color:var(--cx-danger-text)">'+_esc(d.error||'No se pudo')+'</span>';
  }catch(e){ if(msg) msg.innerHTML = '<span style="color:var(--cx-danger-text)">Error de red</span>'; }
}

async function cargar(forzado) {
  try {
    const d = await fetch('/api/centro/operaciones').then(r=>r.json());
    if(d.error) return;

    // CAJA - solo HOY (el mes vive en /financiero)
    const c = d.caja || {};
    document.getElementById('caja-ing-hoy').textContent = fmtM(c.ingresos_hoy);
    document.getElementById('caja-egr-hoy').textContent = fmtM(c.egresos_hoy);
    const neto = c.neto_hoy || 0;
    const eN = document.getElementById('caja-neto-hoy');
    eN.textContent = (neto>=0?'+':'')+fmtM(Math.abs(neto));
    eN.style.color = neto>=0 ? '#15803d' : '#fca5a5';

    // PRODUCCION
    const p = d.produccion || {};
    document.getElementById('prod-lotes').textContent = fmtN(p.lotes_mes);
    // `kg_mes` viene en KILOS · dividirlo otra vez mostraba 0 kg en esta pantalla mientras
    // /gerencia mostraba el valor real.
    document.getElementById('prod-kg').textContent = fmtN(Math.round(p.kg_mes||0)) + ' kg';
    document.getElementById('prod-prog').textContent = fmtN(p.programados_30d);

    // INVENTARIO
    const i = d.inventario || {};
    document.getElementById('inv-cero').textContent = fmtN(i.mps_cero);
    document.getElementById('inv-bajo').textContent = fmtN(i.mps_bajo);
    document.getElementById('inv-venc').textContent = fmtN(i.lotes_vencen_7d);

    // COMERCIAL
    const co = d.comercial || {};
    document.getElementById('sh-hoy').textContent = fmtM(co.shopify_hoy_total);
    document.getElementById('sh-hoy-count').textContent = fmtN(co.shopify_hoy_count) + ' pedidos';
    document.getElementById('sh-mes').textContent = fmtM(co.shopify_mes_total);
    document.getElementById('sh-mes-count').textContent = fmtN(co.shopify_mes_count) + ' pedidos';
    document.getElementById('ped-b2b').textContent = fmtN(co.pedidos_b2b_activos);

    // PAGOS
    const pg = d.pagos || {};
    document.getElementById('oc-pend').textContent = fmtN(pg.ocs_pendientes_count);
    document.getElementById('oc-pend-val').textContent = fmtM(pg.ocs_pendientes_valor);
    document.getElementById('fac-pend').textContent = fmtN(pg.facturas_pendientes_count);
    document.getElementById('fac-pend-val').textContent = fmtM(pg.facturas_saldo_total);

    // MARKETING
    const m = d.marketing || {};
    document.getElementById('mkt-toca').textContent = fmtN(m.influencers_toca_pagar);
    document.getElementById('camp').textContent = fmtN(m.campanas_activas);

    // EQUIPO
    const eq = d.equipo || {};
    document.getElementById('t-venc').textContent = fmtN(eq.tareas_vencidas_total);
    document.getElementById('msg-sin').textContent = fmtN(eq.mensajes_sin_leer);
    document.getElementById('quejas').textContent = fmtN(eq.quejas_alta_critica);
    document.getElementById('ncs').textContent = fmtN(eq.ncs_abiertas);

    // DIRECCIÓN TÉCNICA
    const tc = d.tecnica || {};
    document.getElementById('t-formulas').textContent = fmtN(tc.formulas_vigentes);
    // `fmtN(null)` pintaba 0 y el aviso nunca salia: la tarjeta decia "0 vigentes" cuando lo
    // que pasaba era que nadie habia mirado. Un cero y un "no pude" mandan a lugares distintos.
    document.getElementById('t-invima').textContent =
      (tc.invima_vigentes == null) ? 'sin dato' : fmtN(tc.invima_vigentes);
    document.getElementById('t-sgd').textContent = fmtN(tc.sgd_vencen_30d);

    // RRHH
    const rh = d.rrhh || {};
    document.getElementById('rrhh-act').textContent = fmtN(rh.empleados_activos);
    document.getElementById('rrhh-aus').textContent = fmtN(rh.ausencias_pendientes);

    // ACTIVIDAD
    const act = d.actividad_reciente || [];
    const aDiv = document.getElementById('actividad');
    if(!act.length) {
      aDiv.innerHTML = '<div class="empty">Sin actividad en la última hora</div>';
    } else {
      const icons = {movimiento:'📦', oc:'🛒', tarea:'📋'};
      aDiv.innerHTML = act.map(a => {
        const ic = icons[a.tipo] || '•';
        const t = (a.fecha||'').substring(11,16);
        return '<div class="activity-row">' +
          '<div class="activity-icon">'+ic+'</div>' +
          '<div class="activity-content">' +
            '<div class="activity-title">'+_esc(a.titulo||'-')+'</div>' +
            '<div class="activity-detail">'+_esc(a.detalle||'')+'</div>' +
          '</div>' +
          '<div class="activity-time">'+t+'</div>' +
        '</div>';
      }).join('');
    }
  } catch(e) { console.error('Centro error:', e); }
}

// ── DECISIONES: cola priorizada de lo que puedo atacar hoy ──
var _DEC = [];
var _DEC_FILTRO = 'todas';
var _DEC_GRUPO = 'todos';
// `pagos` faltaba y por eso esas tarjetas salian con un punto gris en vez de su icono.
// El ORDEN de esta tabla es el orden en que se muestran los temas: primero la plata.
// `cobros` es plata que ENTRA (contraentrega sin cobrar); `pagos` es plata que sale. Van
// separados a proposito: mezclarlas en un monton hace que ninguna de las dos se pueda atacar.
var _GRP_META = {pagos:['💸','Pagos'], cobros:['💵','Por cobrar'], compras:['🛒','Compras'],
                 discrepancia:['📊','Discrepancias'], inventario:['📦','Inventario'],
                 calidad:['🧪','Calidad'], equipo:['👥','Equipo']};
function _decColor(n){ return n==='critico' ? '#dc2626' : (n==='atencion' ? '#d97706' : '#0891b2'); }
async function pagarCreador(ix){
  // Paga SIN salir del Centro de Mando. Usa el endpoint CANONICO de Compras: reimplementar el
  // pago aca seria una segunda via para mover plata y las dos divergirian (espejo a egresos,
  // comprobante, auditoria, guard de sobre-pago). El CEO decide aca; Compras ejecuta.
  var d = (window._DEC_VIS||[])[ix]; if(!d || !d.pago) return;
  var p = d.pago;
  var graves = (p.alertas||[]).filter(function(a){return a.nivel==='alto';});
  var txt;
  if(graves.length){
    txt = 'OJO con este pago:\n\n' + graves.map(function(a){
      var pv=a.pago_previo;
      return '• '+a.mensaje+(pv?('\n   anterior: $'+Number(pv.valor||0).toLocaleString('es-CO')+' del '+(pv.fecha||'').slice(0,10)+(pv.entregable?' · '+pv.entregable:'')):'');
    }).join('\n') + '\n\n¿Pagar igual a '+p.nombre+'?';
  } else {
    txt = 'Pagar $'+Number(p.valor||0).toLocaleString('es-CO')+' a '+p.nombre+'?';
  }
  if(!confirm(txt)) return;
  var ref = prompt('Referencia de la transferencia (numero del banco):','');
  if(ref===null) return;
  if(!String(ref).trim()){ alert('La referencia es obligatoria para poder cruzar el pago con el banco'); return; }
  try{
    var t = await (await fetch('/api/csrf-token',{credentials:'same-origin'})).json();
    var r = await fetch('/api/ordenes-compra/'+encodeURIComponent(p.numero_oc)+'/pagar', {
      method:'PATCH', credentials:'same-origin',
      headers:{'Content-Type':'application/json','X-CSRF-Token':(t.csrf_token||t.token||'')},
      body: JSON.stringify({monto: p.valor||0, medio:'Transferencia',
                            numero_transaccion: String(ref).trim(),
                            observaciones: 'Pagado desde Centro de Mando · '+(p.entregable||'')})
    });
    var js = await r.json();
    if(!r.ok || js.error){ alert('No se pudo pagar: '+(js.error||('HTTP '+r.status))); return; }
    cargarDecisiones();
  }catch(e){ alert('Error de red: '+e.message); }
}

// ── PAGOS · la bandeja de creadores, con la ficha completa para decidir sin salir ──────
// Sebastian 27-jul: "cuando le doy click al influencer me lleva a Marketing, no deberia ser;
// deberia mostrarme el influencer con todos los datos: cuenta bancaria, nombre, monto a pagar,
// que le estoy pagando, fecha de publicacion".
window._PG_DATA = null;
window._PG_CERRADOS = {};   // por id de pago · lo que el usuario plegó a mano

function _pgMoneda(n){ return '$' + Math.round(Number(n||0)).toLocaleString('es-CO'); }

async function cargarPagos(){
  var cont=document.getElementById('pg-lista'); if(!cont) return;
  cont.innerHTML='<div class="empty" style="padding:14px;color:var(--cx-text-mute)">Cargando pagos...</div>';
  try{
    var r=await fetch('/api/centro/pagos-influencers',{credentials:'same-origin'});
    var js=await r.json();
    if(!r.ok||js.error) throw new Error(js.error||('HTTP '+r.status));
    window._PG_DATA=js;
    pintarPagos();
  }catch(e){
    cont.innerHTML='<div class="empty" style="padding:14px;color:var(--cx-danger-text)">No se pudo cargar: '+_esc(e.message)+'</div>';
  }
}



function _pgCargarCorreo(p){
  // Sin correo el comprobante NO le llega, y hasta ahora eso mandaba a otra pantalla y a
  // volver. Se carga acá, que es donde el hueco se ve (M121: una capacidad que cuesta
  // alcanzar termina sin usarse).
  if(!p.influencer_id){
    // Sin ficha de creador no hay dónde guardarlo · se DICE en vez de mostrar un campo que
    // no va a funcionar (M100).
    return '<div class="pg-dato"><div class="pg-k">Email</div>'
      + '<div class="pg-v" style="color:var(--cx-danger-text)">sin ficha de creador · '
      + 'no se le puede cargar el correo desde acá</div></div>';
  }
  var id = 'pgmail-' + p.influencer_id;
  return '<div class="pg-dato"><div class="pg-k">Email</div><div class="pg-v">'
    + '<div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap">'
    + '<input id="' + id + '" type="email" placeholder="correo@ejemplo.com" '
    + 'style="flex:1;min-width:170px;padding:6px 9px;border:1px solid var(--cx-border);'
    + 'border-radius:7px;font-size:13px;background:var(--cx-card);color:var(--cx-text)">'
    + '<button onclick="event.stopPropagation();pgGuardarCorreo(' + p.influencer_id + ')" '
    + 'style="background:var(--cx-primary-grad,#6d28d9);color:#fff;border:none;border-radius:7px;'
    + 'padding:7px 13px;font-size:12px;font-weight:700;cursor:pointer">Guardar</button>'
    + '</div>'
    + '<div id="' + id + '-msg" style="font-size:11.5px;color:var(--cx-danger-text);margin-top:4px">'
    + 'sin correo · el comprobante no le va a llegar</div>'
    + '</div></div>';
}

async function pgGuardarCorreo(iid){
  var el = document.getElementById('pgmail-' + iid);
  var msg = document.getElementById('pgmail-' + iid + '-msg');
  var mail = ((el||{}).value || '').trim();
  if(mail.indexOf('@') < 0 || mail.length < 5){
    msg.style.color = 'var(--cx-danger-text)';
    msg.textContent = 'Escribí un correo válido'; return;
  }
  msg.style.color = 'var(--cx-text-mute)';
  msg.textContent = 'Guardando...';
  try{
    var t = await (await fetch('/api/csrf-token',{credentials:'same-origin'})).json();
    // Se reusa el endpoint que YA escribe este campo · no se abre un segundo camino (M1).
    var r = await fetch('/api/marketing/influencers/' + iid + '/banco', {
      method:'PUT', credentials:'same-origin',
      headers:{'Content-Type':'application/json','X-CSRF-Token':(t.csrf_token||t.token||'')},
      body: JSON.stringify({email: mail})
    });
    var js = await r.json();
    if(!r.ok || js.error){ throw new Error(js.error || ('HTTP ' + r.status)); }
    // Se refleja en TODAS las tarjetas de ese creador (puede tener varios pagos esperando) y
    // el contador de "sin correo" baja solo.
    ((window._PG_DATA||{}).pagos||[]).forEach(function(x){
      if(String(x.influencer_id) === String(iid)) x.email = mail;
    });
    pintarPagos();
  }catch(e){
    msg.style.color = 'var(--cx-danger-text)';
    msg.textContent = 'No se pudo guardar: ' + (e.message || e);
  }
}

function pgFiltrarSinCorreo(){
  // Alterna: el mismo clic prende y apaga el filtro. Si no se pudiera apagar, quedarias
  // atrapado viendo cuatro de veinticinco sin saber por que (M112).
  window._PG_SOLO_SIN_CORREO = !window._PG_SOLO_SIN_CORREO;
  pintarPagos();
}

function pintarPagos(){
  var js=window._PG_DATA; if(!js) return;
  var todos=js.pagos||[];
  var res=js.resumen||{};

  var badge=document.getElementById('cm-badge-pagos');
  if(badge){ badge.textContent=res.n||0; badge.className='cm-badge'+((res.n||0)?' on':''); }
  var subn=document.getElementById('pg-sub-n'); if(subn) subn.textContent='('+(res.n||0)+')';

  var _sinMail = todos.filter(function(p){ return !String(p.email||'').trim(); }).length;
  var k=document.getElementById('pg-kpis');
  if(k){
    k.innerHTML=''
      +'<div class="card"><div class="label">Total por pagar</div><div class="val">'+_pgMoneda(res.total)+'</div><div class="sub">'+(res.n||0)+' creador(es) esperando</div></div>'
      +'<div class="card"><div class="label">Revisar antes</div><div class="val" style="color:'+((res.con_alerta||0)?'var(--cx-danger-text)':'var(--cx-text-mute)')+'">'+(res.con_alerta||0)+'</div><div class="sub">cobro repetido o sin fecha de publicación</div></div>'
      +'<div class="card"><div class="label">Sin novedad</div><div class="val" style="color:var(--cx-success-text)">'+Math.max(0,(res.n||0)-(res.con_alerta||0))+'</div><div class="sub">listos para pagar</div></div>'
      // El comprobante de pago se le MANDA al creador, y sin correo guardado no sale. Hasta
      // ahora eso se descubria pago por pago (el aviso salta recien al apretar Pagar): el
      // numero al frente convierte "hay un problema" en "estos cuatro, cargales el correo".
      // Es clicable porque un contador que no lleva a la lista obliga a buscarlos a mano.
      +'<div class="card" onclick="pgFiltrarSinCorreo()" style="cursor:pointer" '
      +'title="Ver sólo los que no tienen correo"><div class="label">Sin correo</div>'
      +'<div class="val" style="color:'+(_sinMail?'var(--cx-danger-text)':'var(--cx-text-mute)')+'">'+_sinMail+'</div>'
      +'<div class="sub">'+(_sinMail?'no les llega el comprobante · clic para verlos':'a todos les llega el comprobante')+'</div></div>';
  }

  var q=((document.getElementById('pg-buscar')||{}).value||'').trim().toLowerCase();
  var lista=todos.filter(function(p){
    if(window._PG_SOLO_SIN_CORREO && String(p.email||'').trim()) return false;
    return !q || (String(p.influencer_nombre||'')+' '+String(p.usuario_red||'')).toLowerCase().indexOf(q)>=0;
  });
  // Lo que hay que revisar va PRIMERO: es la unica jerarquia que importa acá.
  lista=lista.slice().sort(function(a,b){
    var ga=(a.graves||[]).length?0:1, gb=(b.graves||[]).length?0:1;
    if(ga!==gb) return ga-gb;
    return String(a.vence_pago_at||a.fecha||'').localeCompare(String(b.vence_pago_at||b.fecha||''));
  });
  window._PG_VIS=lista;

  var cnt=document.getElementById('pg-conteo');
  if(cnt) cnt.textContent = lista.length===(todos.length)
    ? '' : (lista.length+' de '+todos.length);

  var cont=document.getElementById('pg-lista');
  if(!lista.length){
    cont.innerHTML='<div class="empty" style="padding:18px;color:var(--cx-success-text);font-weight:600">✓ No hay pagos esperando.</div>';
    return;
  }
  cont.innerHTML=lista.map(function(p,ix){ return _pgFila(p,ix); }).join('');
}

function _pgDato(lbl,val,cls){
  if(val===null||val===undefined||val==='') return '';
  return '<div'+(cls?' class="'+cls+'"':'')+'><div class="lbl">'+lbl+'</div>'
       + '<div class="val">'+_esc(String(val))+'</div></div>';
}

// Un bloque de la ficha. Si todos sus campos vinieron vacíos NO se pinta el título: un
// encabezado sobre una franja en blanco se lee como "falta el dato" y no como "no aplica".
function _pgBloque(titulo, campos, cls){
  var cuerpo=campos.join('');
  if(!cuerpo.trim()) return '';
  return '<div class="pg-bloque">'
    + '<div class="pg-bloque-tit">'+titulo+'</div>'
    + '<div class="'+(cls||'')+'"><div class="pg-ficha">'+cuerpo+'</div></div>'
  + '</div>';
}

function _pgFila(p, ix){
  var grave=(p.graves||[]).length>0;
  var ini=String(p.influencer_nombre||'?').trim().charAt(0).toUpperCase();
  // Todo viene ABIERTO: lo unico que se hace acá es pagar o rechazar, y para eso hay que ver
  // la cuenta y que publico. Tener que abrir 25 tarjetas de a una no es trabajo, es fricción.
  // Lo plegado se recuerda por ID del pago, no por posición: la lista se reordena al buscar
  // y con el índice se plegaría la fila equivocada.
  var abierto = !window._PG_CERRADOS[p.id];
  var sub = (p.fecha_publicacion? 'Publicó '+_esc(String(p.fecha_publicacion).slice(0,10)) : '⚠ sin fecha de publicación')
          + (p.entregable? ' · '+_esc(String(p.entregable).slice(0,60)) : '');

  var cuerpo='';
  if(abierto){
    var alertas=(p.alertas||[]).filter(function(a){return a.nivel==='alto';}).map(function(a){
      var pv=a.pago_previo;
      return '<div class="pg-alerta"><b>⚠ '+_esc(a.mensaje||'')+'</b>'
        +(pv? '<div style="margin-top:4px;opacity:.9">Pago anterior: '+_pgMoneda(pv.valor||0)
              +' del '+_esc(String(pv.fecha||'').slice(0,10))
              +(pv.entregable? ' · '+_esc(pv.entregable) : '')+'</div>' : '')
      +'</div>';
    }).join('');

    // Los datos bancarios van en su propio bloque, en su recuadro: es lo que se copia al banco
    // y hasta ahora quedaba mezclado con la fecha de publicación y el número de orden.
    var puedeVerBanco = !!(window._PG_DATA && window._PG_DATA.ve_datos_bancarios);
    var bloqueBanco = puedeVerBanco
      ? _pgBloque('Para consignar', [
          _pgDato('Banco', p.banco),
          _pgDato('Tipo de cuenta', p.tipo_cuenta),
          _pgDato('Número de cuenta', p.cuenta_bancaria, 'pg-cuenta'),
          _pgDato('Cédula / NIT', p.cedula_nit)
        ], 'pg-banco')
      : '<div class="pg-bloque"><div class="pg-bloque-tit">Para consignar</div>'
        + '<div class="pg-banco" style="font-size:12px;color:var(--cx-text-mute)">'
        + 'Los datos bancarios sólo los ve un administrador o la contadora.</div></div>';

    cuerpo='<div class="pg-body">'
      + alertas
      + _pgBloque('Quién es y qué publicó', [
          _pgDato('Creador', p.influencer_nombre),
          _pgDato('Red', p.usuario_red? '@'+p.usuario_red : p.red_social),
          _pgDato('Ciudad', p.ciudad),
          _pgDato('Qué se le paga', p.entregable || p.concepto),
          _pgDato('Fecha de publicación', p.fecha_publicacion || 'sin fecha'),
          (String(p.email||'').trim()
             ? _pgDato('Email', p.email)
             : _pgCargarCorreo(p)),
          _pgDato('Teléfono', p.telefono)
        ])
      + _pgBloque('El cobro', [
          _pgDato('Monto a pagar', _pgMoneda(p.valor)),
          _pgDato('Solicitado', String(p.fecha||'').slice(0,10)),
          _pgDato('Vence', p.vence_pago_at),
          _pgDato('Orden', p.numero_oc)
        ])
      + bloqueBanco
      + '<div style="height:14px"></div>'
      + '<div style="display:flex;gap:8px;flex-wrap:wrap">'
        + (p.numero_oc
            ? '<button onclick="event.stopPropagation();pagarDesdeBandeja('+ix+')" style="background:var(--cx-primary);color:#fff;border:none;border-radius:9px;padding:9px 20px;font-size:13px;font-weight:800;cursor:pointer">Pagar '+_pgMoneda(p.valor)+'</button>'
            : '<span style="font-size:12px;color:var(--cx-text-mute);align-self:center">Este pago no tiene orden asociada · no se puede pagar desde acá</span>')
        + '<button onclick="event.stopPropagation();rechazarDesdeBandeja('+ix+')" style="background:transparent;color:var(--cx-danger-text);border:1px solid var(--cx-danger);border-radius:9px;padding:9px 18px;font-size:13px;font-weight:700;cursor:pointer">Rechazar</button>'
      + '</div>'
    + '</div>';
  }

  return '<div class="pg-row '+(grave?'alerta':'ok')+'">'
    + '<div class="pg-head" onclick="pgToggle('+ix+')">'
      + '<div class="pg-ini">'+_esc(ini)+'</div>'
      + '<div style="flex:1;min-width:0">'
        + '<div class="pg-nom">'+_esc(p.influencer_nombre||'-')+'</div>'
        + '<div class="pg-sub" style="'+(grave?'color:var(--cx-danger-text)':'')+'">'+sub+'</div>'
      + '</div>'
      + '<div class="pg-monto">'+_pgMoneda(p.valor)+'</div>'
      + '<span style="color:var(--cx-text-mute);font-size:12px;white-space:nowrap">'+(abierto?'▲':'▼')+'</span>'
    + '</div>'
    + cuerpo
  + '</div>';
}

function pgToggle(ix){
  // Abiertas por defecto: el toggle sirve para PLEGAR una que ya despaché de vista, no para
  // tener que abrir cada una.
  var p=(window._PG_VIS||[])[ix]; if(!p) return;
  if(window._PG_CERRADOS[p.id]) delete window._PG_CERRADOS[p.id];
  else window._PG_CERRADOS[p.id]=1;
  pintarPagos();
}


function _pgSacarDeLaBandeja(id){
  // Lo pagado/rechazado sale de la bandeja SIN volver a pedir la lista: el servidor ya
  // confirmo, y recargar todo hace perder el scroll y las tarjetas abiertas (Sebastian 6-ago).
  // Los KPI se recalculan desde lo que QUEDA -- si se dejaran como estaban, el total seguiria
  // contando plata que ya se pago, que es peor que la espera (M5: el numero que se muestra es
  // el que decide).
  var js = window._PG_DATA;
  if(!js || !js.pagos){ return false; }
  var antes = js.pagos.length;
  js.pagos = js.pagos.filter(function(x){ return String(x.id) !== String(id); });
  if(js.pagos.length === antes){ return false; }   // no estaba · que el caller recargue
  var res = js.resumen || (js.resumen = {});
  res.n = js.pagos.length;
  res.total = js.pagos.reduce(function(a,x){ return a + (Number(x.valor)||0); }, 0);
  res.con_alerta = js.pagos.filter(function(x){
    return (x.alertas || []).length > 0;
  }).length;
  if(window._PG_CERRADOS) delete window._PG_CERRADOS[id];
  pintarPagos();
  return true;
}

async function rechazarDesdeBandeja(ix){
  // El motivo es OBLIGATORIO: es lo que va a ver Jefferson cuando pregunte por que no le
  // pagaron. Un rechazo sin razon escrita lo deja pidiendo lo mismo la semana que viene.
  var p=(window._PG_VIS||[])[ix]; if(!p) return;
  var motivo=prompt('¿Por qué se rechaza el pago a '+p.influencer_nombre+'?\n(lo va a ver quien lo pidió)','');
  if(motivo===null) return;
  if(String(motivo).trim().length<5){ alert('Escribí el motivo · con eso queda el rastro de por qué no se pagó'); return; }
  try{
    var t=await (await fetch('/api/csrf-token',{credentials:'same-origin'})).json();
    var r=await fetch('/api/centro/pagos-influencers/'+p.id+'/rechazar',{
      method:'POST', credentials:'same-origin',
      headers:{'Content-Type':'application/json','X-CSRF-Token':(t.csrf_token||t.token||'')},
      body: JSON.stringify({motivo:String(motivo).trim()})
    });
    var js=await r.json();
    if(!r.ok||js.error){ alert('No se pudo rechazar: '+(js.error||('HTTP '+r.status))); return; }
    // Sale de la bandeja en el acto · si por lo que sea no estaba en la lista cargada,
    // recien ahi se recarga (nunca dejar la pantalla mostrando algo que ya no existe).
    if(!_pgSacarDeLaBandeja(p.id)){ window._PG_CERRADOS={}; window._PG_DATA=null; await cargarPagos(); }
    cargarDecisiones();
  }catch(e){ alert('Error de red: '+e.message); }
}

async function pagarDesdeBandeja(ix){
  // Mismo endpoint canonico de Compras que usa el resto del sistema: no se abre una segunda
  // via para mover plata (el espejo a egresos, el comprobante y la auditoria viven ahi).
  var p=(window._PG_VIS||[])[ix]; if(!p || !p.numero_oc) return;
  var graves=(p.alertas||[]).filter(function(a){return a.nivel==='alto';});
  var txt = graves.length
    ? 'OJO con este pago:\n\n' + graves.map(function(a){
        var pv=a.pago_previo;
        return '• '+a.mensaje+(pv?('\n   anterior: $'+Number(pv.valor||0).toLocaleString('es-CO')+' del '+String(pv.fecha||'').slice(0,10)+(pv.entregable?' · '+pv.entregable:'')):'');
      }).join('\n') + '\n\n¿Pagar igual a '+p.influencer_nombre+'?'
    : 'Pagar '+_pgMoneda(p.valor)+' a '+p.influencer_nombre+'?';
  // Al pagar se genera el comprobante de egreso (PDF con retenciones) y se le MANDA al creador.
  // Sin correo guardado no sale -- y hasta hoy eso pasaba callado: se pagaba creyendo que el
  // comprobante habia salido. Se avisa ANTES, que es cuando todavia se puede cargar el correo.
  if(!String(p.email||'').trim()){
    txt += '\n\n! ' + p.influencer_nombre + ' no tiene correo guardado: el comprobante de pago '
         + 'NO se le va a enviar. Podes cargarlo en Marketing > Influencers y volver.';
  }
  if(!confirm(txt)) return;
  var ref=prompt('Referencia de la transferencia (numero del banco):','');
  if(ref===null) return;
  if(!String(ref).trim()){ alert('La referencia es obligatoria para poder cruzar el pago con el banco'); return; }
  try{
    var t=await (await fetch('/api/csrf-token',{credentials:'same-origin'})).json();
    var r=await fetch('/api/ordenes-compra/'+encodeURIComponent(p.numero_oc)+'/pagar',{
      method:'PATCH', credentials:'same-origin',
      headers:{'Content-Type':'application/json','X-CSRF-Token':(t.csrf_token||t.token||'')},
      body: JSON.stringify({monto:p.valor||0, medio:'Transferencia',
                            numero_transaccion:String(ref).trim(),
                            observaciones:'Pagado desde Centro de Mando · '+(p.entregable||'')})
    });
    var js=await r.json();
    if(!r.ok||js.error){ alert('No se pudo pagar: '+(js.error||('HTTP '+r.status))); return; }
    // El endpoint YA dice si el comprobante salio y por que no · la pantalla tiraba ese dato a
    // la basura, asi que un pago SIN comprobante se veia igual que uno con comprobante (M100).
    var cp = js.comprobante || {};
    if(cp.email_encolado_a || cp.email_enviado_a){
      // "va en camino", no "llegó": el envío es en segundo plano y puede fallar después.
      // Prometer la entrega hace que nadie revise un comprobante que nunca salió (M100).
      alert('Pagado · comprobante ' + (cp.numero_ce||'') + ' va en camino a '
            + (cp.email_encolado_a || cp.email_enviado_a)
            + ' · si el correo estaba mal escrito el envío falla en silencio: verificalo con el creador.');
    } else if(cp.email_pendiente){
      alert('Pagado' + (cp.numero_ce ? ' · comprobante ' + cp.numero_ce + ' generado' : '')
            + ', pero NO se envio por correo:\n\n' + cp.email_pendiente);
    }
    // Sale de la bandeja en el acto · si por lo que sea no estaba en la lista cargada,
    // recien ahi se recarga (nunca dejar la pantalla mostrando algo que ya no existe).
    if(!_pgSacarDeLaBandeja(p.id)){ window._PG_CERRADOS={}; window._PG_DATA=null; await cargarPagos(); }
    cargarDecisiones();
  }catch(e){ alert('Error de red: '+e.message); }
}

function pintarDecisiones(){
  var cont = document.getElementById('decisiones');
  var lista = _DEC_FILTRO==='todas' ? _DEC : _DEC.filter(function(d){return d.nivel===_DEC_FILTRO;});
  if(_DEC_GRUPO!=='todos') lista = lista.filter(function(d){return (d.grupo||'')===_DEC_GRUPO;});
  if(!lista.length){
    cont.innerHTML = '<div class="empty" style="padding:16px;color:var(--cx-success-text);font-weight:600">✓ Nada urgente que atacar ahora mismo.</div>';
    return;
  }
  // Las decisiones quedan accesibles por INDICE: el boton pasa el indice y no el texto, asi no
  // hay dato del usuario interpolado dentro de un onclick.
  // Y se ordenan POR TEMA (en el orden de _GRP_META, plata primero) y dentro de cada tema por
  // gravedad: asi el indice que ve el boton coincide con lo que se pinta.
  var orden = Object.keys(_GRP_META);
  var peso = {critico:0, atencion:1};
  lista = lista.slice().sort(function(a,b){
    var ga=orden.indexOf(a.grupo||''), gb=orden.indexOf(b.grupo||'');
    if(ga<0) ga=99; if(gb<0) gb=99;
    if(ga!==gb) return ga-gb;
    var pa=(peso[a.nivel]===undefined?9:peso[a.nivel]), pb=(peso[b.nivel]===undefined?9:peso[b.nivel]);
    if(pa!==pb) return pa-pb;
    return (b.valor||0)-(a.valor||0);
  });
  window._DEC_VIS = lista;
  var _grpPrev = null;
  cont.innerHTML = lista.map(function(d, _ix){
    var col = _decColor(d.nivel);
    var gm = _GRP_META[d.grupo] || ['•', d.grupo||''];
    // Encabezado cada vez que cambia el tema (sólo cuando se ven todos mezclados).
    var sep = '';
    if(_DEC_GRUPO==='todos' && d.grupo!==_grpPrev){
      _grpPrev = d.grupo;
      var n = lista.filter(function(z){return z.grupo===d.grupo;}).length;
      sep = '<div class="dec-sep">'+gm[0]+' '+_esc(gm[1])
          + '<span style="font-weight:600;color:var(--cx-text-mute);font-size:11.5px"> · '+n+'</span></div>';
    }
    return sep + _decCard(d, _ix, col, gm);
  }).join('');
}

function _decCard(d, _ix, col, gm){
  {
    // Un pago se RESUELVE aca mismo: el CEO no tiene que irse a otro modulo para ejecutarlo.
    if(d.pago && d.pago.numero_oc){
      return '<div class="dec-card" style="border-left:4px solid '+col+';cursor:default">'+
        '<span class="dec-ico" style="background:'+col+'14;color:'+col+'">'+gm[0]+'</span>'+
        '<div class="dec-body">'+
          '<div class="dec-tit">'+_esc(d.titulo||'-')+'</div>'+
          '<div class="dec-det">'+_esc(d.detalle||'')+'</div>'+
        '</div>'+
        '<button onclick="pagarCreador('+_ix+')" style="background:var(--cx-primary);color:#fff;border:none;border-radius:9px;padding:8px 16px;font-size:13px;font-weight:800;cursor:pointer;white-space:nowrap">Pagar</button>'+
      '</div>';
    }
    return '<a class="dec-card" href="'+_esc(d.accion||'#')+'" style="border-left:4px solid '+col+'">'+
      '<span class="dec-ico" style="background:'+col+'14;color:'+col+'">'+gm[0]+'</span>'+
      '<div class="dec-body">'+
        '<div class="dec-tit">'+_esc(d.titulo||'-')+'</div>'+
        '<div class="dec-det">'+_esc(d.detalle||'')+'</div>'+
      '</div>'+
      '<span class="dec-badge">'+_esc(gm[1])+'</span>'+
      '<span class="dec-arrow"><svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18l6-6-6-6"/></svg></span>'+
    '</a>';
  }
}
var _DEC_RES = {};
function setFiltroDec(f){ _DEC_FILTRO = f; pintarChips(); pintarDecisiones(); }
function setGrupoDec(g){ _DEC_GRUPO = g; pintarChips(); pintarDecisiones(); }
function pintarChips(){
  var res = _DEC_RES || {};
  var c = document.getElementById('dec-chips');
  var defs = [['todas','Todas',(res.total||0)], ['critico','Críticas',(res.critico||0)], ['atencion','Atención',(res.atencion||0)]];
  c.innerHTML = defs.map(function(x){
    var act = _DEC_FILTRO===x[0];
    var col = x[0]==='critico' ? '#dc2626' : (x[0]==='atencion' ? '#d97706' : '#6d28d9');
    return '<button onclick="setFiltroDec(\''+x[0]+'\')" '+
      'style="border:1px solid '+(act?col:'var(--cx-border)')+';background:'+(act?col:'transparent')+';color:'+(act?'#fff':'var(--cx-text-mute)')+';'+
      'border-radius:20px;padding:5px 14px;font-size:12px;font-weight:600;cursor:pointer">'+x[1]+' ('+x[2]+')</button>';
  }).join('');
  pintarGrupos();
}

function pintarGrupos(){
  // Los contadores se cuentan sobre lo que YA filtro la gravedad: si estoy en "Criticas",
  // el chip de Pagos tiene que decir cuantos pagos criticos hay, no el total (M5).
  var cg = document.getElementById('dec-grupos'); if(!cg) return;
  var base = _DEC_FILTRO==='todas' ? _DEC : _DEC.filter(function(d){return d.nivel===_DEC_FILTRO;});
  var cuenta = {};
  base.forEach(function(d){ var g=d.grupo||'otros'; cuenta[g]=(cuenta[g]||0)+1; });
  var defs = [['todos','🎯','Todo', base.length]];
  Object.keys(_GRP_META).forEach(function(g){
    if(cuenta[g]) defs.push([g, _GRP_META[g][0], _GRP_META[g][1], cuenta[g]]);
  });
  // Un tema que hoy no tiene nada NO se muestra: un chip en 0 es ruido.
  cg.innerHTML = defs.map(function(x){
    var act = _DEC_GRUPO===x[0];
    return '<button onclick="setGrupoDec(\''+x[0]+'\')" '+
      'style="border:1px solid '+(act?'var(--cx-primary)':'var(--cx-border)')+';'+
      'background:'+(act?'var(--cx-primary)':'transparent')+';color:'+(act?'#fff':'var(--cx-text-mute)')+';'+
      'border-radius:20px;padding:5px 13px;font-size:12px;font-weight:600;cursor:pointer">'+
      x[1]+' '+x[2]+' <span style="opacity:.75">'+x[3]+'</span></button>';
  }).join('');
}
async function cargarDecisiones(){
  try{
    var d = await fetch('/api/centro/decisiones').then(function(r){return r.json();});
    if(d.error){ document.getElementById('decisiones').innerHTML='<div class="empty" style="padding:14px;color:var(--cx-text-mute)">'+_esc(d.error)+'</div>'; return; }
    _DEC = d.decisiones||[];
    _DEC_RES = d.resumen||{};
    var rz = document.getElementById('dec-resumen');
    rz.textContent = (_DEC_RES.critico||0)+' críticas · '+(_DEC_RES.atencion||0)+' de atención';
    rz.style.color = (_DEC_RES.critico>0) ? '#dc2626' : '#78716c';
    var bd = document.getElementById('cm-badge-dec');
    if(bd){ var nc=(_DEC_RES.critico||0); if(nc>0){ bd.textContent=nc; bd.classList.add('on'); } else { bd.classList.remove('on'); } }
    // El badge de Pagos sale del resumen que ya vino en las decisiones: si sólo se llenara
    // al abrir la pestaña, no avisaria de nada (que es justo para lo que sirve un badge).
    var _rp=_DEC.filter(function(x){return x.ir_a_pagos;})[0];
    var bp=document.getElementById('cm-badge-pagos');
    if(bp){
      var np=(_rp && _rp.n_pagos)||0;
      if(np>0){ bp.textContent=np; bp.classList.add('on'); } else { bp.classList.remove('on'); }
    }
    pintarChips();
    pintarDecisiones();
  }catch(e){ console.error('Decisiones error:', e); }
}

cargar();
cargarDecisiones();
cargarDecisionesCEO();
setInterval(function(){ cargar(); cargarDecisiones(); cargarDecisionesCEO(); }, 60*1000);

// Arranque por hash · `/gerencia` y `/mi-bandeja` redirigen aca con su pestaña, asi que un
// marcador viejo sigue llegando a donde llegaba antes (M120: al mover una ruta enlazada, se
// deja llegando · una URL que muere en la nada es peor que la pantalla vieja).
(function(){
  var h = (location.hash||'').replace('#','');
  if(['dec','pagos','pulso','fin','pend','estr'].indexOf(h) >= 0) showPane(h);
})();
</script>
</body>
</html>
"""
