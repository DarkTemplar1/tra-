@echo off

REM ============================================================
REM   PriceBot - build.bat (prosty, na GOTO + sprawdzanie dostepu)
REM ============================================================

set APP_NAME=PriceBot
set ENTRY=main.py
set VENV=.venv
set DIST_DIR=dist
set BUILD_DIR=build
set LOGFILE=build_debug.log

set VENV_DIR=%CD%\%VENV%

echo =========================================================== > "%LOGFILE%"
echo  [%DATE% %TIME%] START BUILD >> "%LOGFILE%"
echo =========================================================== >> "%LOGFILE%"

echo.
echo [DBG] Katalog roboczy: %CD%
echo [DBG] APP_NAME     = %APP_NAME%
echo [DBG] ENTRY        = %ENTRY%
echo [DBG] VENV         = %VENV%
echo [DBG] VENV_DIR     = %VENV_DIR%
echo [DBG] DIST_DIR     = %DIST_DIR%
echo [DBG] BUILD_DIR    = %BUILD_DIR%
echo [DBG] LOGFILE      = %LOGFILE%
echo [DBG] Szukam programu 'py' i 'python'...
where py      >> "%LOGFILE%" 2>&1
where python  >> "%LOGFILE%" 2>&1

REM ------------------------------------------------------------
REM STEP 0/6 – sprawdzanie plikow i dostepu
REM ------------------------------------------------------------

echo.
echo [STEP] 0/6 - Sprawdzanie dostepu do plikow

REM sprawdz, czy istnieje ENTRY
if not exist "%ENTRY%" goto ERR_NO_ENTRY

REM test odczytu ENTRY
echo [DBG] Test odczytu pliku wejsciowego: %ENTRY% >> "%LOGFILE%"
type "%ENTRY%" >nul 2>>"%LOGFILE%"
if errorlevel 1 goto ERR_NO_READ_ENTRY

REM jesli istnieje requirements.txt – test odczytu
if exist "requirements.txt" goto HAS_REQ
echo [DBG] Plik requirements.txt nie istnieje (krok opcjonalny). >> "%LOGFILE%"
goto TEST_WRITE

:HAS_REQ
echo [DBG] Test odczytu requirements.txt >> "%LOGFILE%"
type "requirements.txt" >nul 2>>"%LOGFILE%"
if errorlevel 1 goto ERR_NO_READ_REQ

:TEST_WRITE
REM test zapisu w katalogu roboczym
echo [DBG] Test zapisu w katalogu roboczym: %CD% >> "%LOGFILE%"
echo test> "write_test.tmp" 2>>"%LOGFILE%"
if errorlevel 1 goto ERR_NO_WRITE
del "write_test.tmp" >nul 2>&1

REM OK, dalej
goto STEP1


REM ------------------------------------------------------------
REM STEP 1/6 – czyszczenie katalogow
REM ------------------------------------------------------------
:STEP1
echo.
echo [STEP] 1/6 - Czyszczenie katalogow %DIST_DIR% i %BUILD_DIR%
echo [DBG] Usuwam stare katalogi (jesli istnieja)... >> "%LOGFILE%"

if exist "%DIST_DIR%" (
  echo [DBG] Kasuje katalog: %DIST_DIR% >> "%LOGFILE%"
  rmdir /s /q "%DIST_DIR%" >> "%LOGFILE%" 2>&1
) else (
  echo [DBG] Katalog %DIST_DIR% nie istnieje - OK. >> "%LOGFILE%"
)

if exist "%BUILD_DIR%" (
  echo [DBG] Kasuje katalog: %BUILD_DIR% >> "%LOGFILE%"
  rmdir /s /q "%BUILD_DIR%" >> "%LOGFILE%" 2>&1
) else (
  echo [DBG] Katalog %BUILD_DIR% nie istnieje - OK. >> "%LOGFILE%"
)

goto STEP2


REM ------------------------------------------------------------
REM STEP 2/6 – venv
REM ------------------------------------------------------------
:STEP2
echo.
echo [STEP] 2/6 - Sprawdzanie / tworzenie wirtualnego srodowiska
echo [DBG] Sprawdzam: %VENV_DIR%\Scripts\python.exe >> "%LOGFILE%"

