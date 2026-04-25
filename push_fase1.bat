@echo off
echo === FASE 1+2+4+5 — Commit y Push a GitHub ===
cd /d "%~dp0"
echo.
echo [1/3] Staging cambios...
git add api/index.py
echo.
echo [2/3] Commit...
git commit -m "Fase 1+2+4+5: recepcion cuarentena+parciales, alertas vencimiento, home, Proveedores 360, Clientes Maquila 360, Calidad BPM (NC+calibraciones+CC)"
echo.
echo [3/3] Push a GitHub...
git push https://sebastianvargasisaza-prog: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@github.com/sebastianvargasisaza-prog/Inventarios.git main
echo.
if %ERRORLEVEL%==0 (
  echo EXITO - Render desplegara automaticamente en ~2 min
  echo    Verifica en: https://dashboard.render.com
) else (
  echo ERROR - Revisa el mensaje arriba
)
pause
