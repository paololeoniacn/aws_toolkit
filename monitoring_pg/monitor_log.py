import os
import psycopg2
from dotenv import load_dotenv
import json
import argparse

# python monitor_log.py --env prod --since 1h     # ultimi 60 minuti
# python monitor_log.py --since 3d                # ultimi 3 giorni
# python monitor_log.py --since 30m               # ultimi 30 minuti


# Carica le variabili da .env
# --------------------------------------------
# Parsing degli argomenti da riga di comando
# --------------------------------------------
parser = argparse.ArgumentParser(description="Log monitor CDP")
parser.add_argument('--env', default='dev', help="Ambiente: dev, prod, etc.")
parser.add_argument('--since', help="Intervallo: es. '1h', '30m', '1d', '3d'", default=None)
args = parser.parse_args()


# Carica il file .env corrispondente
env_file = f".env.{args.env}"
if not os.path.exists(env_file):
    print(f"⚠️  File '{env_file}' non trovato. Uso fallback su '.env.dev'")
    env_file = ".env.dev"
load_dotenv(dotenv_path=env_file)


# Recupera le variabili di configurazione
DB_HOST = os.getenv("POSTGRES_HOST")
DB_PORT = os.getenv("POSTGRES_PORT")
DB_NAME = os.getenv("POSTGRES_DB")
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_SCHEMA = os.getenv("POSTGRES_SCHEMA")

def log_env_variables():
    print("🔧 Variabili di ambiente caricate:")
    print(f"  POSTGRES_HOST     = {DB_HOST}")
    print(f"  POSTGRES_PORT     = {DB_PORT}")
    print(f"  POSTGRES_DB       = {DB_NAME}")
    print(f"  POSTGRES_USER     = {DB_USER}")
    print(f"  POSTGRES_PASSWORD = {'(caricata)' if DB_PASSWORD else '(non trovata!)'}")
    print(f"  POSTGRES_SCHEMA   = {DB_SCHEMA}")
    print("-" * 60)

log_env_variables()

# Connessione al DB
def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

from datetime import datetime, timedelta

def parse_since_arg(since_arg):
    if not since_arg:
        return None
    now = datetime.utcnow()
    try:
        if since_arg.endswith("h"):
            hours = int(since_arg[:-1])
            return now - timedelta(hours=hours)
        elif since_arg.endswith("m"):
            minutes = int(since_arg[:-1])
            return now - timedelta(minutes=minutes)
        elif since_arg.endswith("d"):
            days = int(since_arg[:-1])
            return now - timedelta(days=days)
        else:
            raise ValueError("Formato non valido. Usa es. '1h', '30m', '2d'")
    except Exception as e:
        print(f"⚠️  Errore parsing '--since': {e}")
        return None

SINCE_TIMESTAMP = parse_since_arg(args.since)
if SINCE_TIMESTAMP:
    print(f"📅 Filtro temporale attivo: log da {SINCE_TIMESTAMP.isoformat()} UTC")

# Mappatura dei codici di attività
def analyze_result_activity(result_activity):
    result_mapping = {
        '0': 'Stato iniziale',
        '1': 'Feedback inviato correttamente a Infocamere',
        '2': 'Feedback inviato correttamente a Crm',
        '3': 'KO GRAPHQL',
        'V': 'Verifica GRAPHQL',
        'E': 'Errore invio Infocamere',
        'R': 'Errore invio CRM'
    }
    return result_mapping.get(result_activity, 'Stato sconosciuto')

def check_identifier_with_good_state(identifier, current_log_id):
    if not identifier:
        return None

    conn = get_db_connection()
    cursor = conn.cursor()

    query = f"""
    SET search_path TO {DB_SCHEMA};
    SELECT id_log, result_activity
    FROM mt_activity_log al
    LEFT JOIN info_in_aem_fdb r ON al.id_request = r.id
    WHERE r.identifier = %s
      AND al.id_log != %s
      AND al.result_activity NOT IN ('E', 'R', '3')
    ORDER BY al.id_log DESC
    LIMIT 1;
    """

    cursor.execute(query, (identifier, current_log_id))
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    if result:
        log_id, result_activity = result
        stato_buono_descr = analyze_result_activity(result_activity)
        return (log_id, result_activity, stato_buono_descr)

    return None

# Estrai gli ultimi log
def fetch_recent_activity_logs(limit=10):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = f"""
    SET search_path TO {DB_SCHEMA};
    SELECT id_log, created_at, id_request, message, proc_name, result_activity, result_descr
    FROM mt_activity_log
    ORDER BY id_log DESC
    LIMIT %s;
    """
    cursor.execute(query, (limit,))
    logs = cursor.fetchall()

    cursor.close()
    conn.close()
    return logs

# Estrai gli ultimi log con join e filtro
def fetch_recent_logs(limit=10, since=None):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = f"""
    SET search_path TO {DB_SCHEMA};
    SELECT 
        al.id_log, 
        al.created_at, 
        al.id_request, 
        al.message, 
        al.proc_name, 
        al.result_activity, 
        al.result_descr,
        r.identifier,
        r.status
    FROM mt_activity_log al
    LEFT JOIN info_in_aem_fdb r ON al.id_request = r.id
    WHERE al.proc_name = 'Send Status Feedback'
      AND al.result_activity IN ('E', 'R', '3')
    """
    params = []

    if since:
        query += " AND al.created_at >= %s"
        params.append(since)

    query += " ORDER BY al.id_log DESC LIMIT %s;"
    params.append(limit)

    cursor.execute(query, params)
    logs = cursor.fetchall()
    cursor.close()
    conn.close()
    return logs


# Analizza e stampa i log
def analyze_logs(logs):
    for log in logs:
        (
            id_log, created_at, id_request, message,
            proc_name, result_activity, result_descr,
            identifier, status
        ) = log

        if message:
            try:
                msg_json = json.loads(message)
                ret_code = msg_json.get("retCode")
                ret_message = msg_json.get("retMessage")
            except json.JSONDecodeError:
                ret_code = None
                ret_message = "Errore nel parsing del JSON"
        else:
            ret_code = None
            ret_message = None

        activity_status = analyze_result_activity(result_activity)

        print(f"[{created_at} UTC] | LOG ID {id_log} | REQUEST {id_request}")
        print(f"  ↪ Processo: {proc_name}")
        print(f"  ↪ Stato: {result_activity} ({activity_status})")
        print(f"  ↪ Descrizione: {result_descr}")
        if identifier:
            print(f"  ↪ Identifier AEM: {identifier}")
        if status:
            print(f"  ↪ Status AEM: {status}")
        if ret_code is not None:
            print(f"  ↪ Dettagli JSON: retCode={ret_code}, retMessage={ret_message}")
                # ↪ Controllo per lo stesso identifier in stato "buono"
        result_check = check_identifier_with_good_state(identifier, id_log)
        if result_check:
            other_log_id, good_code, good_status = result_check
            print(f"  ↪ ✅ UL presente anche in stato {good_code} ({good_status}) con log ID {other_log_id}")
        else:
            from send_mail_service import send_alert_email
            send_alert_email(
                identifier=identifier,
                description=f"PROCESSO {proc_name} - Stato: {result_activity} ({activity_status})",
                error_message="Descrizione: {result_descr}"
            )
            print(f"  ↪ ❌ UL NON presente anche in stato BUONO")        

        print("-" * 60)


# Funzione principale
def main():
    logs = fetch_recent_logs(limit=20, since=SINCE_TIMESTAMP)
    analyze_logs(logs)

if __name__ == "__main__":
    main()
