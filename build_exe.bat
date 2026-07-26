@echo off
setlocal
cd /d "%~dp0"

call ".venv\Scripts\activate.bat"
set PYTHONPATH=%cd%\src

echo Building Viewing.exe ...
pyinstaller --noconfirm --clean build_exe.spec
if errorlevel 1 (
  echo Build failed.
  exit /b 1
)

:: Copy .env next to exe if present (local secrets for testing)
if exist ".env" copy /Y ".env" "dist\.env" >nul

echo.
echo Done: dist\Viewing.exe
endlocal
