# Reset Database
Write-Host "Resetting database..." -ForegroundColor Red
Set-Location $PSScriptRoot

$dbDir = "server/db"

# Reset users
Set-Content -Path "$dbDir/users.json" -Value '{"users": []}'
Write-Host "  - users.json cleared" -ForegroundColor Gray

# Reset games
Set-Content -Path "$dbDir/games.json" -Value '{"games": []}'
Write-Host "  - games.json cleared" -ForegroundColor Gray

# Reset rooms
Set-Content -Path "$dbDir/rooms.json" -Value '{"rooms": []}'
Write-Host "  - rooms.json cleared" -ForegroundColor Gray

# Clear storage
if (Test-Path "server/storage/*.zip") {
    Remove-Item "server/storage/*.zip" -Force
    Write-Host "  - storage/*.zip cleared" -ForegroundColor Gray
}

Write-Host "Database reset complete!" -ForegroundColor Green