if exist "%VENV_DIR%\Scripts\python.exe" goto HAVE_VENV

echo [DBG] Brak %VENV_DIR%\Scripts\python.exe - tworze nowe venv... >> "%LOGFILE%"
echo [DBG] Komenda: py -3 -m venv "%VENV_DIR%" >> "%LOGFILE%"
py -3 -m venv "%VENV_DIR%" >> "%LOGFILE%" 2>&1
if errorlevel 1 goto ERR_VENV_CREATE

:HAVE_VENV
if not exist "%VENV_DIR%\Scripts\python.exe" goto ERR_VENV_NO_PY
echo [DBG] Wirtualne srodowisko gotowe. >> "%LOGFILE%"

goto STEP3


REM ------------------------------------------------------------
REM STEP 3/6 – aktywacja venv
REM ------------------------------------------------------------
:STEP3
echo.
echo [STEP] 3/6 - Aktywacja wirtualnego srodowiska

if not exist "%VENV_DIR%\Scripts\activate.bat" goto ERR_VENV_NO_ACTIVATE

echo [DBG] call "%VENV_DIR%\Scripts\activate" >> "%LOGFILE%"
call "%VENV_DIR%\Scripts\activate"
if errorlevel 1 goto ERR_VENV_ACTIVATE

goto STEP4


REM ------------------------------------------------------------
REM STEP 4/6 – pip + zaleznosci
REM ------------------------------------------------------------
:STEP4
echo.
echo [STEP] 4/6 - Instalacja zaleznosci (pip)
set PYTHONUNBUFFERED=1

echo [DBG] Aktualizacja pip >> "%LOGFILE%"
python -m pip install --upgrade pip >> "%LOGFILE%" 2>&1
if errorlevel 1 goto ERR_PIP_UPGRADE

if exist "requirements.txt" (
  echo [DBG] Instalacja z requirements.txt >> "%LOGFILE%"
  pip install -r requirements.txt >> "%LOGFILE%" 2>&1
  if errorlevel 1 goto ERR_PIP_REQ
) else (
  echo [WARN] Brak pliku requirements.txt - pomijam ten krok. >> "%LOGFILE%"
)

echo [DBG] Instalacja pyinstaller >> "%LOGFILE%"
pip install pyinstaller >> "%LOGFILE%" 2>&1
if errorlevel 1 goto ERR_PIP_PYINSTALLER

goto STEP5


REM ------------------------------------------------------------
REM STEP 5/6 – PyInstaller
REM ------------------------------------------------------------
:STEP5
echo.
echo [STEP] 5/6 - Uruchamianie PyInstaller
echo [DBG] Sprawdzam wersje pyinstaller: >> "%LOGFILE%"
pyinstaller --version >> "%LOGFILE%" 2>&1

echo [DBG] Komenda PyInstaller: >> "%LOGFILE%"
echo pyinstaller --noconfirm --name "%APP_NAME%" --onefile --windowed --hidden-import=tkinter --hidden-import=lxml "%ENTRY%" >> "%LOGFILE%"

pyinstaller --noconfirm --name "%APP_NAME%" --onefile --windowed --hidden-import=tkinter --hidden-import=lxml "%ENTRY%" >> "%LOGFILE%" 2>&1

set BUILD_ERR=%ERRORLEVEL%
echo [DBG] BUILD_ERR=%BUILD_ERR% >> "%LOGFILE%"
if not "%BUILD_ERR%"=="0" goto ERR_BUILD

goto STEP6


REM ------------------------------------------------------------
REM STEP 6/6 – sprawdzenie EXE
REM ------------------------------------------------------------
:STEP6
echo.
echo [STEP] 6/6 - Sprawdzanie wyniku budowania

