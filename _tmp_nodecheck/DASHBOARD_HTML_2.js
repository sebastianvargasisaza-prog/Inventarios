
// PWA: registrar service worker (Sebastian 30-abr-2026: "y si haz lo del mobil")
if('serviceWorker' in navigator){
  window.addEventListener('load',function(){
    navigator.serviceWorker.register('/static/sw.js').catch(function(e){console.log('SW reg fail',e);});
  });
}
