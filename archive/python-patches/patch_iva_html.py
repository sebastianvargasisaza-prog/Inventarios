# patch_iva_html.py — IVA toggle para modal Revisar en Compras
# Ejecutar: python3 /sessions/magical-great-cray/mnt/Inventarios/patch_iva_html.py

TARGET = '/tmp/inv_p9/api/templates_py/compras_html.py'

with open(TARGET, 'r') as f:
    h = f.read()

# ================================================================
# PATCH B: openRev() con IVA — reemplazar funcion completa
# ================================================================
OLD_B = (
    "function openRev(num,prov,val,obs){\n"
    "  document.getElementById('rev-num').value=num;\n"
    "  document.getElementById('rev-info').innerHTML='<strong>'+num+'</strong><br><span style=\"color:#78716c;\">'+esc(obs||'-')+'</span>';\n"
    "  document.getElementById('rev-val').value=val||'';\n"
    "  document.getElementById('rev-obs').value='';\n"
    "  document.getElementById('rev-fent').value='';\n"
    "  document.getElementById('rev-ibox').style.display='none';\n"
    "  fillProvSelect('rev-prov');\n"
    "  document.getElementById('rev-prov').value=prov;\n"
    "  if(prov) fillProv('rev-prov','rev-ibox');\n"
    "  openModal('m-rev');\n"
    "}"
)

NEW_B = (
    "function openRev(num,prov,val,obs,conIva,valBase){\n"
    "  var oc=OCS.find(function(o){ return o.numero_oc===num; })||{};\n"
    "  var ivaActivo=conIva!==undefined ? !!conIva : !!(oc.con_iva);\n"
    "  var base=valBase!==undefined ? valBase : (oc.valor_sin_iva>0 ? oc.valor_sin_iva : (ivaActivo ? parseFloat(val||0)/1.19 : parseFloat(val||0)));\n"
    "  document.getElementById('rev-num').value=num;\n"
    "  document.getElementById('rev-info').innerHTML='<strong>'+num+'</strong><br><span style=\"color:#78716c;\">'+esc(obs||'-')+'</span>';\n"
    "  document.getElementById('rev-val').value=base>0 ? base.toFixed(0) : (val||'');\n"
    "  document.getElementById('rev-iva-chk').checked=ivaActivo;\n"
    "  document.getElementById('rev-obs').value='';\n"
    "  document.getElementById('rev-fent').value='';\n"
    "  document.getElementById('rev-ibox').style.display='none';\n"
    "  fillProvSelect('rev-prov');\n"
    "  document.getElementById('rev-prov').value=prov;\n"
    "  if(prov) fillProv('rev-prov','rev-ibox');\n"
    "  calcRevIva();\n"
    "  openModal('m-rev');\n"
    "}\n"
    "function calcRevIva(){\n"
    "  var base=parseFloat(document.getElementById('rev-val').value)||0;\n"
    "  var chk=document.getElementById('rev-iva-chk').checked;\n"
    "  var bd=document.getElementById('rev-iva-breakdown');\n"
    "  if(chk && base>0){\n"
    "    var iva=base*0.19;\n"
    "    var tot=base+iva;\n"
    "    var fmt2=function(n){ return '$'+Math.round(n).toLocaleString('es-CO'); };\n"
    "    document.getElementById('rev-iva-sub').textContent=fmt2(base);\n"
    "    document.getElementById('rev-iva-monto').textContent=fmt2(iva);\n"
    "    document.getElementById('rev-iva-total').textContent=fmt2(tot);\n"
    "    bd.style.display='block';\n"
    "  } else {\n"
    "    bd.style.display='none';\n"
    "  }\n"
    "}"
)

assert OLD_B in h, "PATCH B anchor not found"
h = h.replace(OLD_B, NEW_B, 1)
print("PATCH B OK")

with open(TARGET, 'w') as f:
    f.write(h)
print("Done.")
