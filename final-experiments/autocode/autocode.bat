@echo off
:: AutoCode launcher — builds latest Go TUI and runs it from any directory.
:: Place this on your PATH or run it directly.

setlocal
set "PROJECT=K:\projects\ai\lowrescoder"
set "TUI_SRC=%PROJECT%\cmd\autocode-tui"
set "TUI_BIN=%PROJECT%\build\autocode-tui.exe"

:: Tell the Go TUI how to start the Python backend (works from any directory)
set "AUTOCODE_PYTHON_CMD=%PROJECT%\build\autocode-backend.bat"

:: Build latest
pushd "%TUI_SRC%"
go build -o "%TUI_BIN%" . 2>nul
if errorlevel 1 (
    echo [AutoCode] Build failed. Running last known good binary...
) else (
    echo [AutoCode] Built latest.
)
popd

:: Run from current directory (so agent sees the right project root)
"%TUI_BIN%" %*
