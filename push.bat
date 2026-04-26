@echo off
cd /d "%~dp0"
set /p TOKEN=<.git_token
git remote set-url origin https://sebastianvargasisaza-prog:%TOKEN%@github.com/sebastianvargasisaza-prog/Inventarios.git
git add -A
git commit -m "update %date% %time%"
git push origin main
echo.
echo ================================================
echo  Push completado. Render despliega en ~60 seg.
echo ================================================
pause
