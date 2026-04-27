@echo off
echo === Fix COMPRAS_HTML — push a GitHub ===
cd /d "%~dp0"
git add api/index.py
git commit -m "fix: COMPRAS_HTML - errores JS resueltos (syntax error addRow + 6 onclick con quoting roto)"
git push
echo.
echo === Listo. Render desplegara automaticamente. ===
pause
