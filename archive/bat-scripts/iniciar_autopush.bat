@echo off
echo Iniciando AutoPush en background...
start "AutoPush-Inventarios" /min python "%~dp0autopush.py"
echo.
echo AutoPush corriendo. Ahora cada cambio que haga Claude
echo se sube a GitHub automaticamente en maximo 15 segundos.
echo.
echo Para detenerlo: cierra la ventana "AutoPush-Inventarios"
echo Para ver el log: abre autopush.log en la carpeta
echo.
pause
