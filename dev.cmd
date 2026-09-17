@echo off
REM Avvia tutto l'ambiente di sviluppo: Docker se serve, backend e app.
REM Si può lanciare con doppio clic, oppure da PowerShell/CMD.
REM Per fermare tutto: Ctrl+C (o chiudere questa finestra).

cd /d "%~dp0"

set "BASH=C:\Program Files\Git\bin\bash.exe"
if not exist "%BASH%" (
  echo.
  echo   Serve Git per Windows per avviare il progetto.
  echo   Scaricalo da https://git-scm.com/download/win e riprova.
  echo.
  pause
  exit /b 1
)

"%BASH%" -lc "cd \"$(cygpath -u '%CD%')\" && bash scripts/dev.sh"

echo.
echo   Il servizio si e' fermato. Errori sopra, se ce ne sono.
pause
