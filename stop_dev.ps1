Write-Host "Deteniendo backend y contenedores..."

Set-Location "C:\ProjectsZeqe\sports-booking"
docker compose down

Write-Host "Entorno detenido"
& .\.venv\Scripts\deactivate
