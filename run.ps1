# Check for Python installation
try {
    python --version | Out-Null
} catch {
    Write-Host "Python is not installed or not in PATH" -ForegroundColor Red
    exit 1
}

# Create logs directory if it doesn't exist
if (-not (Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs" | Out-Null
}

# Activate virtual environment if it exists
if (Test-Path ".venv\Scripts\Activate.ps1") {
    . .venv\Scripts\Activate.ps1
} else {
    Write-Host "Virtual environment not found. Creating one..." -ForegroundColor Yellow
    python -m venv .venv
    . .venv\Scripts\Activate.ps1
    python -m pip install --upgrade pip
    pip install -r requirements.txt
}

# Parse command line arguments
$debugMode = $args -contains "--debug"
$helpMode = $args -contains "--help"

if ($helpMode) {
    Write-Host "Usage:"
    Write-Host "  .\run.ps1 [options]`n"
    Write-Host "Options:"
    Write-Host "  --debug    Start application in debug mode"
    Write-Host "  --help     Show this help message"
    exit 0
}

if ($debugMode) {
    Write-Host "Starting in debug mode..." -ForegroundColor Cyan
    Write-Host "Debug log will be written to logs\debug.log" -ForegroundColor Cyan
    python src/main.py --debug 2>&1 | Tee-Object -FilePath "logs\debug.log"
} else {
    Write-Host "Starting in normal mode..." -ForegroundColor Green
    python src/main.py
}

# Check exit code
if ($LASTEXITCODE -ne 0) {
    Write-Host "Application exited with error code $LASTEXITCODE" -ForegroundColor Red
    if ($debugMode) {
        Write-Host "Check logs\debug.log for details" -ForegroundColor Yellow
    }
}

# Deactivate virtual environment
deactivate 