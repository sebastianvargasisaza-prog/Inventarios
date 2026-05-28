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
})();
