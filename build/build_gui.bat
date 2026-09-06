@echo off
REM Ponytail: minimal linear build script for C# GUI and dist bundling
setlocal

echo [Step 1] Publishing FaceSeeker.GUI (Release win-x64 self-contained)...
set DOTNET_EXE=dotnet
if exist "%LOCALAPPDATA%\Microsoft\dotnet\dotnet.exe" (
    set DOTNET_EXE="%LOCALAPPDATA%\Microsoft\dotnet\dotnet.exe"
)

call %DOTNET_EXE% publish "%~dp0..\FaceSeeker.GUI\FaceSeeker.GUI.csproj" -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true -o "%~dp0..\dist\publish_tmp"
if %ERRORLEVEL% neq 0 (
    echo dotnet publish failed.
    exit /b %ERRORLEVEL%
)

echo [Step 2] Checking for ConfuserEx...
where Confuser.CLI >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo Obfuscating FaceSeeker.exe with ConfuserEx...
    Confuser.CLI "%~dp0..\dist\publish_tmp\FaceSeeker.exe" >nul 2>&1
) else (
    echo ConfuserEx not found in PATH, skipping IL obfuscation.
)

echo [Step 3] Copying executable to dist/...
copy /y "%~dp0..\dist\publish_tmp\FaceSeeker.exe" "%~dp0..\dist\" >nul 2>&1
xcopy /e /y /i "%~dp0..\dist\publish_tmp\*" "%~dp0..\dist\" >nul 2>&1
rmdir /s /q "%~dp0..\dist\publish_tmp" >nul 2>&1

echo [Step 4] Ensuring engine is built and copied to dist/engine/...
call "%~dp0build_engine.bat"

echo [Step 5] Copying models to dist/models/...
if not exist "%~dp0..\dist\models" mkdir "%~dp0..\dist\models"
copy /y "%~dp0..\models\*.onnx" "%~dp0..\dist\models\" >nul 2>&1

echo [Step 6] Setting up python runtime if available in dist/python/...
if exist "%~dp0..\python" (
    xcopy /e /y /i "%~dp0..\python\*" "%~dp0..\dist\python\" >nul 2>&1
) else (
    echo Note: dist/python/ can be populated with python-embed runtime for portable deployment.
)

echo Full build complete ? dist/ is ready to ship
endlocal