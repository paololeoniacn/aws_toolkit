# aws_toolkit

Raccolta di strumenti AWS containerizzati via Podman. Ogni modulo è indipendente e si avvia con un singolo comando.

---

## Moduli

| Cartella | Cosa fa |
|---|---|
| [`cloudwatch/`](#cloudwatch--log-viewer-eks) | Tail in tempo reale dei log CloudWatch da cluster EKS |
| [`s3_batch_rename/`](s3_batch_rename/README.md) | Rinomina bulk di chiavi S3 (copy + delete) |
| [`s3_count_by_prefix/`](s3_count_by_prefix/) | Conteggio oggetti S3 per prefisso |
| [`s3_manager/`](s3_manager/) | CLI interattiva per operazioni su S3 (list, upload, download, delete) |
| [`lambda/`](lambda/) | Script per build e deploy di Lambda Layer Python su AWS |

---

## cloudwatch — Log viewer EKS

Legge in tempo reale i log dei pod EKS tramite l'API CloudWatch Logs. Gira dentro un container Podman: nessuna dipendenza Python da installare localmente.

### Come funziona

```
PowerShell (terminale)
  ├── Run-Log-Psn       ← linea PSN  (EKS PSN, check credenziali automatico)
  └── Run-Log           ← linea legacy (EKS legacy, credenziali manuali)
        └── cloudwatch/podman_run.ps1      ← build + avvio container
              └── cloudwatch/tail_watch_cw_log.py  ← polling CloudWatch API
```

I log vengono raccolti da **FluentBit** e scritti su CloudWatch Logs. Lo script filtra per servizio usando `logStreamNamePrefix` (filtraggio server-side, efficiente).

> Gli script PowerShell `Run-Log-Psn` e `Run-Log` non fanno parte di questa repo — sono mantenuti sulla repo PSN di progetto. Questa repo contiene solo il core containerizzato (`cloudwatch/`) e i template di configurazione (`envs/`).

---

## Setup (una tantum)

### 1 — Prerequisiti

```powershell
podman --version          # richiesto: 4.x+
aws --version             # richiesto: AWS CLI v2  (solo per Run-Log-Psn)
$PSVersionTable.PSVersion # richiesto: 7.0+
```

- Podman: [podman.io](https://podman.io/getting-started/installation)
- AWS CLI v2: [aws.amazon.com/cli](https://aws.amazon.com/cli/)
- PowerShell 7: [github.com/PowerShell/PowerShell](https://github.com/PowerShell/PowerShell/releases)
- klogg (opzionale — log viewer con follow): [github.com/variar/klogg](https://github.com/variar/klogg)

---

### 2 — Clona la repo

Scegli una cartella padre (es. `C:\mitur\tools\`) e clona dentro:

```powershell
git clone https://github.com/paololeoniacn/aws_toolkit.git C:\mitur\tools\aws_toolkit
```

---

### 3 — Crea la cartella credenziali

Le credenziali AWS **non devono stare nella repo**. La posizione consigliata è una cartella `envs/` **allo stesso livello** di `aws_toolkit/` — in questo modo basta impostare una sola variabile d'ambiente e tutto funziona automaticamente:

```
C:\mitur\tools\
  aws_toolkit\   ← repo (git clone)
  envs\          ← credenziali locali (mai versionato)
```

```powershell
mkdir C:\mitur\tools\envs
```

Copia i template dalla repo, rinominali senza `.example` e compila le credenziali:

```powershell
copy C:\mitur\tools\aws_toolkit\envs\test-psn.env.example  C:\mitur\tools\envs\test-psn.env
notepad C:\mitur\tools\envs\test-psn.env
```

Fai lo stesso per gli ambienti che ti servono (`stage-psn.env`, `prod-psn.env`, `test.env`, `stage.env`, `prod.env`).

**Formato credenziali PSN** (recuperare dal portale AWS SSO):
```
AWS_ACCESS_KEY_ID=ASIA...
AWS_SECRET_ACCESS_KEY=...
AWS_SESSION_TOKEN=...
AWS_DEFAULT_REGION=eu-south-1
LOG_GROUP_PREFIX=/aws/eks/tdh-
EKS_STREAM_PREFIX=fluentbit-kube.var.log.containers.
```

**Formato credenziali legacy**:
```
AWS_ACCESS_KEY_ID=ASIA...
AWS_SECRET_ACCESS_KEY=...
AWS_SESSION_TOKEN=...
AWS_DEFAULT_REGION=eu-south-1
LOG_GROUP=/aws/eks/<nome-cluster>
```

> Le credenziali SSO scadono ogni ~1 ora. `Run-Log-Psn` le controlla automaticamente e chiede il rinnovo interattivo. `Run-Log` richiede aggiornamento manuale del file `.env`.

---

### 4 — Configura il profilo PowerShell

Gli script `Run-Log-Psn` e `Run-Log` sono disponibili sulla **repo PSN di progetto**. Una volta recuperati e posizionati, apri il profilo PowerShell:

```powershell
notepad $PROFILE
```

Aggiungi **solo questa variabile** (il path alla cartella `aws_toolkit` clonata):

```powershell
$env:CW_TOOLKIT_ROOT = "C:\mitur\tools\aws_toolkit"
```

Se `envs/` è allo stesso livello di `aws_toolkit/` (struttura consigliata), non serve impostare altro — la cartella viene trovata automaticamente come cartella sorella. In alternativa, se preferisci un path personalizzato:

```powershell
$env:CW_ENVS_ROOT = "C:\percorso\personalizzato\envs"   # opzionale
```

Ricarica il profilo:

```powershell
. $PROFILE
```

---

### 5 — Verifica

```powershell
Get-Command Run-Log, Run-Log-Psn
```

Output atteso:
```
CommandType  Name          Version  Source
-----------  ----          -------  ------
Function     Run-Log
Function     Run-Log-Psn
```

---

## Utilizzo

### Run-Log-Psn (linea PSN)

```powershell
Run-Log-Psn -Filter "exportcms" -Since "1h"                           # TEST, ultima ora
Run-Log-Psn -Filter "cdp"       -Since "30m" -Env STAGE               # STAGE, 30 minuti
Run-Log-Psn -Filter "aem"       -Since "2h"  -Env PROD -Severity ERROR -Klogg
Run-Log-Psn -Filter ""          -Since "15m" -Console                  # tutti i servizi
```

| Parametro | Valori | Default |
|---|---|---|
| `-Filter` | nome servizio | — (obbligatorio) |
| `-Since` | `15m` `1h` `2h` `1d` | — (obbligatorio) |
| `-Env` | `TEST` `STAGE` `PROD` | `TEST` |
| `-Severity` | `ERROR` `WARN` `INFO` | — |
| `-Console` | switch | off |
| `-Klogg` | switch | off |
| `-LogDir` | path | `C:\Mitur_logs` |

Mapping ambienti PSN:

| `-Env` | Cluster EKS | Log group |
|---|---|---|
| `TEST` | `coll` | `/aws/eks/tdh-coll-apilayer` |
| `STAGE` | `coll-stage` | `/aws/eks/tdh-coll-stage-apilayer` |
| `PROD` | `prod` | `/aws/eks/tdh-prod-apilayer` |

Output log: `C:\Mitur_logs\psn\<env>\psn_<env>_<servizio>_<timestamp>(S<since>).log`

---

### Run-Log (linea legacy)

```powershell
Run-Log -Filter "utility"    -Since "1h"
Run-Log -Filter "cammini"    -Since "30m" -Env STAGE -Klogg
Run-Log -Filter "ristoranti" -Since "2h"  -Env PROD  -Console
```

Stessi parametri di `Run-Log-Psn`, senza `-Severity`. Le credenziali vanno aggiornate manualmente nel file `.env` corrispondente.

Output log: `C:\Mitur_logs\<env>\<env>_<servizio>_<timestamp>(S<since>).log`

---

## Struttura repo

```
aws_toolkit/
  cloudwatch/           ← core: Dockerfile, script Python, podman_run.ps1
  envs/                 ← template .env.example (uno per ambiente, nessuna credenziale)
  s3_batch_rename/      ← rinomina bulk chiavi S3
  s3_count_by_prefix/   ← conteggio oggetti S3
  s3_manager/           ← CLI interattiva S3
  lambda/               ← build Lambda Layer Python
```

I file `.env` reali (credenziali) vanno tenuti **fuori dalla repo**. La convenzione consigliata è una cartella `envs/` sorella di `aws_toolkit/`, così basta impostare solo `CW_TOOLKIT_ROOT` nel profilo.

---

## Troubleshooting

| Sintomo | Causa | Soluzione |
|---|---|---|
| `Run-Log / Run-Log-Psn non riconosciuto` | Profilo non ricaricato | `. $PROFILE` |
| `Cartella cloudwatch non trovata` | `CW_TOOLKIT_ROOT` errato o non impostato | Verifica il path nella variabile |
| `File .env non trovato` | `envs/` non è sorella di `aws_toolkit/` oppure `CW_ENVS_ROOT` non impostato | Crea `envs/` affianco o imposta `CW_ENVS_ROOT` |
| `UnrecognizedClientException` | Credenziali scadute | `Run-Log-Psn`: prompt automatico — `Run-Log`: aggiorna `.env` manualmente |
| `⏳ Nessun nuovo log` in loop | `-Filter` non matcha nessuno stream | Prova con `-Filter ""` per vedere tutti i log |
| `podman_run.ps1 non trovato` | Repo incompleta o path errato | Verifica che `cloudwatch/podman_run.ps1` esista nel clone |
