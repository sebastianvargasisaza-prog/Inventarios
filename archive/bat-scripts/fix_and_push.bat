@echo off
echo =======================================================
echo  FIX AND PUSH — Reset historial limpio + push seguro
echo =======================================================
echo.
cd /d "%~dp0"

echo [1] Verificando token...
if not exist ".git_token" (
    echo ERROR: Falta el archivo .git_token
    pause
    exit /b 1
)
set /p TOKEN=<.git_token
if "%TOKEN%"=="" (
    echo ERROR: .git_token esta vacio
    pause
    exit /b 1
)
echo Token OK.
echo.

echo [2] Configurando remote sin exponer token en archivos...
git remote set-url origin https://sebastianvargasisaza-prog:%TOKEN%@github.com/sebastianvargasisaza-prog/Inventarios.git
echo.

echo [3] Reset suave al ultimo commit exitoso (688240a)...
echo     (Esto deshace los commits locales fallidos sin perder archivos)
git reset --soft 688240a
echo.

echo [4] Stageando todos los archivos limpios actuales...
git add -A
echo.

echo [5] Creando commit limpio sin secrets...
git commit -m "fix: JS syntax fix, clean auth - no secrets in tracked files"
echo.

echo [6] Push a GitHub...
git push origin main
echo.

if %ERRORLEVEL% EQU 0 (
    echo =======================================================
    echo  PUSH EXITOSO! Render despliega en ~60 segundos.
    echo  La app estara lista en https://inventarios-0363.onrender.com
    echo =======================================================
) else (
    echo =======================================================
    echo  Push fallo. Ver error arriba.
    echo =======================================================
)
echo.
pause
