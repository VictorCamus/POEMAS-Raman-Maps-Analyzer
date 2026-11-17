@echo off
setlocal

REM ============================================================
REM MODE D'INSTAL·LACIO
REM ============================================================

set "INSTALL_MODE=usuari"
set "SYNC_ARGS=--no-dev"

if /I "%~1"=="dev" (
    set "INSTALL_MODE=desenvolupador"
    set "SYNC_ARGS=--group dev"
) else if not "%~1"=="" (
    echo Us: %~nx0 [dev]
    echo.
    echo Sense arguments: instal·lacio per a usuaris.
    echo Amb "dev": instal·lacio per a desenvolupadors.
    pause
    exit /b 2
)

echo Mode d'instal·lacio: %INSTALL_MODE%
echo.

echo ====================================
echo   CONFIGURANT ENTORN POEMAS
echo ====================================
echo.

REM ============================================================
REM CONFIGURAR POWERSHELL 5.1
REM ============================================================

set "PSModulePath=%USERPROFILE%\Documents\WindowsPowerShell\Modules;%ProgramFiles%\WindowsPowerShell\Modules;%SystemRoot%\System32\WindowsPowerShell\v1.0\Modules"

REM ============================================================
REM CONFIGURACIO DEL PROJECTE
REM ============================================================

REM Nom del projecte = nom de la carpeta actual
for %%I in ("%CD%") do set "PROJECT_NAME=%%~nxI"

REM Entorn virtual fora de OneDrive
set "VENV_HOME=%USERPROFILE%\.virtualenvs"
set "VENV_PATH=%VENV_HOME%\%PROJECT_NAME%"

REM Fer que uv utilitze esta ruta també en aquesta sessio
set "UV_PROJECT_ENVIRONMENT=%VENV_PATH%"

REM Ruta on instal·larem uv si no esta disponible
set "UV_INSTALL_DIR=%USERPROFILE%\.local\bin"
set "UV=%UV_INSTALL_DIR%\uv.exe"

REM Fer que uv utilitze este entorn per a este projecte
set "UV_PROJECT_ENVIRONMENT=%VENV_PATH%"

REM ============================================================
REM 1. COMPROVAR / INSTAL·LAR UV
REM ============================================================

echo Comprovant uv...
echo.

set "UV_INSTALL_DIR=%USERPROFILE%\.local\bin"
set "UV=%UV_INSTALL_DIR%\uv.exe"

if not exist "%UV%" (
    echo uv no esta instal·lat.
    echo Instal·lant uv...
    echo.

    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$env:UV_INSTALL_DIR='%UV_INSTALL_DIR%'; irm https://astral.sh/uv/install.ps1 | iex"

    if errorlevel 1 (
        echo.
        echo ERROR: No s'ha pogut instal·lar uv.
        pause
        exit /b 1
    )
)

REM Comprovar que podem executar uv
"%UV%" --version >nul 2>&1

if errorlevel 1 (
    echo.
    echo ERROR: No s'ha pogut executar uv.
    echo Ruta buscada:
    echo   %UV%
    pause
    exit /b 1
)

echo uv:
"%UV%" --version
echo.


REM ============================================================
REM 2. COMPROVAR EL PROJECTE
REM ============================================================

if not exist "%CD%\pyproject.toml" (
    echo ERROR: No s'ha trobat pyproject.toml.
    echo.
    echo Este script ha de executar-se des de la carpeta del projecte.
    pause
    exit /b 1
)

if not exist "%CD%\uv.lock" (
    echo ERROR: No s'ha trobat uv.lock.
    echo.
    echo Genera primer el lockfile en el desenvolupament amb:
    echo   uv lock
    echo.
    echo Despres incorpora uv.lock al repositori.
    pause
    exit /b 1
)


REM ============================================================
REM 3. INSTAL·LAR PYTHON 3.14
REM ============================================================

echo Instal·lant / comprovant Python 3.14...
echo.

"%UV%" python install 3.14

if errorlevel 1 (
    echo.
    echo ERROR: No s'ha pogut instal·lar Python 3.14.
    pause
    exit /b 1
)

echo.


REM ============================================================
REM 4. CREAR / SINCRONITZAR L'ENTORN VIRTUAL
REM ============================================================

if not exist "%VENV_HOME%" (
    mkdir "%VENV_HOME%"
    if errorlevel 1 (
        echo.
        echo ERROR: No s'ha pogut crear la carpeta d'entorns virtuals.
        pause
        exit /b 1
    )
)

echo Entorn virtual:
echo   %VENV_PATH%
echo.

echo Sincronitzant dependències del mode %INSTALL_MODE%...
echo.

"%UV%" sync --locked %SYNC_ARGS% --python 3.14

if errorlevel 1 (
    echo.
    echo ERROR: No s'han pogut sincronitzar les dependències.
    echo Comprova que pyproject.toml i uv.lock estiguen actualitzats.
    pause
    exit /b 1
)


REM ============================================================
REM 5. CREAR DRECERA DE L'ESCRIPTORI
REM ============================================================

echo Creant drecera...

for /f "usebackq delims=" %%i in (`
    powershell -NoProfile -Command ^
    "[Environment]::GetFolderPath('Desktop')"
`) do (
    set "DESKTOP=%%i"
)

set "PYTHON=%VENV_PATH%\Scripts\pythonw.exe"
set "TARGET=%CD%\POEMAS.py"
set "SHORTCUT=%DESKTOP%\POEMAS.lnk"
set "ICON=%CD%\POEMAS.ico"


powershell -NoProfile -Command ^
"$s = New-Object -ComObject WScript.Shell; ^
 $l = $s.CreateShortcut('%SHORTCUT%'); ^
 $l.TargetPath = '%PYTHON%'; ^
 $l.Arguments = '\"%TARGET%\"'; ^
 $l.WorkingDirectory = '%CD%'; ^
 $l.IconLocation = $env:ICON; ^
 $l.Save()"

if errorlevel 1 (
    echo.
    echo AVIS: No s'ha pogut crear la drecera.
) else (
    echo Drecera creada correctament.
)

echo.
echo ====================================
echo   ENTORN CREAT CORRECTAMENT
echo ====================================
echo.
echo Projecte:
echo   %CD%
echo.
echo Entorn virtual:
echo   %VENV_PATH%
echo.
echo Python:
echo   %PYTHON%
echo.
echo ====================================
echo.

pause