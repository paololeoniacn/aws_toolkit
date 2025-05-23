# USAGE
# .\podman_run.ps1 -Since "1h" -Filter "infocamere" 


param(
    [string]$Since = "1h",
    [string]$Filter = "utility",
    [string]$Severity = "ERROR"
)

Write-Host "🔧 Costruzione immagine Docker 'cloudwatch-tail'..."
podman build -t cloudwatch-tail . | Write-Output

if (-Not (Test-Path ".env")) {
    Write-Host "⚠️  File .env non trovato. Creane uno prima di eseguire il container." -ForegroundColor Red
    exit 1
}

Write-Host "🚀 Avvio del container 'cloudwatch-tail' con:"
Write-Host "     --since $Since"
Write-Host "     --filter $Filter"
Write-Host "     --severity $Severity"

podman run --rm -it --env-file .env cloudwatch-tail `
    --since $Since `
    --filter $Filter `
    --severity $Severity

Write-Host "🧹 Pulizia: rimozione container basati sull'immagine 'cloudwatch-tail'..."
$containers = podman ps -a -q --filter ancestor=cloudwatch-tail
if ($containers) {
    podman rm -f $containers | Write-Output
} else {
    Write-Host "✅ Nessun container da rimuovere."
}

Write-Host "🗑️ Rimozione immagine 'cloudwatch-tail'..."
podman rmi cloudwatch-tail | Write-Output

Write-Host "✅ Operazioni completate."
