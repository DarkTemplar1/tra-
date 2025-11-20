@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM ===================== CONFIG =======================
set "APP_NAME=PriceBot"
set "MAIN_FILE=main.py"
set "LOG=build_debug.log"
REM =====================================================

REM ===== Lokacja skryptu (niezależna od użytkownika Windows) =====
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo ========================================
echo        BUILDING %APP_NAME%.exe
echo ========================================

REM ===== Szukamy Pythona w .venv, potem globalnie =====
if exist "%SCRIPT_DIR%\.venv\Scripts\python.exe" (
    set "PYEXE=%SCRIPT_DIR%\.venv\Scripts\python.exe"
) else (
    for /f "delims=" %%P in ('where python 2^>nul') do set "PYEXE=%%P"
)

if not defined PYEXE (
    echo [ERROR] Nie znaleziono Python. Zainstaluj Python 3.8+ i dodaj do PATH.
    echo [ERROR] Budowanie przerwane.
    pause
    exit /b 1
)

echo [INFO] Używany Python: %PYEXE%

REM ===== Sprawdzamy PyInstaller i instalujemy jeśli go nie ma =====
echo [INFO] Sprawdzanie PyInstaller...
"%PYEXE%" -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo [INFO] Instalacja PyInstaller...
    "%PYEXE%" -m pip install pyinstaller >> "%LOG%" 2>&1
)

REM ===== Usuwamy poprzednie buildy =====
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "%APP_NAME%.spec" del "%APP_NAME%.spec"

REM =================== WYKONANIE BUILD ============================
echo [INFO] Tworzenie EXE. Log: %LOG%
echo ---------------------------------------------------------------

"%PYEXE%" -m PyInstaller "%MAIN_FILE%" ^
    --onefile ^
    --windowed ^
    --clean ^
    --name="%APP_NAME%" ^
    --add-data "%SCRIPT_DIR%:." ^
    >> "%LOG%" 2>&1

REM =================== SPRAWDZANIE ================================
if errorlevel 1 (
    echo [ERROR] Kompilacja nie powiodła się. Sprawdź plik: %LOG%
    pause
    exit /b 1
)

echo.
echo [OK] GOTOWE! Utworzono:
echo    dist\%APP_NAME%.exe
echo ---------------------------------------------------------------
pause
exit /b 0
