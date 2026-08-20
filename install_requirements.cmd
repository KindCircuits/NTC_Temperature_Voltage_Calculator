@echo off
setlocal

where py >nul 2>nul
if errorlevel 1 (
    set "PYTHON=python"
) else (
    set "PYTHON=py"
)

%PYTHON% -m pip install --upgrade pip
if errorlevel 1 goto :error

%PYTHON% -m pip install matplotlib
if errorlevel 1 goto :error

echo.
echo Dependencies installed successfully.
pause
exit /b 0

:error
echo.
echo Installation failed. Make sure Python 3 is installed and available on PATH.
pause
exit /b 1
