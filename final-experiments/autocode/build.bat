@echo off
setlocal

if "%1"=="" goto run
if "%1"=="run" goto run
if "%1"=="tui" goto tui
if "%1"=="setup" goto setup
if "%1"=="test" goto test
if "%1"=="test-all" goto testall
if "%1"=="go-test" goto gotest
if "%1"=="lint" goto lint
if "%1"=="format" goto format
if "%1"=="help" goto help
echo Unknown target: %1
goto help

:run
echo Building Go TUI...
cd cmd\autocode-tui && go build -o ..\..\build\autocode-tui.exe . && cd ..\..
if errorlevel 1 (
    echo Build failed!
    goto end
)
echo Build OK. Running...
build\autocode-tui.exe
goto end

:tui
echo Building Go TUI...
cd cmd\autocode-tui && go build -o ..\..\build\autocode-tui.exe .
goto end

:testall
echo Running Go tests...
cd cmd\autocode-tui && go test ./... -v -count=1 && cd ..\..
echo Running Python tests...
uv run pytest tests/ -v --cov=src/autocode
goto end

:setup
echo Installing Python dependencies...
uv sync --all-extras
goto end

:test
echo Running Python tests...
uv run pytest tests/ -v --cov=src/autocode
goto end

:gotest
echo Running Go tests...
cd cmd\autocode-tui && go test ./... -v
goto end

:lint
echo Running linters...
uv run ruff check src/ tests/
uv run mypy src/autocode/
goto end

:format
echo Formatting code...
uv run ruff format src/ tests/
goto end

:help
echo Usage: build.bat [target]
echo.
echo Targets:
echo   run       Build + run Go TUI (default when no target given)
echo   tui       Build Go TUI frontend only
echo   setup     Install Python dependencies (uv sync --all-extras)
echo   test      Run Python unit tests
echo   test-all  Run Go + Python tests
echo   go-test   Run Go unit tests
echo   lint      Run ruff + mypy
echo   format    Run ruff format
goto end

:end
endlocal
