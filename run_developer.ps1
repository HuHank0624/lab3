# Run Developer Client
Write-Host "Starting Developer Client..." -ForegroundColor Cyan
Set-Location $PSScriptRoot
& ".venv/Scripts/python.exe" -m developer_client.client
