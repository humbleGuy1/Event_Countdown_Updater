@echo off
setlocal EnableExtensions

set "ROOT=%~dp0"
cd /d "%ROOT%"

set "CONFIG=%~1"
if "%CONFIG%"=="" set "CONFIG=config.toml"

if /I "%CONFIG%"=="--help" goto :usage
if /I "%CONFIG%"=="-h" goto :usage
if /I "%CONFIG%"=="/?" goto :usage

echo Event Countdown Updater
echo Project: %CD%
echo.

if not exist "%CONFIG%" (
    echo Config file was not found: "%CONFIG%"
    if exist "config.example.toml" (
        echo.
        set /p CREATE_CONFIG=Create "%CONFIG%" from config.example.toml now? [y/N]: 
        if /I "%CREATE_CONFIG%"=="Y" (
            copy "config.example.toml" "%CONFIG%" >nul
            if errorlevel 1 goto :copy_failed
            echo Created "%CONFIG%".
            echo Fill event, universe, place, title, and icon settings before live use.
            echo.
        ) else (
            echo Copy config.example.toml to config.toml and fill the required values.
            goto :finish_error
        )
    ) else (
        goto :finish_error
    )
)

call :find_python
if errorlevel 1 goto :finish_error

if defined PYTHONPATH (
    set "PYTHONPATH=%ROOT%src;%PYTHONPATH%"
) else (
    set "PYTHONPATH=%ROOT%src"
)

echo Config: %CONFIG%
echo.
echo Choose action:
echo   1. status
echo   2. apply dry-run
echo   3. apply live
echo   4. watch dry-run
echo   5. watch live
echo.

set "ACTION="
set /p ACTION=Action [1]: 
if "%ACTION%"=="" set "ACTION=1"

set "COMMAND="
set "LIVE_FLAG="
set "WATCH_INTERVAL="
if "%ACTION%"=="1" set "COMMAND=status"
if "%ACTION%"=="2" set "COMMAND=apply"
if "%ACTION%"=="3" (
    set "COMMAND=apply"
    set "LIVE_FLAG=--live"
)
if "%ACTION%"=="4" set "COMMAND=watch"
if "%ACTION%"=="5" (
    set "COMMAND=watch"
    set "LIVE_FLAG=--live"
)

if not defined COMMAND (
    echo Unknown action: %ACTION%
    goto :finish_error
)

echo.
set "NOW="
if /I "%COMMAND%"=="watch" (
    set /p WATCH_INTERVAL=Check interval in seconds [60]: 
    if "%WATCH_INTERVAL%"=="" set "WATCH_INTERVAL=60"
) else (
    set /p NOW=Optional --now override [YYYY-MM-DD HH:MM[:SS], blank = current time]: 
)

if defined LIVE_FLAG (
    call :ensure_api_key
    if errorlevel 1 goto :finish_error
)

echo.
call :run_tool "%COMMAND%" "%LIVE_FLAG%" "%NOW%" "%WATCH_INTERVAL%"
set "EXIT_CODE=%ERRORLEVEL%"
goto :finish

:run_tool
set "COMMAND_ARG=%~1"
set "LIVE_ARG=%~2"
set "NOW_ARG=%~3"
set "INTERVAL_ARG=%~4"

if /I "%COMMAND_ARG%"=="watch" (
    if "%LIVE_ARG%"=="" (
        %PYTHON_CMD% -m event_countdown_updater --config "%CONFIG%" watch --interval "%INTERVAL_ARG%"
    ) else (
        %PYTHON_CMD% -m event_countdown_updater --config "%CONFIG%" watch %LIVE_ARG% --interval "%INTERVAL_ARG%"
    )
    exit /b %ERRORLEVEL%
)

if "%NOW_ARG%"=="" (
    if "%LIVE_ARG%"=="" (
        %PYTHON_CMD% -m event_countdown_updater --config "%CONFIG%" %COMMAND_ARG%
    ) else (
        %PYTHON_CMD% -m event_countdown_updater --config "%CONFIG%" %COMMAND_ARG% %LIVE_ARG%
    )
) else (
    if "%LIVE_ARG%"=="" (
        %PYTHON_CMD% -m event_countdown_updater --config "%CONFIG%" --now "%NOW_ARG%" %COMMAND_ARG%
    ) else (
        %PYTHON_CMD% -m event_countdown_updater --config "%CONFIG%" --now "%NOW_ARG%" %COMMAND_ARG% %LIVE_ARG%
    )
)
exit /b %ERRORLEVEL%

:find_python
python --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=python"
    exit /b 0
)

py -3 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py -3"
    exit /b 0
)

for %%P in (
    "%LocalAppData%\Python\bin\python.exe"
    "%UserProfile%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
) do (
    if exist "%%~P" (
        "%%~P" --version >nul 2>&1
        if not errorlevel 1 (
            set "PYTHON_CMD="%%~P""
            exit /b 0
        )
    )
)

for /D %%D in ("%LocalAppData%\Programs\Python\Python*") do (
    if exist "%%~D\python.exe" (
        "%%~D\python.exe" --version >nul 2>&1
        if not errorlevel 1 (
            set "PYTHON_CMD="%%~D\python.exe""
            exit /b 0
        )
    )
)

echo Python was not found. Install Python 3.11+ or add it to PATH.
exit /b 1

:ensure_api_key
if defined ROBLOX_API_KEY exit /b 0

echo.
echo Live mode needs ROBLOX_API_KEY. It will be set only for this window.
set /p ROBLOX_API_KEY=ROBLOX_API_KEY: 
if "%ROBLOX_API_KEY%"=="" (
    echo ROBLOX_API_KEY is empty; live update cannot run.
    exit /b 1
)
exit /b 0

:usage
echo Usage:
echo   run.bat
echo   run.bat path\to\config.toml
echo.
echo The script runs from its own folder, adds src to PYTHONPATH, asks for
echo status/dry-run/live mode, optional --now, and ROBLOX_API_KEY for live mode.
exit /b 0

:copy_failed
echo Failed to create "%CONFIG%".
goto :finish_error

:finish_error
set "EXIT_CODE=1"

:finish
echo.
echo Exit code: %EXIT_CODE%
pause
exit /b %EXIT_CODE%
