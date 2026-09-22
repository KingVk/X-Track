@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0.."

set VERSION=1.0.4
set OUTDIR=release
set NAME=X-Track-%VERSION%-windows

echo ========================================
echo  Build X-Track %VERSION% (PyInstaller)
echo ========================================
echo.

python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
  echo [INFO] Installing PyInstaller...
  python -m pip install -U "pyinstaller>=6.0" PyQt6 gallery-dl
  if errorlevel 1 (
    echo [ERROR] Failed to install build deps
    exit /b 1
  )
)

echo [INFO] Cleaning old build/dist...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if not exist "%OUTDIR%" mkdir "%OUTDIR%"

echo [INFO] Running PyInstaller...
python -m PyInstaller --noconfirm build.spec
if errorlevel 1 (
  echo [ERROR] PyInstaller failed
  exit /b 1
)

if not exist "dist\X-Track\X-Track.exe" (
  echo [ERROR] dist\X-Track\X-Track.exe missing
  exit /b 1
)
if not exist "dist\X-Track\gallery-dl.exe" (
  echo [ERROR] dist\X-Track\gallery-dl.exe missing
  exit /b 1
)
if not exist "dist\X-Track\X-Track-Watermark.exe" (
  echo [ERROR] dist\X-Track\X-Track-Watermark.exe missing
  exit /b 1
)

echo %VERSION%> "dist\X-Track\VERSION.txt"
echo [INFO] Writing README-RELEASE.txt...
> "dist\X-Track\README-RELEASE.txt" (
  echo X-Track %VERSION%
  echo.
  echo 1. Unzip this folder anywhere
  echo 2. Double-click X-Track.exe for downloads
  echo 3. Or double-click X-Track-Watermark.exe for batch watermarks
  echo 4. Select Netscape cookies.txt and a download folder in the main app
  echo.
  echo Included:
  echo - X-Track.exe              Main GUI ^(download + inline watermark^)
  echo - X-Track-Watermark.exe    Standalone batch watermark tool
  echo - gallery-dl.exe           Downloader CLI ^(bundled^)
  echo - _internal\resources\fonts          Douyin font
  echo - data\                    created on first run ^(config^)
  echo.
  echo FFmpeg ^(watermarks^):
  echo - Not bundled. On first watermark use, the app can install to %%USERPROFILE%%\.xtrack\bin
  echo - Or install system-wide: winget install Gyan.FFmpeg
  echo.
  echo Notes:
  echo - Keep the whole folder together; do not move only the .exe
  echo - Windows may SmartScreen-block unsigned builds: More info -^> Run anyway
  echo - Antivirus may flag PyInstaller packs; add an exclusion if needed
)

echo [INFO] Creating zip %OUTDIR%\%NAME%.zip ...
powershell -NoProfile -Command "Compress-Archive -Path 'dist\X-Track\*' -DestinationPath '%OUTDIR%\%NAME%.zip' -Force"
if errorlevel 1 (
  echo [ERROR] Zip failed
  exit /b 1
)

echo.
echo [OK] Built:
echo   dist\X-Track\
echo   %OUTDIR%\%NAME%.zip
echo.
echo Upload to GitHub Release ^(do not commit the zip into git^):
echo   gh release create v%VERSION% "%OUTDIR%\%NAME%.zip" --title "X-Track %VERSION%" --notes "Windows onedir build"
exit /b 0
