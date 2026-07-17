
// Asistente conversacional Claude · contexto planta
var _AI_HIST = [];
function aiTogglePanel(){
  var p = document.getElementById('ai-panel');
  var open = p.style.display !== 'flex';
  p.style.display = open ? 'flex' : 'none';
  if(open && _AI_HIST.length === 0){
    aiAddMsg('assistant', '👋 Hola, soy el asistente de tu planta. Conozco las cadencias, capacidades, equipos, producciones y MP en tiempo real. Pregúntame:\n\n• "¿Cuánto Suero AH puedo producir esta semana?"\n• "¿Por qué hay alerta crítica?"\n• "¿Qué cadencia tiene Vit C?"');
  }
}
function aiAddMsg(role, txt){
  var box = document.getElementById('ai-messages');
  var bg = role==='user' ? '#7c3aed' : '#fff';
  var col = role==='user' ? '#fff' : '#0f172a';
  var border = role==='user' ? 'none' : '1px solid #e5e7eb';
  var align = role==='user' ? 'flex-end' : 'flex-start';
  var div = document.createElement('div');
  div.style.cssText = 'display:flex;justify-content:'+align+';margin-bottom:8px';
  div.innerHTML = '<div style="background:'+bg+';color:'+col+';border:'+border+';padding:9px 12px;border-radius:12px;max-width:85%;white-space:pre-wrap;line-height:1.45;font-size:13px">'+_escHTML(txt)+'</div>';
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}
async function aiEnviar(){
  var input = document.getElementById('ai-input');
  var pregunta = input.value.trim();
  if(!pregunta) return;
  input.value = '';
  aiAddMsg('user', pregunta);
  _AI_HIST.push({role:'user', content:pregunta});
  // Loading
  var box = document.getElementById('ai-messages');
  var loading = document.createElement('div');
  loading.id = 'ai-loading';
  loading.style.cssText = 'color:#94a3b8;font-size:11px;padding:6px 10px';
  loading.textContent = 'Pensando...';
  box.appendChild(loading);
  box.scrollTop = box.scrollHeight;
  document.getElementById('ai-send').disabled = true;
  try {
    var r = await fetch('/api/asistente/planta', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({pregunta: pregunta, historial: _AI_HIST.slice(-10)})
    });
    var d = await r.json();
    document.getElementById('ai-loading')?.remove();
    var resp = d.respuesta || d.error || 'No pude responder.';
    aiAddMsg('assistant', resp);
    if(d.respuesta) _AI_HIST.push({role:'assistant', content:d.respuesta});
  } catch(e){
    document.getElementById('ai-loading')?.remove();
    aiAddMsg('assistant', '⚠ Error de red: '+e.message);
  }
  document.getElementById('ai-send').disabled = false;
  input.focus();
}
function aiQuick(p){
  document.getElementById('ai-input').value = p;
  aiEnviar();
}
