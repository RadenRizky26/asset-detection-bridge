@echo off
REM Start the AutoCAD Bridge Service (Windows, AutoCAD must be open with target DWG).
REM Usage: start-bridge.bat [port]
setlocal
set PORT=%1
if "%PORT%"=="" set PORT=8765

cd /d "%~dp0autocad-bridge\src"

if not defined AUTOCAD_BRIDGE_PORT set AUTOCAD_BRIDGE_PORT=%PORT%

echo ==============================================
echo  AutoCAD Bridge Service  (port %AUTOCAD_BRIDGE_PORT%)
echo  Make sure AutoCAD is running + target DWG open.
echo  Health: http://127.0.0.1:%AUTOCAD_BRIDGE_PORT%/health
echo ==============================================

python -c "import pdf_markup_core" 2>nul || (
  echo Installing pdf-markup-core (editable)...
  pip install -e "%~dp0lib\pdf-markup-core"
)
python -c "import fastapi, uvicorn" 2>nul || (
  echo Installing bridge dependencies...
  pip install -e "%~dp0autocad-bridge"
)

uvicorn bridge_main:app --host 127.0.0.1 --port %AUTOCAD_BRIDGE_PORT%
