import csv
from datetime import datetime, timedelta
import random

# CONFIGURAZIONE
data_inizio_str = "2025-07-03T12:25:00"  # data di partenza che puoi cambiare
intervallo_minuti = 5                    # intervallo tra i log
mesi_indietro = 3                        # quanti mesi indietro generare

# Converte la stringa in oggetto datetime
data_inizio = datetime.fromisoformat(data_inizio_str)

# Calcola la data finale
giorni_indietro = mesi_indietro * 30  # approssimazione mesi -> giorni
data_fine = data_inizio - timedelta(days=giorni_indietro)

# Crea il file CSV
with open('log_data.csv', 'w', newline='') as csvfile:
    fieldnames = ['timestamp', 'logcount', 'trend']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')

    writer.writeheader()
    
    data_corrente = data_inizio
    while data_corrente >= data_fine:
        # Genera un logcount casuale (puoi modificare range come vuoi)
        logcount = random.randint(1, 100)
        writer.writerow({
            'timestamp': data_corrente.strftime('%Y-%m-%dT%H:%M:%S'),
            'logcount': logcount,
            'trend': 'current'
        })
        
        # Passa al timestamp precedente
        data_corrente -= timedelta(minutes=intervallo_minuti)

print("File log_data.csv generato con successo!")
