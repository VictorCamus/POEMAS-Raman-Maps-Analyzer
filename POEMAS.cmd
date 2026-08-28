@echo off

set VENV_HOME=%USERPROFILE%\.virtualenvs
for %%I in ("%CD%") do set PROJECT_NAME=%%~nxI

"%VENV_HOME%\%PROJECT_NAME%\Scripts\python" POEMAS.py
pause