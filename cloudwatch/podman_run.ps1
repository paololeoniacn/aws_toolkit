# podman_run.ps1 — Build e avvio container CloudWatch tail
#
# USAGE (diretto):
#   .\podman_run.ps1 -Since "1h" -Filter "exportcms" -EnvFile "C:\...\envs\test-psn.env"
#
# USAGE (tramite Run-Log-Psn / Run-Log):
#   Il file env viene passato automaticamente dallo script PowerShell chiamante.

param(
    [string]$Since         = "1h",
    [string]$Filter        = "",
    [string]$Env           = "",
    [string]$Severity      = "",
    [string]$LogType       = "",
    [string]$FilterPattern = "",
    [string]$EnvFile       = "",
    [string]$StartDate     = "",
    [string]$EndDate       = ""
)

# Risolvi il path del file .env
if (-not $EnvFile) {
    $EnvFile = Join-Path $PSScriptRoot ".env"
}

if (-Not (Test-Path $EnvFile)) {
    Write-Host "File .env non trovato: $EnvFile" -ForegroundColor Red
    exit 1
}

# Esegue un comando podman con timeout: senza questo, un hang della VM (tipico dopo
# lo sleep del PC per conflitti di rete WSL2/Hyper-V) blocca lo script a tempo indefinito.
function Invoke-PodmanWithTimeout {
    param(
        [Parameter(Mandatory)] [string[]] $PodmanArgs,
        [int] $TimeoutSeconds = 30
    )

    $outFile = [System.IO.Path]::GetTempFileName()
    $errFile = [System.IO.Path]::GetTempFileName()
    try {
        $proc = Start-Process -FilePath "podman" -ArgumentList $PodmanArgs -NoNewWindow -PassThru `
            -RedirectStandardOutput $outFile -RedirectStandardError $errFile

        if (-not $proc.WaitForExit($TimeoutSeconds * 1000)) {
            try { $proc.Kill($true) } catch {}
            return [pscustomobject]@{ TimedOut = $true; ExitCode = $null; Output = "" }
        }

        $output = (Get-Content $outFile -Raw -ErrorAction SilentlyContinue) + (Get-Content $errFile -Raw -ErrorAction SilentlyContinue)
        return [pscustomobject]@{ TimedOut = $false; ExitCode = $proc.ExitCode; Output = $output }
    }
    finally {
        Remove-Item $outFile, $errFile -ErrorAction SilentlyContinue
    }
}

function Test-PodmanReady {
    param([int]$TimeoutSeconds = 15)
    $result = Invoke-PodmanWithTimeout -PodmanArgs @("info") -TimeoutSeconds $TimeoutSeconds
    return (-not $result.TimedOut) -and ($result.ExitCode -eq 0)
}

function Ensure-PodmanReady {
    if (-not (Get-Command podman -ErrorAction SilentlyContinue)) {
        Write-Host "Podman non trovato nel PATH. Installa Podman o verifica la configurazione della shell." -ForegroundColor Red
        exit 1
    }

    if (Test-PodmanReady) {
        return
    }

    Write-Host "Podman non risulta attivo. Avvio della machine di default..." -ForegroundColor Yellow
    $start = Invoke-PodmanWithTimeout -PodmanArgs @("machine", "start") -TimeoutSeconds 90

    if ($start.TimedOut) {
        Write-Host "'podman machine start' non ha risposto entro 90s." -ForegroundColor Red
        Write-Host "Probabile stato di rete WSL2 incoerente (capita dopo lo sleep del PC.) Prova a mano: 'wsl --shutdown' seguito da 'podman machine start'." -ForegroundColor DarkRed
        exit 1
    }

    for ($attempt = 1; $attempt -le 3; $attempt++) {
        if (Test-PodmanReady -TimeoutSeconds 10) {
            return
        }
        if ($attempt -lt 3) { Start-Sleep -Seconds 2 }
    }

    Write-Host "Podman non e' partito correttamente. Verifica 'podman machine list' e lo stato della machine di default." -ForegroundColor Red
    if ($start.Output) {
        Write-Host $start.Output -ForegroundColor DarkRed
    }
    exit 1
}

Ensure-PodmanReady

Write-Host "Costruzione immagine Docker 'cloudwatch-tail'..."
podman build -t cloudwatch-tail . | Write-Output

Write-Host "Avvio del container 'cloudwatch-tail' con:"
Write-Host "     --since   $Since"
Write-Host "     --filter  $Filter"
if ($Env)           { Write-Host "     --env            $Env" }
if ($Severity)      { Write-Host "     --severity       $Severity" }
if ($LogType)       { Write-Host "     --log-type       $LogType" }
if ($FilterPattern) { Write-Host "     --filter-pattern $FilterPattern" }
Write-Host "     --env-file $EnvFile"

$containerName = "cloudwatch-tail-$(Get-Random)"

$containerArgs = @(
    '--since',          $Since,
    '--filter',         $Filter,
    '--env',            $Env,
    '--severity',       $Severity,
    '--log-type',       $LogType,
    '--filter-pattern', $FilterPattern
)
if ($StartDate) { $containerArgs += '--start', $StartDate }
if ($EndDate)   { $containerArgs += '--end',   $EndDate }

podman run --rm -it --name $containerName --env-file $EnvFile cloudwatch-tail @containerArgs

# --rm rimuove automaticamente questo container all'uscita.
# L'immagine viene rimossa solo se non ci sono altre istanze ancora attive.
Write-Host "Pulizia post-run..."
$running = podman ps -q --filter ancestor=cloudwatch-tail
if (-not $running) {
    Write-Host "Rimozione immagine 'cloudwatch-tail'..."
    podman rmi cloudwatch-tail 2>&1 | Out-Null
    Write-Host "Operazioni completate."
} else {
    Write-Host "Altre istanze attive, immagine mantenuta."
    Write-Host "Operazioni completate."
}
