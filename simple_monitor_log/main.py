import psycopg2
import json
import os
from dotenv import load_dotenv

# Carica variabili da .env
load_dotenv()

import csv

def load_exclusion_list(filepath="exclusion.csv"):
    exclusion_dict = {}
    if not os.path.exists(filepath):
        return exclusion_dict
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            identifier = row.get("identifier", "").strip()
            reason = row.get("reason", "").strip()
            if identifier:
                exclusion_dict[identifier] = reason or "motivo non specificato"
    return exclusion_dict

def get_falso_positivi():
    conn = psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOST"),
        port=os.getenv("POSTGRES_PORT")
    )
    cur = conn.cursor()

    # Imposta lo schema
    cur.execute(f"SET search_path TO {os.getenv('POSTGRES_SCHEMA')};")

    error_states = ['E', 'R', '3']
    good_states = ['0', 'V', '1', '2']

    exclusion_dict = load_exclusion_list()


    # Query record in errore
    cur.execute("""
        SELECT id, identifier, status, event_date
        FROM info_in_aem_fdb
        WHERE status IN %s
    """, (tuple(error_states),))
    error_rows = cur.fetchall()

    risultati = []
    count_total = 0
    count_fp = 0
    count_real_errors = 0
    count_skipped = 0

    for err in error_rows:
        err_id, identifier, status, event_date = err

        if identifier in exclusion_dict:
            count_skipped += 1
            skip_reason = exclusion_dict[identifier]
            # facoltativo: stampa il motivo
            print(f"🔕 Skippato {identifier} — {skip_reason}")
            continue


        count_total += 1

        # Cerca log con errore
        cur.execute("""
            SELECT id_request, result_activity, created_at
            FROM mt_activity_log 
            WHERE id_request = %s AND result_activity = 'E'
            ORDER BY created_at DESC
            LIMIT 1
        """, (err_id,))
        activity = cur.fetchone()

        # Cerca altro record buono per stesso identifier
        cur.execute("""
            SELECT id, identifier, status, event_date
            FROM info_in_aem_fdb
            WHERE identifier = %s 
              AND id != %s 
              AND status IN %s
            ORDER BY event_date DESC
            LIMIT 1
        """, (identifier, err_id, tuple(good_states)))
        good = cur.fetchone()

        record = {
            "error_status": {
                "id": err_id,
                "identifier": identifier,
                "status": status,
                "timestamp": str(event_date),
                "activity_log": {
                    "result_activity": activity[1],
                    "timestamp": str(activity[2])
                } if activity else None
            }
        }

        if good:
            count_fp += 1
            record["ok_status"] = {
                "id": good[0],
                "identifier": good[1],
                "status": good[2],
                "timestamp": str(good[3])
            }
        else:
            count_real_errors += 1

        risultati.append(record)

    cur.close()
    conn.close()

    # Report in testa
    print("📊 REPORT RIEPILOGATIVO".center(60, "-"))
    print(f"{'Totale record errori rilevati:':45} {count_total + count_skipped}")
    print(f"{'Totale identifier in exclusion list:':45} {len(exclusion_dict)}")
    print(f"{'🔕  Record Skippati (exclusion):':45} {count_skipped}")
    print(f"{'✔️  Record Analizzati:':45} {count_total}")
    print(f"{'⚠️  Record Falsi positivi:':45} {count_fp}")
    print(f"{'❌  Record Errori veri registrati:':45} {count_real_errors}")
    print("-" * 60)
    print(f"{'✅ Report JSON salvato in':45} output.json\n")

    with open("output.json", "w") as f:
        json.dump(risultati, f, indent=2)

if __name__ == "__main__":
    get_falso_positivi()
