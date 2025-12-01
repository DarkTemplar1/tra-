@echo off
REM ========================================================
REM        BUILD PriceBot.exe
REM ========================================================

setlocal

set APP_NAME=PriceBot
set SPEC_FILE=PriceBot.spec

echo ========================================
echo        BUILDING %APP_NAME%.exe
echo ========================================

REM ---- Ścieżka do Pythona z bieżącego folderu ----
set "SCRIPT_DIR=%~dp0"
if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%SCRIPT_DIR%.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)
echo [INFO] Używany Python: %PYTHON_EXE%

REM ---- Sprzątanie poprzednich buildów ----
if exist "%SCRIPT_DIR%build" rd /s /q "%SCRIPT_DIR%build"
if exist "%SCRIPT_DIR%dist" rd /s /q "%SCRIPT_DIR%dist"

echo [INFO] Tworzenie EXE na podstawie %SPEC_FILE%. Log: build_debug.log
"%PYTHON_EXE%" -m PyInstaller ^
    --noconfirm ^
    "%SPEC_FILE%" > build_debug.log 2>&1

echo ---------------------------------------------------------------
if exist "%SCRIPT_DIR%dist\%APP_NAME%.exe" (
    echo [OK] GOTOWE: dist\%APP_NAME%.exe
) else (
    echo [BŁĄD] Nie znaleziono dist\%APP_NAME%.exe
    echo       Sprawdź build_debug.log
)
echo ---------------------------------------------------------------

pause
endlocal
