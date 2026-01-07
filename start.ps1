# Start the Flask application (Windows PowerShell)
# Usage: .\start.ps1

$ErrorActionPreference = "Stop"

# Get script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host "Starting Hybrid AI Invoice Parser..." -ForegroundColor Cyan

# Check if virtual environment exists
$venvPath = Join-Path $scriptDir "venv\Scripts\Activate.ps1"
if (Test-Path $venvPath) {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    & $venvPath
} else {
    Write-Host "Warning: Virtual environment not found. Using system Python." -ForegroundColor Yellow
}

# Check if app.py exists
$appPath = Join-Path $scriptDir "app.py"
if (-not (Test-Path $appPath)) {
    Write-Host "Error: app.py not found!" -ForegroundColor Red
    exit 1
}

# Start Flask application
Write-Host "Starting Flask server..." -ForegroundColor Green
Write-Host "Application will be available at: http://127.0.0.1:5000" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Gray
Write-Host ""

# Open browser after delay using cmd (most reliable method)
cmd /c "start /min cmd /c `"timeout /t 4 /nobreak >nul && start http://127.0.0.1:5000`""

python app.py
