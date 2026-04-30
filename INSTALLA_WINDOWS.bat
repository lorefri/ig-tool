@echo off
chcp 65001 >nul
echo.
echo ============================================
echo   WD International University - OutreachBot
echo ============================================
echo.

:: Controlla se Python è installato
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRORE] Python non trovato!
    echo Scarica Python da: https://www.python.org/downloads/
    echo Assicurati di spuntare "Add Python to PATH" durante l'installazione.
    pause
    exit /b 1
)

echo [OK] Python trovato.
echo.
echo Installazione dipendenze in corso...
pip install -r requirements.txt

if errorlevel 1 (
    echo [ERRORE] Installazione fallita. Riprova come Amministratore.
    pause
    exit /b 1
)

echo.
echo [OK] Dipendenze installate.
echo.
echo ============================================
echo   Avvio app...
echo ============================================
echo.
echo L'app si aprirà nel browser. Per fermarla: CTRL+C
echo.
streamlit run app.py

pause
