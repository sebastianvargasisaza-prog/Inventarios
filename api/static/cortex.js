/* EOS Cortex JS · helpers globales · 27-may-2026 PM
 * Aplica cx-ready (oculta loader) cuando DOM listo + captura JS errors
 * y los muestra en overlay (cx-error + data-cx-error). Soluciona el
 * "pantalla queda en blanco" cuando algún script inline falla.
 *
 * Templates que cargan cortex.css también deben cargar este script.
 */
(function () {
  function cxReady() {
    try { document.body.classList.add('cx-ready'); } catch (_) {}
  }
  if (document.readyState === 'complete' || document.readyState === 'interactive') {
    setTimeout(cxReady, 0);
  } else {
    document.addEventListener('DOMContentLoaded', cxReady);
  }
  // Failsafe extra: si DOMContentLoaded tarda, ocultar loader en 6s
  setTimeout(cxReady, 6000);

  // Capture global errors y mostrar overlay
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
  window.cxReady = cxReady;
})();
