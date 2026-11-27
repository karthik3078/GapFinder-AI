$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Test-Path '.venv/Scripts/python.exe')) {
    throw 'Create .venv and install requirements first. See README.md.'
}
if (-not (Test-Path 'frontend/dist/index.html')) {
    Push-Location frontend
    try {
        npm ci
        if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
        npm run build
        if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
    } finally { Pop-Location }
}
Write-Host 'Open http://127.0.0.1:8000 - Demo: student@demo.com / demo123'
& '.venv/Scripts/python.exe' -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
