import os
import time
import boto3
import argparse
import datetime
from dotenv import load_dotenv
from botocore.exceptions import BotoCoreError, ClientError

# Flush immediato
import sys
sys.stdout.reconfigure(line_buffering=True)

# Carica variabili .env
load_dotenv()

# Argomenti da CLI
parser = argparse.ArgumentParser()
parser.add_argument('--filter', default='utility', help="Filtro log stream name")
parser.add_argument('--since', default='5m', help="Quanto indietro nei log (es: 30m, 1h, 2h)")
parser.add_argument('--severity', default='', help="Filtra solo log che contengono questa stringa (es: ERROR, WARN, INFO)")

args = parser.parse_args()

print("📦 Argomenti ricevuti:", args)


LOG_STREAM_FILTER = args.filter
SINCE = args.since

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

# Calcolo start time
duration = parse_duration(SINCE)
# start_time = int((datetime.datetime.now() - duration).timestamp() * 1000) # ROME
start_time = int((datetime.datetime.now(datetime.timezone.utc) - duration).timestamp() * 1000) # UTC


print("🔐 AWS_ACCESS_KEY_ID:", os.getenv('AWS_ACCESS_KEY_ID'))
print("🌍 AWS_DEFAULT_REGION:", os.getenv('AWS_DEFAULT_REGION'))
print(f"🎯 Filtro stream: '{LOG_STREAM_FILTER}', da {SINCE} fa")

client = boto3.client('logs')
LOG_GROUP=os.getenv('LOG_GROUP')

print("🔐 LOG_GROUP:", LOG_GROUP)

def get_first_stream_with_events():
    print("🔍 Cerco log stream attivo...")
    paginator = client.get_paginator('describe_log_streams')
    for page in paginator.paginate(
        logGroupName=LOG_GROUP,
        orderBy='LastEventTime',
        descending=True
    ):
        for stream in page['logStreams']:
            name = stream['logStreamName']
            if LOG_STREAM_FILTER not in name:
                continue
            response = client.get_log_events(
                logGroupName=LOG_GROUP,
                logStreamName=name,
                startTime=start_time,
                limit=1,
                startFromHead=False
            )
            if response.get('events'):
                print(f"✅ Trovato stream con log: {name}")
                return name
    print("⚠️ Nessun log stream trovato.")
    return None

def tail_log(stream_name, severity_filter=""):
    severity_filter = severity_filter.upper()
    print(f"📡 Tailing stream: {stream_name}")
    next_token = None
    try:
        while True:
            kwargs = {
                'logGroupName': LOG_GROUP,
                'logStreamName': stream_name,
                'startTime': start_time,
                'limit': 100,
                'startFromHead': False
            }
            if next_token:
                kwargs['nextToken'] = next_token

            response = client.get_log_events(**kwargs)
            events = response.get('events', [])
            token = response.get('nextForwardToken')

            if not events:
                print("⏳ Nessun nuovo log...")
            else:
                for event in events:
                    ts = datetime.datetime.utcfromtimestamp(event['timestamp'] / 1000.0)
                    msg = event['message'].strip()
                    # print(f"[{ts}] {msg}", flush=True)
                    import json
                    msg = event['message'].strip()
                    try:
                        parsed = json.loads(msg)
                        log_line = parsed.get('log', msg)
                    except json.JSONDecodeError:
                        log_line = msg

                    if severity_filter and severity_filter!="ERROR" and severity_filter in log_line.upper():
                        print(f"[{ts}] 🔍 {log_line}", flush=True)
                    elif "ERROR" in log_line.upper():
                        print(f"[{ts}] ❗ {log_line}", flush=True)
                    elif "it.mitur." in log_line:
                        print(f"[{ts}] 🧩 {log_line}", flush=True)
                    else:
                        print(f"[{ts}] {log_line}", flush=True)


            if token == next_token:
                time.sleep(2)
            next_token = token

    except KeyboardInterrupt:
        print("\n🛑 Interrotto dall'utente.")
    except Exception as e:
        print("❌ Errore:", e)

def list_log_groups(region='eu-south-1'):
    """
    Restituisce una lista dei nomi dei log group nella regione specificata.
    """
    try:
        client = boto3.client('logs', region_name=region)
        log_groups = []
        paginator = client.get_paginator('describe_log_groups')

        for page in paginator.paginate():
            for group in page.get('logGroups', []):
                log_groups.append(group['logGroupName'])

        return log_groups

    except (BotoCoreError, ClientError) as e:
        print(f"❌ Errore AWS: {e}")
        return []

def print_log_groups():
    log_groups = list_log_groups()
    print("📋 Log groups trovati:")
    for lg in log_groups:
        print(f" - {lg}")
        
if __name__ == "__main__":
    stream = get_first_stream_with_events()
    if stream:
        tail_log(stream, args.severity)
    else:
        exit(1)
