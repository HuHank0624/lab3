# Run Server
Write-Host "Starting Game Platform Server..." -ForegroundColor Green
Set-Location $PSScriptRoot
& ".venv/Scripts/python.exe" -m server.server
