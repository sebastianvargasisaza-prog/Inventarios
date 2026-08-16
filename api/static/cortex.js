/* EOS Cortex JS · helpers globales · 28-may-2026
 * Captura JS errors globales y los muestra en overlay (cx-error +
 * data-cx-error) sin bloquear la pantalla. El loader CSS-only fue
 * ELIMINADO (tapaba la pantalla 7.6s y bloqueaba clicks).
 *
 * Templates que cargan cortex.css también cargan este script (via after_request).
 */
(function () {
  // cxReady se mantiene como no-op compatible por si algún código lo invoca.
  window.cxReady = function () {
    try { document.body.classList.add('cx-ready'); } catch (_) {}
  };

  // Capture global errors y mostrar overlay (NO bloquea interacción)
  window.addEventListener('error', function (e) {
    try {
      var msg = (e && e.message ? e.message : 'error desconocido');
      var src = (e && e.filename ? (' [' + e.filename.split('/').pop() + ':' + e.lineno + ']') : '');
      document.body.setAttribute('data-cx-error', (msg + src).slice(0, 240));
      document.body.classList.add('cx-error');
    } catch (_) {}
  }, true);

  window.addEventListener('unhandledrejection', function (e) {
    try {
      var msg = '';
      if (e && e.reason) {
        msg = (typeof e.reason === 'string') ? e.reason : (e.reason.message || String(e.reason));
      }
      document.body.setAttribute('data-cx-error', ('Promise: ' + msg).slice(0, 240));
      document.body.classList.add('cx-error');
    } catch (_) {}
  });

  // Helper público: ocultar/mostrar error manualmente
  window.cxClearError = function () {
    try { document.body.classList.remove('cx-error'); document.body.removeAttribute('data-cx-error'); } catch (_) {}
  };

  /* ── Un refresco automático no trabaja contra una pestaña que nadie mira ────
   * Sebastián 15-ago-2026: *"están lentos en cada cosa, cargando y mostrando"*.
   *
   * EOS se usa con varias pestañas abiertas, y 18 pantallas se refrescan solas
   * cada 20-300 segundos (producción y dashboard cada 20s, la campana cada 25s,
   * compras y el operario cada 30s, gerencia con cinco de 300s). Ninguna miraba
   * si la pestaña estaba visible, así que cuatro pestañas abiertas eran cuatro
   * veces el tráfico contra TRES workers - y cada request lento retiene uno de
   * los tres (M43/M91).
   *
   * Se arregla en UN solo lugar en vez de en dieciocho archivos (M3): se envuelve
   * `setInterval` y, para los intervalos LARGOS, se saltea el tick cuando la
   * pestaña está oculta. El corte en 15 segundos es lo que separa un refresco de
   * datos de una animación o un reloj: por debajo no se toca nada.
   *
   * Al volver a la pestaña se ejecuta UNA vez enseguida: si sólo se saltearan los
   * ticks, el usuario volvería a una pantalla con datos viejos hasta el próximo
   * tick, que en gerencia son cinco minutos.
   */
  (function () {
    var UMBRAL_MS = 15000;      // por debajo: animaciones, relojes → no se tocan
    var nativoSet = window.setInterval;
    var nativoClear = window.clearInterval;
    var pendientes = {};        // id → función, de los que se saltearon estando oculta

    window.setInterval = function (fn, ms) {
      var args = Array.prototype.slice.call(arguments, 2);
      if (typeof fn !== 'function' || !(ms >= UMBRAL_MS)) {
        return nativoSet.apply(window, arguments);
      }
      var id = null;
      var envuelto = function () {
        if (document.hidden) {  // nadie está mirando: no se gasta un worker
          if (id !== null) { pendientes[id] = envuelto; }
          return;
        }
        return fn.apply(this, args);
      };
      id = nativoSet.call(window, envuelto, ms);
      return id;
    };

    // Un intervalo CANCELADO no puede volver a correr al enfocar la pestaña: sin
    // esto, el poller de un modal ya cerrado se ejecutaría una vez más contra un
    // DOM que ya no existe (M112: el disparador y su destino se retiran juntos).
    window.clearInterval = function (id) {
      try { delete pendientes[id]; } catch (_) {}
      return nativoClear.apply(window, arguments);
    };

    document.addEventListener('visibilitychange', function () {
      if (document.hidden) { return; }
      var cola = pendientes;
      pendientes = {};
      for (var k in cola) {
        if (Object.prototype.hasOwnProperty.call(cola, k)) {
          try { cola[k](); } catch (_) {}
        }
      }
    });
  })();

  // Sebastián 30-jun · el scroll del mouse sobre un <input type="number"> ENFOCADO le cambiaba el valor sin querer
  // (bug UX clásico que hizo cambiar cantidades de producción). Prevenir: cancelar el wheel mientras el number
  // tiene foco (el valor deja de cambiar; para scrollear la página, el usuario mueve el mouse fuera del campo).
  try {
    document.addEventListener('wheel', function (e) {
      var el = e.target;
      if (el && el.tagName === 'INPUT' && el.type === 'number' && el === document.activeElement) {
        e.preventDefault();
      }
    }, { passive: false });
  } catch (_) {}
})();
