#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ---------------------------------------------------
# Funzioni di supporto
# ---------------------------------------------------
function ErrorExit {
    param (
        [string]$Message,
        [int]$ExitCode = 1
    )
    Write-Error "Errore: $Message"
    exit $ExitCode
}

function Info {
    param ([string]$Message)
    Write-Host "⟳ $Message"
}

function Cleanup {
    Info "Rimuovo il file temporaneo .env"
    Remove-Item -Path ".env" -ErrorAction SilentlyContinue
}
Register-EngineEvent PowerShell.Exiting -Action { Cleanup }

# ---------------------------------------------------
# Parsing argomenti
# ---------------------------------------------------
$envSuffix = ""
$positionalArgs = @()
$targetFile = ".env"

for ($i = 0; $i -lt $args.Count; $i++) {
    switch ($args[$i]) {
        '-env' {
            $envSuffix = $args[$i + 1]
            $i++
            continue
        }
        '-h' | '--help' {
            Info "Uso: script.ps1 [-env <ambiente>] [altri argomenti]"
            Info "Esempio: .\script.ps1 -env prod log-group-name"
            exit 0
        }
        default {
            if ($args[$i].StartsWith('-')) {
                ErrorExit "Opzione sconosciuta: $($args[$i])"
            } else {
                $positionalArgs += $args[$i]
            }
        }
    }
}

# ---------------------------------------------------
# 1. Controlla che podman sia installato
# ---------------------------------------------------
if (-not (Get-Command podman -ErrorAction SilentlyContinue)) {
    ErrorExit "podman non trovato. Installa Podman seguendo https://podman.io/getting-started/installation"
}

# ---------------------------------------------------
# 2. Verifica presenza file .env (dinamico)
# ---------------------------------------------------
$envFile = if ($envSuffix) { ".env.$envSuffix" } else { ".env.dev" }

Info "Usando file di ambiente: $envFile"

if (-Not (Test-Path $envFile)) {
    ErrorExit "file '$envFile' non trovato. Crea '$envFile' con le variabili d'ambiente necessarie prima di eseguire lo script."
}

Copy-Item -Path $envFile -Destination $targetFile -Force

# ---------------------------------------------------
# 3. Configurazione immagine
# ---------------------------------------------------
$imageName = "cloudwatch-tail"

# ---------------------------------------------------
# 4. Costruzione immagine
# ---------------------------------------------------
Info "Inizio build dell'immagine '$imageName'..."
try {
    podman build -t $imageName .
} catch {
    ErrorExit "build fallita. Controlla il Dockerfile e i permessi nella directory corrente."
}
Info "Build completata con successo."

# ---------------------------------------------------
# 5. Avvio del container
# ---------------------------------------------------
if ($positionalArgs.Count -eq 0) {
    Info "Nessun argomento passato al container."
}

Info "Avvio del container '$imageName'..."
try {
    podman run --rm -it --env-file $targetFile $imageName @positionalArgs
} catch {
    ErrorExit "avvio del container fallito. 
- Verifica i parametri passati: $($positionalArgs -join ' ') 
- Controlla il contenuto di '$targetFile' 
- Assicurati che l’immagine esista con 'podman images'"
}

Info "Container terminato correttamente."
