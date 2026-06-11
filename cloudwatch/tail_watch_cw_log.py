import json
import os
import time
import boto3
import argparse
import datetime
from dotenv import load_dotenv
from botocore.exceptions import BotoCoreError, ClientError
import re
import pytz

# Flush immediato
import sys
sys.stdout.reconfigure(line_buffering=True)

# Regex per matchare "ERROR" come parola (non cattura "errorCode"), preceduto da ']' e spazi opzionali
error_pattern = re.compile(r'\] *ERROR\b', re.IGNORECASE)
# Regex per matchare "WARN" come parola
warn_pattern  = re.compile(r'\] *WARN\b',  re.IGNORECASE)

date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}')

TIMEOUT_SECS = 10
# Carica variabili .env
load_dotenv()

# Argomenti da CLI
parser = argparse.ArgumentParser()
parser.add_argument('--filter', default='', help="Prefisso log stream EKS (nome servizio/pod)")
parser.add_argument('--env', default='', help="Filtra per ambiente EKS (es: coll, coll-stage, prod)")
parser.add_argument('--since', default='5m', help="Quanto indietro nei log (es: 30m, 1h, 2h)")
parser.add_argument('--severity', default='', help="Filtra per livello: ERROR, WARN, INFO")
parser.add_argument('--filter-pattern', default='', help="CloudWatch Logs filter pattern (es: ?ERROR ?Exception)")
parser.add_argument('--log-type', default='', help="Tipo di log nel nome del gruppo (filtro legacy)")
parser.add_argument('--start', default='', help="Data inizio assoluta (es: 2026-03-30 o 2026-03-30T00:00:00, ora di Roma). Se presente, --since viene ignorato.")
parser.add_argument('--end',   default='', help="Data fine assoluta (es: 2026-03-31 o 2026-03-30T23:59:59, ora di Roma). Se presente, l'estrazione si ferma automaticamente.")

args = parser.parse_args()

print("📦 Argomenti ricevuti:", args)

SINCE = args.since

# --- Modalità di selezione log group ---
# LOG_GROUP (singolo): modalità diretta — usa il gruppo specificato senza discovery.
# LOG_GROUP_PREFIX (prefisso): modalità discovery — trova tutti i gruppi che iniziano con il prefisso.
# LOG_GROUP ha precedenza se entrambi sono presenti.
LOG_GROUP_SINGLE = os.getenv('LOG_GROUP', '')
LOG_GROUP_PREFIX = os.getenv('LOG_GROUP_PREFIX', '')

# Prefisso dei log stream FluentBit in EKS.
# Formato: fluentbit-kube.var.log.containers.<service>-<pod-hash>_<namespace>_...
# Configurabile via .env per adattarsi a setup FluentBit non standard.
EKS_STREAM_PREFIX = os.getenv('EKS_STREAM_PREFIX', 'fluentbit-kube.var.log.containers.')


# Parse durata tipo "30m", "1h"
def parse_duration(dur):
    unit = dur[-1]
    value = int(dur[:-1])
    if unit == 'm':
        return datetime.timedelta(minutes=value)
    elif unit == 'h':
        return datetime.timedelta(hours=value)
    else:
        raise ValueError("Formato --since non valido. Usa es: 30m o 1h")


# Calcolo start/end time
rome_tz  = pytz.timezone("Europe/Rome")
local_now = datetime.datetime.now(rome_tz)

if args.start:
    _fmt = "%Y-%m-%dT%H:%M:%S" if 'T' in args.start else "%Y-%m-%d"
    start_aware = rome_tz.localize(datetime.datetime.strptime(args.start, _fmt))
else:
    duration    = parse_duration(SINCE)
    start_aware = local_now - duration

start_time_global = int(start_aware.astimezone(datetime.timezone.utc).timestamp() * 1000)

end_time_ms  = None
end_aware    = None
if args.end:
    _fmt      = "%Y-%m-%dT%H:%M:%S" if 'T' in args.end else "%Y-%m-%d"
    end_aware = rome_tz.localize(datetime.datetime.strptime(args.end, _fmt))
    end_time_ms = int(end_aware.astimezone(datetime.timezone.utc).timestamp() * 1000)

print("-"*50)
print(f"🕒 Ora locale: {local_now}")
print(f"🕒 Start time log REQUEST: {start_aware}")
print(f"🕒 Start time UTC: {start_aware.astimezone(datetime.timezone.utc)}")
if end_aware:
    print(f"🕒 End time log REQUEST: {end_aware}")
    print(f"🕒 End time UTC: {end_aware.astimezone(datetime.timezone.utc)}")
