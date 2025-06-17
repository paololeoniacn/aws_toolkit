import os
import psycopg2
from dotenv import load_dotenv
import json
import argparse
import logging
from datetime import datetime
import sys
from collections import Counter

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
parser.add_argument('--severity', choices=['error', 'all'], default='error',
                    help="Filtra per severità: 'error' (default), 'all'")
args = parser.parse_args()

# Configura il logger
import logging

# Nome file dinamico: report_YYYY-MM-DD_HH-MM.log
timestamp_str = datetime.now().strftime("%Y-%m-%d_%H-%M")
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_file_name = os.path.join(log_dir, f"report_{timestamp_str}.log")


# Formato comune
log_format = "[%(asctime)s] [%(levelname)s] %(message)s"
file_format = "[%(levelname)s] %(message)s"
formatter = logging.Formatter(log_format)
fileFormatter = logging.Formatter(file_format)
# File handler (salva tutto)
file_handler = logging.FileHandler(log_file_name, encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(fileFormatter)

# Stream handler INFO e DEBUG su stdout
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.INFO)
stdout_handler.addFilter(lambda record: record.levelno < logging.WARNING)
stdout_handler.setFormatter(formatter)

# Stream handler WARNING+ su stderr
stderr_handler = logging.StreamHandler(sys.stderr)
stderr_handler.setLevel(logging.WARNING)
stderr_handler.setFormatter(formatter)

# Logger globale
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.handlers = [file_handler, stdout_handler, stderr_handler]


# Carica il file .env corrispondente
env_file = f".env.{args.env}"
if not os.path.exists(env_file):
    logger.warn(f"⚠️  File '{env_file}' non trovato. Uso fallback su '.env.dev'")
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
    logger.info("🔧 Variabili di ambiente caricate:")
    logger.info(f"  POSTGRES_HOST     = {DB_HOST}")
    logger.info(f"  POSTGRES_PORT     = {DB_PORT}")
    logger.info(f"  POSTGRES_DB       = {DB_NAME}")
    logger.info(f"  POSTGRES_USER     = {DB_USER}")
    logger.info(f"  POSTGRES_PASSWORD = {'(caricata)' if DB_PASSWORD else '(non trovata!)'}")
    logger.info(f"  POSTGRES_SCHEMA   = {DB_SCHEMA}")
    logger.info("-" * 60)

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
        logger.error(f"⚠️  Errore parsing '--since': {e}")
        return None

SINCE_TIMESTAMP = parse_since_arg(args.since)
if SINCE_TIMESTAMP:
    logger.info(f"📅 Filtro temporale attivo: log da {SINCE_TIMESTAMP.isoformat()} UTC")

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
def fetch_recent_logs(limit, since=None, severity="error"):
    logger.info(f"limit {limit}, since={since}, severity={severity}")
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
    """

    params = []

    if severity == "error":
        query += " AND al.result_activity IN ('E', 'R', '3')"
    # elif severity == "all":
    #     query += " AND al.result_activity NOT IN ('E', 'R', '3')"
    #     query += " AND r.status NOT IN ('E', 'R', '3')"

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
def analyze_logs_ori(logs, severity="error"):
    for log in logs:
        (
            id_log, created_at, id_request, message,
            proc_name, result_activity, result_descr,
            identifier, status
        ) = log

        # Parsing JSON
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

        logger.debug(f"[{created_at} UTC] | LOG ID {id_log} | REQUEST {id_request}")
        logger.debug(f"  ↪ Processo: {proc_name}")
        logger.debug(f"  ↪ Stato: {result_activity} ({activity_status})")
        logger.debug(f"  ↪ Descrizione: {result_descr}")
        if identifier:
            logger.debug(f"  ↪ Identifier AEM: {identifier}")
        if status:
            logger.debug(f"  ↪ Status AEM: {status}")
        if ret_code is not None:
            logger.debug(f"  ↪ Dettagli JSON: retCode={ret_code}, retMessage={ret_message}")

        if severity == "error":
            result_check = check_identifier_with_good_state(identifier, id_log)
            if result_check:
                other_log_id, good_code, good_status = result_check
                logger.debug(f"  ↪ ✅ UL presente anche in stato {good_code} ({good_status}) con log ID {other_log_id}")
            else:
                from send_mail_service import send_alert_email
                send_alert_email(
                    identifier=identifier,
                    description=f"PROCESSO {proc_name} - Stato: {result_activity} ({activity_status})",
                    error_message="Descrizione: {result_descr}"
                )
                logger.error(f"  ↪ ❌ UL NON presente anche in stato BUONO")

        logger.debug("-" * 60)

def analyze_logs(logs, severity="error"):
    ok_logs = []
    real_errors = []

    for log in logs:
        (
            id_log, created_at, id_request, message,
            proc_name, result_activity, result_descr,
            identifier, status
        ) = log

        # Parsing JSON
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

        logger.debug(f"[{created_at} UTC] | LOG ID {id_log} | REQUEST {id_request}")
        logger.debug(f"  ↪ Processo: {proc_name}")
        logger.debug(f"  ↪ Stato: {result_activity} ({activity_status})")
        logger.debug(f"  ↪ Descrizione: {result_descr}")
        if identifier:
            logger.debug(f"  ↪ Identifier AEM: {identifier}")
        if status:
            logger.debug(f"  ↪ Status AEM: {status}")
        if ret_code is not None:
            logger.debug(f"  ↪ Dettagli JSON: retCode={ret_code}, retMessage={ret_message}")

        errore_grezzo = result_activity in ['E', 'R', '3']

        if errore_grezzo:
            result_check = check_identifier_with_good_state(identifier, id_log)
            if result_check:
                logger.debug(f"  ↪ ✅ UL recuperato in stato buono: {result_check[1]} ({result_check[2]})")
                ok_logs.append(log)
            else:
                from send_mail_service import send_alert_email
                send_alert_email(
                    identifier=identifier,
                    description=f"PROCESSO {proc_name} - Stato: {result_activity} ({activity_status})",
                    error_message="Descrizione: {result_descr}"
                )
                logger.error(f"  ↪ ❌ UL NON recuperato. Errore effettivo.")
                real_errors.append(log)
        else:
            ok_logs.append(log)

        logger.debug("-" * 60)

    return ok_logs, real_errors

def generate_summary_report(logs):
    logger.info("📊 Report riepilogativo per codice stato:")
    counter = Counter()

    for log in logs:
        result_activity = log[5]  # colonna 6: result_activity
        counter[result_activity] += 1

    for code, count in sorted(counter.items()):
        descr = analyze_result_activity(code)
        logger.info(f"  ➤ Stato {code}: {count} occorrenze - {descr}")


# Funzione principale
def main():
    logs = fetch_recent_logs(limit=1000, since=SINCE_TIMESTAMP, severity="all")  # always all
    logger.info(f"🔍 Trovati {len(logs)} log (tutti inclusi)")

    ok_logs, real_errors = analyze_logs(logs, severity=args.severity)

    logger.info(f"🟢 Log validi o recuperati: {len(ok_logs)}")
    logger.info(f"🔴 Errori effettivi (non recuperati): {len(real_errors)}")

    generate_summary_report(ok_logs + real_errors)  # report completo

if __name__ == "__main__":
    main()
