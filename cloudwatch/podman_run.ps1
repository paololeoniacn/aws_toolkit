# podman_run.ps1 — Build e avvio container CloudWatch tail
#
# USAGE (diretto):
#   .\podman_run.ps1 -Since "1h" -Filter "exportcms" -EnvFile "C:\...\envs\test-psn.env"
#
# USAGE (tramite Run-Log-Psn / Run-Log):
#   Il file env viene passato automaticamente dallo script PowerShell chiamante.

param(
    [string]$Since    = "1h",
    [string]$Filter   = "",
    [string]$Env      = "",
    [string]$Severity = "",
    [string]$LogType  = "",
    [string]$EnvFile  = ""
)

# Risolvi il path del file .env
if (-not $EnvFile) {
    $EnvFile = Join-Path $PSScriptRoot ".env"
}

if (-Not (Test-Path $EnvFile)) {
    Write-Host "File .env non trovato: $EnvFile" -ForegroundColor Red
    exit 1
}

function Get-PodmanReadiness {
    $output = & podman info 2>&1
    $exitCode = $LASTEXITCODE

    [pscustomobject]@{
        IsReady   = ($exitCode -eq 0)
        ErrorText = if ($exitCode -eq 0) { "" } else { ($output | Out-String).Trim() }
    }
}

function Wait-PodmanReady {
    param(
        [int]$MaxAttempts = 10,
        [int]$DelaySeconds = 2
    )

    $status = $null
    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        $status = Get-PodmanReadiness
        if ($status.IsReady) {
            return $status
        }

        if ($attempt -lt $MaxAttempts) {
            Start-Sleep -Seconds $DelaySeconds
        }
    }

    return $status
}

function Ensure-PodmanReady {
    if (-not (Get-Command podman -ErrorAction SilentlyContinue)) {
        Write-Host "Podman non trovato nel PATH. Installa Podman o verifica la configurazione della shell." -ForegroundColor Red
        exit 1
    }

    $status = Get-PodmanReadiness
    if ($status.IsReady) {
        return
    }

    Write-Host "Podman non risulta attivo. Avvio della machine di default..." -ForegroundColor Yellow
    & podman machine start

    $status = Wait-PodmanReady
    if (-not $status.IsReady) {
        Write-Host "Podman non e' partito correttamente. Verifica 'podman machine list' e lo stato della machine di default." -ForegroundColor Red
        if ($status.ErrorText) {
            Write-Host $status.ErrorText -ForegroundColor DarkRed
        }
        exit 1
    }
}

Ensure-PodmanReady

Write-Host "Costruzione immagine Docker 'cloudwatch-tail'..."
podman build -t cloudwatch-tail . | Write-Output

Write-Host "Avvio del container 'cloudwatch-tail' con:"
Write-Host "     --since   $Since"
Write-Host "     --filter  $Filter"
if ($Env)      { Write-Host "     --env      $Env" }
if ($Severity) { Write-Host "     --severity $Severity" }
if ($LogType)  { Write-Host "     --log-type $LogType" }
Write-Host "     --env-file $EnvFile"

podman run --rm -it --env-file $EnvFile cloudwatch-tail `
    --since $Since `
    --filter $Filter `
    --env $Env `
    --severity $Severity `
    --log-type $LogType

Write-Host "Pulizia: rimozione container basati sull'immagine 'cloudwatch-tail'..."
$containers = podman ps -a -q --filter ancestor=cloudwatch-tail
if ($containers) {
    podman rm -f $containers | Write-Output
} else {
    Write-Host "Nessun container da rimuovere."
}

Write-Host "Rimozione immagine 'cloudwatch-tail'..."
podman rmi cloudwatch-tail | Write-Output
Write-Host "Operazioni completate."