print("🕓 Firma richiesta (UTC):", datetime.datetime.utcnow().isoformat() + "Z")
print("-"*50)

print("🔐 AWS_ACCESS_KEY_ID:", os.getenv('AWS_ACCESS_KEY_ID'))
print("🌍 AWS_DEFAULT_REGION:", os.getenv('AWS_DEFAULT_REGION'))
if LOG_GROUP_SINGLE:
    print(f"🎯 Log group singolo: '{LOG_GROUP_SINGLE}'")
else:
    print(f"🎯 Prefisso log group: '{LOG_GROUP_PREFIX}'")
if args.log_type:
    print(f"🗂️  Tipo log: '{args.log_type}'")
if args.filter:
    print(f"🔍 Filtro servizio: '{args.filter}' → stream prefix: '{EKS_STREAM_PREFIX}{args.filter}'")
if args.env:
    print(f"🌐 Filtro ambiente: '{args.env}'")
print("-"*50)

client = boto3.client('logs')


def is_eks_group(name: str) -> bool:
    """Restituisce True se il log group appartiene a un cluster EKS."""
    return '/aws/eks/' in name


def _extract_eks_env(cluster_name: str) -> str:
    """Estrae l'ambiente dal nome del cluster EKS.

    Convenzione: tdh-<env>-<cluster-type>
    Esempi:
      tdh-coll-apilayer       -> 'coll'
      tdh-coll-stage-apilayer -> 'coll-stage'
      tdh-prod-apilayer       -> 'prod'
    """
    if cluster_name.startswith('tdh-'):
        rest = cluster_name[4:]          # "coll-apilayer", "coll-stage-apilayer"
        parts = rest.rsplit('-', 1)      # split sull'ultimo '-'
        if len(parts) == 2:
            return parts[0]              # "coll", "coll-stage", "prod"
    return cluster_name


def get_label_from_log_group(log_group_name):
    """Estrae il label del servizio/ambiente dal nome del log group."""
    name = log_group_name.lower()

    # EKS PSN: /aws/eks/tdh-coll-apilayer, /aws/eks/tdh-coll-stage-apilayer, ecc.
    if is_eks_group(log_group_name):
        cluster = log_group_name.split('/')[-1]
        env = _extract_eks_env(cluster)
        if 'prod' in env:
            return f"🚀 [{env.upper()}]"
        elif 'stage' in env:
            return f"🧪 [{env.upper()}]"
        else:
            return f"🔧 [{env.upper()}]"

    # Etichette per nome servizio (fallback generico)
    service_labels = {
        "infocamere": "📤 InfoCamere",
        "crm":        "📦 Crm",
        "cdp":        "👁️ CDP",
        "utility":    "🔍 Utility",
        "google":     "🌎 Google",
        "cammini":    "🦶 Cammini",
        "ristoranti": "🍕 Ristoranti",
        "datalake":   "🌊 DataLake",
        "aem":        "📊 AEM",
        "esperienze": "🧩 Esperienze",
        "tools":      "⚙️ tools",
    }
    for key, label in service_labels.items():
        if key in name:
            return label

    parts = log_group_name.split('/')
    service = parts[-1] if parts else log_group_name
    return f"___{service}"


def discover_log_groups():
    """Trova tutti i log group corrispondenti ai filtri specificati.

    Modalità LOG_GROUP_SINGLE: restituisce direttamente il gruppo specificato,
    senza discovery. Usata per ambienti con un singolo log group noto.

    Modalità LOG_GROUP_PREFIX: scopre tutti i gruppi con il prefisso dato.
    EKS PSN: filtra per ambiente tramite _extract_eks_env().
    """
    # --- Modalità singolo gruppo (LOG_GROUP) ---
    if LOG_GROUP_SINGLE:
        return [LOG_GROUP_SINGLE]

    # --- Modalità discovery per prefisso (LOG_GROUP_PREFIX) ---
    paginator = client.get_paginator('describe_log_groups')
    groups = []
    for page in paginator.paginate(logGroupNamePrefix=LOG_GROUP_PREFIX):
        for group in page.get('logGroups', []):
            name = group['logGroupName']

            if is_eks_group(name):
                # Filtra per ambiente EKS con match preciso sul nome cluster
                if args.env:
                    cluster = name.split('/')[-1]
                    env_in_cluster = _extract_eks_env(cluster)
                    if env_in_cluster != args.env.lower():
                        continue
                # Filtro servizio avviene sui log stream in tail_all_groups
            else:
                if args.log_type and args.log_type not in name:
                    continue
                if args.filter and args.filter.lower() not in name.lower():
                    continue
                if args.env and args.env.lower() not in name.lower():
                    continue

            groups.append(name)
    return groups


