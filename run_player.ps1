# Run Player Client
Write-Host "Starting Player Client..." -ForegroundColor Yellow
Set-Location $PSScriptRoot
& ".venv/Scripts/python.exe" -m player_client.client
