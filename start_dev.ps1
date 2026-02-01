Write-Host "Iniciando entorno de desarrollo..."

Write-Host "Iniciando Docker Desktop..."
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"

Write-Host "Esperando a Docker..."
do {
    Start-Sleep -Seconds 3
    $dockerReady = docker info 2>$null
} until ($dockerReady)

Write-Host "Docker listo"

Write-Host "Levantando contenedores..."
Set-Location "C:\ProjectsZeqe\sports-booking"
docker compose up -d

Write-Host "Iniciando backend..."
& .\.venv\Scripts\activate
uvicorn app.main:app --reload