def tail_all_groups(log_groups, start_time, end_time_ms=None):
    """Tail multipli log group in polling round-robin."""
    last_times = {lg: start_time for lg in log_groups}

    print(f"📡 Tailing {len(log_groups)} log group(s):")
    for lg in log_groups:
        print(f"  - {lg}")
    print("-" * 50)

    try:
        while True:
            if end_time_ms:
                now_ms = int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000)
                if now_ms >= end_time_ms:
                    print("\n✅ Fine finestra temporale raggiunta. Estrazione completata.")
                    break
            had_events = False

            for log_group in log_groups:
                kwargs = {
                    'logGroupName': log_group,
                    'startTime': last_times[log_group],
                    'interleaved': True,
                }

                # --- Filtro log stream (EKS) ---
                # FluentBit nomina gli stream:
                #   fluentbit-kube.var.log.containers.<service>-<pod-hash>_...
                # logStreamNamePrefix filtra server-side: preciso, efficiente,
                # nessun falso positivo da contenuto di altri servizi.
                if is_eks_group(log_group) and args.filter:
                    kwargs['logStreamNamePrefix'] = f"{EKS_STREAM_PREFIX}{args.filter}"

                # --- Filtro contenuto (filterPattern CloudWatch) ---
                # filter_pattern esplicito ha priorità massima.
                # severity da sola viene promossa a filterPattern.
                if args.filter_pattern:
                    kwargs['filterPattern'] = args.filter_pattern
                elif args.severity:
                    kwargs['filterPattern'] = f'"{args.severity.upper()}"'

                try:
                    response = client.filter_log_events(**kwargs)
                    events = response.get('events', [])

                    # Segui nextToken finché ci sono pagine vuote (es. gap tra deploy)
                    _next = response.get('nextToken')
                    while not events and _next:
                        skip_kwargs = dict(kwargs)
                        skip_kwargs['nextToken'] = _next
                        response = client.filter_log_events(**skip_kwargs)
                        events = response.get('events', [])
                        _next = response.get('nextToken')

                    if events:
                        had_events = True
                        base_label = get_label_from_log_group(log_group)

                        for event in events:
                            msg = event['message'].strip()

                            # Prova a parsare JSON per estrarre 'log'
                            try:
                                parsed = json.loads(msg)
                                log_line = str(parsed.get('log', msg))
                            except json.JSONDecodeError:
                                log_line = msg

                            # Filtro manuale se filterPattern non trova tutto
                            if args.severity and args.severity.upper() not in log_line.upper():
                                continue

                            label = base_label
                            if error_pattern.search(log_line):
                                label = f"❌❌❌ ERROR - {base_label}"
                            elif warn_pattern.search(log_line):
                                label = f"⚠️⚠️⚠️ WARN - {base_label}"

                            lines = log_line.splitlines()
                            if lines:
                                for line in lines:
                                    if date_pattern.match(line):
                                        print(f"{label} {line}", flush=True)
                                    else:
                                        print(f"│   {line}", flush=True)

                        last_times[log_group] = events[-1]['timestamp'] + 1

                except ClientError as e:
                    print(f"⚠️ Errore su {log_group}: {e}")

            if not had_events:
                print(f"⏳ Nessun nuovo log negli ultimi {TIMEOUT_SECS} secondi...")

            time.sleep(TIMEOUT_SECS)

    except KeyboardInterrupt:
        print("\n🛑 Interrotto dall'utente.")
    except Exception as e:
        print("❌ Errore:", e)
        print("Wait for 5 minutes or try to execute -> podman machine stop && podman machine start")


def list_log_groups():
    """Restituisce i log group disponibili (per diagnostica)."""
    try:
        log_groups = []
        paginator = client.get_paginator('describe_log_groups')
        kwargs = {}
        if LOG_GROUP_PREFIX:
            kwargs['logGroupNamePrefix'] = LOG_GROUP_PREFIX
        for page in paginator.paginate(**kwargs):
            for group in page.get('logGroups', []):
                log_groups.append(group['logGroupName'])
        return log_groups
    except (BotoCoreError, ClientError) as e:
        print(f"❌ Errore AWS: {e}")
        return []


if __name__ == "__main__":
    log_groups = discover_log_groups()
    if not log_groups:
        print("⚠️ Nessun log group trovato con i filtri specificati.")
        print("💡 Log group disponibili:")
        for lg in list_log_groups():
            print(f"  - {lg}")
    else:
        tail_all_groups(log_groups, start_time_global, end_time_ms)
