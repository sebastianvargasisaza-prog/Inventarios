@echo off
echo === Push fix COMPRAS a GitHub ===
cd /d "%~dp0"
git push https://sebastianvargasisaza-prog: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@github.com/sebastianvargasisaza-prog/Inventarios.git main
echo.
if %ERRORLEVEL%==0 (
  echo EXITO - Render desplegara automaticamente en ~2 min
) else (
  echo ERROR - Revisa el mensaje arriba
)
pause