if exist "%DIST_DIR%\%APP_NAME%.exe" (
  echo [OK] Zbudowano: %DIST_DIR%\%APP_NAME%.exe
  echo [OK] EXE istnieje w katalogu: %DIST_DIR% >> "%LOGFILE%"
  echo Uruchom i w GUI w sekcji "Miejsce tworzenia plikow i folderow" kliknij "Przygotowanie Aplikacji".
  goto DONE
)

echo [ERR] Nie znaleziono pliku EXE w %DIST_DIR%.
echo [ERR] Plik %DIST_DIR%\%APP_NAME%.exe nie istnieje - cos blokuje zapis (antywirus / uprawnienia?). >> "%LOGFILE%"
if exist "%DIST_DIR%" (
  dir "%DIST_DIR%" >> "%LOGFILE%" 2>&1
) else (
  echo [DBG] Katalog %DIST_DIR% w ogole nie zostal utworzony. >> "%LOGFILE%"
)
exit /b 41


REM ------------------------------------------------------------
REM BLOK BLEDÓW – CZYTELNE KOMUNIKATY
REM ------------------------------------------------------------
:ERR_NO_ENTRY
echo [ERR] Nie znaleziono pliku wejsciowego: %ENTRY%
echo [ERR] Nie znaleziono pliku wejsciowego: %ENTRY% >> "%LOGFILE%"
exit /b 10

:ERR_NO_READ_ENTRY
echo [ERR] Brak dostepu do odczytu pliku: %ENTRY%
echo [ERR] Brak dostepu do odczytu pliku: %ENTRY% >> "%LOGFILE%"
exit /b 11

:ERR_NO_READ_REQ
echo [ERR] Brak dostepu do odczytu pliku: requirements.txt
echo [ERR] Brak dostepu do odczytu pliku: requirements.txt >> "%LOGFILE%"
exit /b 12

:ERR_NO_WRITE
echo [ERR] Brak uprawnien do zapisu w katalogu roboczym: %CD%
echo [ERR] Nie udalo sie utworzyc pliku write_test.tmp >> "%LOGFILE%"
exit /b 13

:ERR_VENV_CREATE
echo [ERR] Nie udalo sie utworzyc wirtualnego srodowiska: %VENV_DIR%
echo [ERR] Py -3 -m venv zwrocil blad. >> "%LOGFILE%"
exit /b 20

:ERR_VENV_NO_PY
echo [ERR] Po tworzeniu nadal brak: %VENV_DIR%\Scripts\python.exe
echo [ERR] Prawdopodobnie antywirus lub uprawnienia blokuja pliki w venv. >> "%LOGFILE%"
exit /b 21

:ERR_VENV_NO_ACTIVATE
echo [ERR] Brak pliku aktywacji: %VENV_DIR%\Scripts\activate.bat
echo [ERR] venv wydaje sie byc uszkodzony. >> "%LOGFILE%"
exit /b 22

:ERR_VENV_ACTIVATE
echo [ERR] Nie udalo sie aktywowac venv.
echo [ERR] activate zwrocil blad. >> "%LOGFILE%"
exit /b 23

:ERR_PIP_UPGRADE
echo [ERR] Nie udalo sie zaktualizowac pip.
echo [ERR] python -m pip install --upgrade pip zwrocil blad. >> "%LOGFILE%"
exit /b 30

:ERR_PIP_REQ
echo [ERR] Bledy podczas instalacji pakietow z requirements.txt.
echo [ERR] pip install -r requirements.txt zwrocil blad. >> "%LOGFILE%"
exit /b 31

:ERR_PIP_PYINSTALLER
echo [ERR] Nie udalo sie zainstalowac pyinstaller.
echo [ERR] pip install pyinstaller zwrocil blad. >> "%LOGFILE%"
exit /b 32

:ERR_BUILD
echo [ERR] PyInstaller zakonczyl sie bledem, errorlevel=%BUILD_ERR%.
echo [ERR] Sprawdz szczegoly w pliku logu: %LOGFILE% >> "%LOGFILE%"
exit /b 40


REM ------------------------------------------------------------
:DONE
echo.
echo [DONE] Budowanie zakonczone. Szczegoly znajdziesz w: %LOGFILE%
exit /b 0
