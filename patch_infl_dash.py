# patch_infl_dash.py — excluir Influencer OCs del dashboard Para Pagar / Para Autorizar
# Los OCs Influencer/Marketing Digital tienen su propio tab con flujo propio.
# Si aparecen en el dashboard, generan duplicidad de botones de pago.

TARGET = '/tmp/inv_p9/api/templates_py/compras_html.py'

with open(TARGET, 'r') as f:
    h = f.read()

# ================================================================
# PATCH: renderDash — filtrar Influencer OCs de autList y pagList
# ================================================================
OLD = (
    "  var autList = OCS.filter(function(o){ return o.estado==='Revisada'; });\n"
    "  var pagList = OCS.filter(function(o){ return o.estado==='Autorizada'; });\n"
    "  var recList = OCS.filter(function(o){ return o.estado==='Pagada'; });"
)

NEW = (
    "  var _noInfl=function(o){ return (o.categoria||'').indexOf('Influencer')<0; };\n"
    "  var autList = OCS.filter(function(o){ return o.estado==='Revisada' && _noInfl(o); });\n"
    "  var pagList = OCS.filter(function(o){ return o.estado==='Autorizada' && _noInfl(o); });\n"
    "  var recList = OCS.filter(function(o){ return o.estado==='Pagada' && _noInfl(o); });"
)

assert OLD in h, "PATCH anchor not found"
h = h.replace(OLD, NEW, 1)
print("PATCH OK")

with open(TARGET, 'w') as f:
    f.write(h)
print("Done.")
