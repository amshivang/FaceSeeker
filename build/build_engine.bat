@echo off
REM Ponytail: minimal linear build script for engine
echo [Step 1] Changing directory to FaceSeeker.Engine...
cd /d "%~dp0..\FaceSeeker.Engine"

echo [Step 2] Building C extensions with setup_build.py...
python setup_build.py build_ext --inplace

echo [Step 3] Creating dist\engine directory...
if not exist "..\dist\engine" mkdir "..\dist\engine"

echo [Step 4] Copying compiled .pyd files to dist\engine...
copy /y BUILD_SOURCES\*.pyd "..\dist\engine\" >nul 2>&1
copy /y *.pyd "..\dist\engine\" >nul 2>&1

echo [Step 5] Copying python source files to dist\engine...
copy /y BUILD_SOURCES\config.py "..\dist\engine\"
copy /y BUILD_SOURCES\result_models.py "..\dist\engine\"
copy /y BUILD_SOURCES\server.py "..\dist\engine\"
copy /y BUILD_SOURCES\detector.py "..\dist\engine\"
copy /y BUILD_SOURCES\recognizer.py "..\dist\engine\"
copy /y BUILD_SOURCES\pipeline.py "..\dist\engine\"
copy /y BUILD_SOURCES\video_scanner.py "..\dist\engine\"

echo [Step 6] Running PyArmor if installed...
where pyarmor >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo Obfuscating engine python files with PyArmor...
    pyarmor gen -O "..\dist\engine_obf" "..\dist\engine\server.py" "..\dist\engine\config.py" "..\dist\engine\result_models.py" >nul 2>&1
    if exist "..\dist\engine_obf" (
        copy /y "..\dist\engine_obf\*" "..\dist\engine\" >nul 2>&1
        rmdir /s /q "..\dist\engine_obf" >nul 2>&1
    )
) else (
    echo PyArmor not detected in PATH, using direct engine modules.
)

echo Engine build complete